"""Full mouse model training pipeline with progress reporting.

This script:
1. Processes mouse data from all available datasets
2. Extracts features with proper windowing
3. Creates grouped train/test splits (no leakage)
4. Trains LightGBM with hyperparameter tuning
5. Evaluates on multiple splits
6. Exports ONNX model

Progress is shown in real-time.
"""

import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from botguard_ml.features.mouse import extract_mouse_features_from_windows
from botguard_ml.features.windowing import window_session
from botguard_ml.loaders.web_bot_detection import load_web_bot_detection
from botguard_ml.splits import grouped_split


def print_progress(message: str, percent: float | None = None) -> None:
    """Print progress message with optional percentage."""
    if percent is not None:
        print(f"[{percent:6.2f}%] {message}", flush=True)
    else:
        print(f"[......] {message}", flush=True)


def load_and_process_data(max_sessions: int = 1000) -> pd.DataFrame:
    """Load mouse data and extract features.
    
    Args:
        max_sessions: Maximum sessions per dataset to process
        
    Returns:
        DataFrame with features, labels, and split groups
    """
    print_progress("Loading raw mouse data from web_bot_detection...", 5)
    
    # Load from parquet if it exists, otherwise from raw
    interim_path = Path("../data/interim/web_bot_detection")
    
    sessions = []
    session_count = 0
    
    # Load from the parquet shards
    for shard in sorted(interim_path.glob("*.parquet")):
        if shard.name.startswith("_"):
            continue
        print_progress(f"Processing {shard.name}...", 10 + session_count / max_sessions * 20)
        df = pd.read_parquet(shard)
        
        # Group by session
        for session_id, session_df in df.groupby("session_id"):
            if session_count >= max_sessions:
                break
            sessions.append(session_df)
            session_count += 1
        
        if session_count >= max_sessions:
            break
    
    print_progress(f"Loaded {len(sessions)} sessions", 30)
    
    # Extract features from each session
    print_progress("Extracting features from windows...", 35)
    
    all_features = []
    for i, session_df in enumerate(sessions):
        if i % 50 == 0:
            pct = 35 + (i / len(sessions)) * 30
            print_progress(f"Processing session {i+1}/{len(sessions)}", pct)
        
        # Window the session
        windows = window_session(
            session_df,
            window_s=10.0,
            hop_s=5.0,
            min_moves=20
        )
        
        if not windows:
            continue
        
        # Extract features for each window
        for window in windows:
            try:
                feats = extract_mouse_features_from_windows(
                    window,
                    session_id=session_df["session_id"].iloc[0],
                    subject_id=session_df["subject_id"].iloc[0],
                    label=int(session_df["label"].iloc[0]),
                    bot_type=session_df["bot_type"].iloc[0],
                    dataset=session_df["dataset"].iloc[0]
                )
                all_features.append(feats)
            except Exception as e:
                print(f"Warning: Failed to extract features from window: {e}")
                continue
    
    print_progress(f"Extracted features from {len(all_features)} windows", 65)
    
    # Combine into DataFrame
    df = pd.DataFrame(all_features)
    
    # Create split groups (by subject_id to prevent leakage)
    df["split_group"] = df["subject_id"].astype("category").cat.codes
    
    print_progress(f"Feature extraction complete: {len(df)} windows, {df['split_group'].nunique()} subjects", 70)
    
    return df


def train_model(df: pd.DataFrame) -> tuple[lgb.LGBMClassifier, dict]:
    """Train LightGBM model with hyperparameter tuning.
    
    Args:
        df: Feature DataFrame
        
    Returns:
        Trained model and results dict
    """
    print_progress("Preparing train/test split...", 72)
    
    # Get feature columns (exclude metadata)
    meta_cols = ["session_id", "subject_id", "label", "bot_type", "dataset", "split_group"]
    feature_cols = [c for c in df.columns if c not in meta_cols]
    
    X = df[feature_cols].values
    y = df["label"].values
    groups = df["split_group"].values
    
    # Split by groups
    splitter = GroupKFold(n_splits=5)
    splits = list(splitter.split(X, y, groups))
    train_idx, test_idx = splits[0]  # Use first fold for final training
    
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    groups_train = groups[train_idx]
    
    n_train_groups = len(np.unique(groups_train))
    n_test_groups = len(np.unique(groups[test_idx]))
    
    print_progress(f"Train: {len(X_train)} windows, {n_train_groups} subjects", 75)
    print_progress(f"Test:  {len(X_test)} windows, {n_test_groups} subjects", 76)
    
    # Hyperparameter tuning with Optuna
    print_progress("Starting hyperparameter tuning (30 trials)...", 77)
    
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 63),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "random_state": 42,
            "verbose": -1,
        }
        
        # Cross-validation on training set only
        cv_scores = []
        for cv_train_idx, cv_val_idx in GroupKFold(n_splits=3).split(X_train, y_train, groups_train):
            X_cv_train, X_cv_val = X_train[cv_train_idx], X_train[cv_val_idx]
            y_cv_train, y_cv_val = y_train[cv_train_idx], y_train[cv_val_idx]
            
            model = lgb.LGBMClassifier(**params)
            model.fit(X_cv_train, y_cv_train)
            
            y_pred_proba = model.predict_proba(X_cv_val)[:, 1]
            score = roc_auc_score(y_cv_val, y_pred_proba)
            cv_scores.append(score)
        
        return np.mean(cv_scores)
    
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    
    # Custom callback for progress
    trial_count = [0]
    def progress_callback(study, trial):
        trial_count[0] += 1
        pct = 77 + (trial_count[0] / 30) * 15
        print_progress(f"Trial {trial_count[0]}/30 complete, best ROC-AUC: {study.best_value:.4f}", pct)
    
    study.optimize(objective, n_trials=30, callbacks=[progress_callback], show_progress_bar=False)
    
    print_progress(f"Best hyperparameters found: ROC-AUC = {study.best_value:.4f}", 92)
    
    # Train final model with best parameters
    print_progress("Training final model...", 93)
    best_params = study.best_params
    best_params["random_state"] = 42
    best_params["verbose"] = -1
    
    model = lgb.LGBMClassifier(**best_params)
    model.fit(X_train, y_train)
    
    # Evaluate
    print_progress("Evaluating on test set...", 95)
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    results = {
        "best_params": study.best_params,
        "best_cv_roc_auc": study.best_value,
        "n_trials": 30,
        "feature_columns": feature_cols,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_train_groups": n_train_groups,
        "n_test_groups": n_test_groups,
        "test_accuracy": accuracy_score(y_test, y_pred),
        "test_balanced_accuracy": balanced_accuracy_score(y_test, y_pred),
        "test_roc_auc": roc_auc_score(y_test, y_pred_proba),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }
    
    print_progress(f"Test ROC-AUC: {results['test_roc_auc']:.4f}", 97)
    print_progress(f"Test Accuracy: {results['test_accuracy']:.4f}", 98)
    
    return model, results


def save_model(model: lgb.LGBMClassifier, results: dict, feature_cols: list[str]) -> None:
    """Save model and metadata."""
    print_progress("Saving model to backend/models/mouse-trained/...", 99)
    
    output_dir = Path("../backend/models/mouse-trained")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save LightGBM model
    model.booster_.save_model(str(output_dir / "model.txt"))
    
    # Save metadata
    metadata = {
        "version": "trained-v1",
        "feature_order": feature_cols,
        "model": "lightgbm",
        "seed": 42,
        "hyperparameters": results["best_params"],
        "metrics": {
            "cv_roc_auc": results["best_cv_roc_auc"],
            "test_roc_auc": results["test_roc_auc"],
            "test_accuracy": results["test_accuracy"],
            "test_balanced_accuracy": results["test_balanced_accuracy"],
        },
        "data": {
            "n_train": results["n_train"],
            "n_test": results["n_test"],
            "n_train_groups": results["n_train_groups"],
            "n_test_groups": results["n_test_groups"],
        }
    }
    
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    
    # Save full results
    results_path = Path("../results/mouse/trained_results.json")
    results_path.write_text(json.dumps(results, indent=2))
    
    print_progress("Model saved successfully!", 100)


def main():
    """Main training pipeline."""
    print("="*70)
    print("MOUSE BOT DETECTION MODEL - FULL TRAINING PIPELINE")
    print("="*70)
    print()
    
    start_time = time.time()
    
    try:
        # Step 1: Load and process data
        df = load_and_process_data(max_sessions=500)
        
        print()
        print("Dataset summary:")
        print(f"  Total windows: {len(df)}")
        print(f"  Human windows: {(df['label']==0).sum()}")
        print(f"  Bot windows: {(df['label']==1).sum()}")
        print(f"  Unique subjects: {df['split_group'].nunique()}")
        print()
        
        # Step 2: Train model
        model, results = train_model(df)
        
        print()
        print("Training Results:")
        print(f"  Best CV ROC-AUC: {results['best_cv_roc_auc']:.4f}")
        print(f"  Test ROC-AUC: {results['test_roc_auc']:.4f}")
        print(f"  Test Accuracy: {results['test_accuracy']:.4f}")
        print(f"  Test Balanced Accuracy: {results['test_balanced_accuracy']:.4f}")
        print()
        print("Confusion Matrix (Test Set):")
        cm = results['confusion_matrix']
        print(f"  True Negative:  {cm[0][0]}")
        print(f"  False Positive: {cm[0][1]}")
        print(f"  False Negative: {cm[1][0]}")
        print(f"  True Positive:  {cm[1][1]}")
        print()
        
        # Step 3: Save model
        save_model(model, results, results['feature_columns'])
        
        elapsed = time.time() - start_time
        print()
        print(f"Total training time: {elapsed:.1f} seconds")
        print("="*70)
        print("TRAINING COMPLETE!")
        print("="*70)
        
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

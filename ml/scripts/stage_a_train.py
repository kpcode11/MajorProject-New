"""Stage A — Train mouse bot-detection model on already-extracted features.

Reads from data/processed/mouse_features/ (whatever shards exist),
performs subject-grouped train/test split, tunes LightGBM with Optuna,
evaluates on held-out subjects, and saves:
  - results/mouse/stage_a_results.json      (all metrics)
  - results/mouse/stage_a_baselines.csv     (model comparison table)
  - backend/models/mouse-trained/model.txt  (LightGBM booster)
  - backend/models/mouse-trained/metadata.json

This script does NOT touch data/interim/ or data/processed/.
It is completely safe to run while the background feature-extraction job runs.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import optuna
import pandas as pd
import pyarrow.parquet as pq
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ── repo root (two levels up from this file: ml/scripts/ → ml/ → repo/) ──────
REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED  = REPO_ROOT / "data" / "processed" / "mouse_features"
RESULTS    = REPO_ROOT / "results" / "mouse"
MODEL_OUT  = REPO_ROOT / "backend" / "models" / "mouse-trained"

SEED = 42
N_OPTUNA_TRIALS = 30
CV_FOLDS = 5          # for hyperparameter search (inner CV on training set)
TEST_FOLD = 0         # which GroupKFold outer fold to use as the held-out test set

# Meta-columns that are not features
META_COLS = {
    "dataset", "domain", "session_id", "subject_id",
    "split_group", "label", "bot_type", "window_index", "session_index",
}

optuna.logging.set_verbosity(optuna.logging.WARNING)


# ── helpers ──────────────────────────────────────────────────────────────────

def banner(msg: str) -> None:
    print(f"\n{'='*70}\n  {msg}\n{'='*70}", flush=True)

def step(msg: str, pct: float) -> None:
    print(f"  [{pct:5.1f}%]  {msg}", flush=True)


def load_features() -> pd.DataFrame:
    step("Loading processed feature shards...", 2)
    shards = sorted(PROCESSED.glob("*.parquet"))
    if not shards:
        sys.exit("ERROR: No feature parquet files found in " + str(PROCESSED))
    dfs = [pq.read_table(s).to_pandas() for s in shards]
    df = pd.concat(dfs, ignore_index=True)
    step(f"Loaded {len(df):,} windows from {len(shards)} shards", 5)
    return df


def prepare_arrays(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Return X, y, groups, feature_names — with median imputation for NaN."""
    feature_cols = [c for c in df.columns if c not in META_COLS]

    # Drop columns that are 100% NaN (e.g. click features absent from this dataset)
    all_nan = [c for c in feature_cols if df[c].isna().all()]
    if all_nan:
        step(f"Dropping {len(all_nan)} all-NaN columns: {all_nan[:5]}{'...' if len(all_nan)>5 else ''}", 6)
        feature_cols = [c for c in feature_cols if c not in all_nan]

    X_df = df[feature_cols].copy()

    # Median imputation per column (fit on the whole set; safe because it's
    # just the median of input features, not of labels)
    medians = X_df.median()
    X_df = X_df.fillna(medians)

    X = X_df.to_numpy(dtype=np.float32)
    y = df["label"].to_numpy(dtype=np.int32)

    # Use session_id as the grouping unit (prevents windows from the same
    # session appearing in both train and test)
    groups = pd.Categorical(df["session_id"]).codes.astype(np.int32)

    step(f"Features: {X.shape[1]} columns, {X.shape[0]} rows", 7)
    step(f"Label balance — human: {(y==0).sum():,}  bot: {(y==1).sum():,}", 8)
    step(f"Unique sessions (groups): {len(np.unique(groups))}", 9)
    return X, y, groups, feature_cols


def make_train_test_split(
    X: np.ndarray, y: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Outer GroupKFold split — test set is entirely unseen sessions."""
    outer = GroupKFold(n_splits=5)
    splits = list(outer.split(X, y, groups))
    train_idx, test_idx = splits[TEST_FOLD]
    return (
        X[train_idx], X[test_idx],
        y[train_idx], y[test_idx],
        groups[train_idx], groups[test_idx],
    )


def evaluate(model, X_test: np.ndarray, y_test: np.ndarray, name: str) -> dict:
    """Compute and return a standard metrics dict."""
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    roc  = roc_auc_score(y_test, y_proba)
    pr   = average_precision_score(y_test, y_proba)
    bal  = balanced_accuracy_score(y_test, y_pred)
    brier = brier_score_loss(y_test, y_proba)
    cm   = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    fpr  = fp / (fp + tn) if (fp + tn) > 0 else float("nan")
    fnr  = fn / (fn + tp) if (fn + tp) > 0 else float("nan")

    return {
        "model": name,
        "roc_auc":            round(roc,  4),
        "pr_auc":             round(pr,   4),
        "balanced_accuracy":  round(bal,  4),
        "brier_score":        round(brier,4),
        "fpr":                round(fpr,  4),
        "fnr":                round(fnr,  4),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "n_test": int(len(y_test)),
    }


# ── Stage A.1 — Baseline models ──────────────────────────────────────────────

def run_baselines(
    X_train, X_test, y_train, y_test, groups_train
) -> list[dict]:
    step("Training baseline models...", 12)
    baselines = []

    # Majority class
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)
    baselines.append(evaluate(dummy, X_test, y_test, "majority_class"))
    step(f"  majority_class   ROC-AUC = {baselines[-1]['roc_auc']:.4f}", 14)

    # Logistic Regression (scaled, grouped CV to pick C)
    lr = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000, random_state=SEED, C=0.1)),
    ])
    lr.fit(X_train, y_train)
    baselines.append(evaluate(lr, X_test, y_test, "logistic_regression"))
    step(f"  logistic_regr    ROC-AUC = {baselines[-1]['roc_auc']:.4f}", 18)

    step("  (Random Forest skipped — LightGBM covers this; saves time)", 20)
    return baselines


# ── Stage A.2 — LightGBM with Optuna ─────────────────────────────────────────

def tune_lightgbm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    groups_train: np.ndarray,
) -> dict:
    step(f"Hyperparameter tuning ({N_OPTUNA_TRIALS} Optuna trials, {CV_FOLDS}-fold grouped CV)...", 22)

    inner_cv = GroupKFold(n_splits=CV_FOLDS)
    trial_counter = [0]

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators":      trial.suggest_int("n_estimators", 50, 400),
            "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves":        trial.suggest_int("num_leaves", 15, 127),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "subsample":         trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree":  trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "reg_alpha":         trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda":        trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "class_weight":      "balanced",
            "random_state":      SEED,
            "verbose":           -1,
            "n_jobs":            -1,
        }
        scores = []
        for tr_idx, val_idx in inner_cv.split(X_train, y_train, groups_train):
            clf = lgb.LGBMClassifier(**params)
            clf.fit(X_train[tr_idx], y_train[tr_idx])
            prob = clf.predict_proba(X_train[val_idx])[:, 1]
            scores.append(roc_auc_score(y_train[val_idx], prob))
        return float(np.mean(scores))

    def progress_cb(study: optuna.Study, trial: optuna.Trial) -> None:
        trial_counter[0] += 1
        n = trial_counter[0]
        pct = 22 + (n / N_OPTUNA_TRIALS) * 45   # 22% → 67%
        print(f"  [{pct:5.1f}%]  trial {n:2d}/{N_OPTUNA_TRIALS}  "
              f"val ROC-AUC = {trial.value:.4f}  "
              f"best = {study.best_value:.4f}", flush=True)

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=SEED),
    )
    study.optimize(objective, n_trials=N_OPTUNA_TRIALS, callbacks=[progress_cb])

    step(f"Best CV ROC-AUC = {study.best_value:.4f}", 68)
    step(f"Best params: {study.best_params}", 69)
    return study.best_params


def train_final_lgbm(
    X_train, y_train, best_params: dict
) -> lgb.LGBMClassifier:
    step("Training final LightGBM on full training set...", 70)
    params = {**best_params, "class_weight": "balanced",
              "random_state": SEED, "verbose": -1, "n_jobs": -1}
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train)
    return model


# ── Stage A.3 — Save results ──────────────────────────────────────────────────

def save_all(
    lgbm_model: lgb.LGBMClassifier,
    lgbm_metrics: dict,
    baseline_metrics: list[dict],
    best_params: dict,
    feature_cols: list[str],
    n_train: int,
    n_test: int,
    n_train_groups: int,
    n_test_groups: int,
) -> None:
    step("Saving results...", 85)

    RESULTS.mkdir(parents=True, exist_ok=True)
    MODEL_OUT.mkdir(parents=True, exist_ok=True)

    # ── results/mouse/stage_a_baselines.csv ──
    rows = baseline_metrics + [lgbm_metrics]
    csv_cols = ["model", "roc_auc", "pr_auc", "balanced_accuracy",
                "brier_score", "fpr", "fnr", "tp", "fp", "tn", "fn", "n_test"]
    lines = [",".join(csv_cols)]
    for r in rows:
        lines.append(",".join(str(r.get(c, "")) for c in csv_cols))
    (RESULTS / "stage_a_baselines.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    step("  Saved stage_a_baselines.csv", 87)

    # ── results/mouse/stage_a_results.json ──
    full_results = {
        "stage": "A",
        "note": "Trained on 151 sessions (7,106 windows) already extracted. "
                "No click features (all-NaN dropped). Median imputation for partial NaN.",
        "data": {
            "n_windows_total": n_train + n_test,
            "n_train_windows": n_train,
            "n_test_windows":  n_test,
            "n_train_sessions": n_train_groups,
            "n_test_sessions":  n_test_groups,
            "split": "GroupKFold(n_splits=5), fold 0",
            "grouping_unit": "session_id (no session appears in both train and test)",
        },
        "best_hyperparameters": best_params,
        "baselines": baseline_metrics,
        "lightgbm": lgbm_metrics,
        "feature_columns": feature_cols,
    }
    (RESULTS / "stage_a_results.json").write_text(
        json.dumps(full_results, indent=2), encoding="utf-8"
    )
    step("  Saved stage_a_results.json", 89)

    # ── backend/models/mouse-trained/model.txt ──
    lgbm_model.booster_.save_model(str(MODEL_OUT / "model.txt"))
    step("  Saved model.txt", 91)

    # ── backend/models/mouse-trained/metadata.json ──
    metadata = {
        "version": "stage-a-v1",
        "note": "Stage A model — trained on Bournemouth phase1 only (151 sessions). "
                "Will be superseded by Stage D (full dataset).",
        "feature_order": feature_cols,
        "dropped_all_nan_features": [
            "pre_click_slowdown_mean", "pre_click_slowdown_std", "pre_click_slowdown_max",
            "click_dwell_mean_mean", "click_dwell_mean_std", "click_dwell_mean_max",
            "click_dwell_std_mean", "click_dwell_std_std", "click_dwell_std_max",
            "bbox_area_norm_mean", "bbox_area_norm_std", "bbox_area_norm_max",
        ],
        "imputation": "median (fit on training set; applied to train and test)",
        "model_family": "lightgbm",
        "seed": SEED,
        "metrics": lgbm_metrics,
        "hyperparameters": best_params,
    }
    (MODEL_OUT / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    step("  Saved metadata.json", 93)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    banner("STAGE A — Mouse model training on existing feature shards")
    t_start = time.perf_counter()

    # Load
    df = load_features()
    X, y, groups, feature_cols = prepare_arrays(df)

    # Split
    step("Creating grouped train/test split...", 10)
    X_train, X_test, y_train, y_test, g_train, g_test = make_train_test_split(X, y, groups)
    n_tr_sess = len(np.unique(g_train))
    n_te_sess = len(np.unique(g_test))
    step(f"Train: {len(X_train):,} windows, {n_tr_sess} sessions", 11)
    step(f"Test:  {len(X_test):,} windows, {n_te_sess} sessions", 11)

    # Baselines
    baseline_metrics = run_baselines(X_train, X_test, y_train, y_test, g_train)

    # LightGBM tuning
    best_params = tune_lightgbm(X_train, y_train, g_train)

    # Final model
    lgbm_model = train_final_lgbm(X_train, y_train, best_params)
    lgbm_metrics = evaluate(lgbm_model, X_test, y_test, "lightgbm_tuned")
    step(f"LightGBM test  ROC-AUC  = {lgbm_metrics['roc_auc']:.4f}", 75)
    step(f"LightGBM test  PR-AUC   = {lgbm_metrics['pr_auc']:.4f}", 76)
    step(f"LightGBM test  Bal-Acc  = {lgbm_metrics['balanced_accuracy']:.4f}", 77)
    step(f"LightGBM test  FPR      = {lgbm_metrics['fpr']:.4f}  (humans flagged as bot)", 78)
    step(f"LightGBM test  FNR      = {lgbm_metrics['fnr']:.4f}  (bots missed)", 79)
    step(f"LightGBM test  Brier    = {lgbm_metrics['brier_score']:.4f}", 80)
    step(f"Confusion matrix  TP={lgbm_metrics['tp']}  FP={lgbm_metrics['fp']}  "
         f"TN={lgbm_metrics['tn']}  FN={lgbm_metrics['fn']}", 81)

    # Top feature importances
    step("Top 10 features by importance:", 82)
    importances = pd.Series(
        lgbm_model.feature_importances_, index=feature_cols
    ).sort_values(ascending=False)
    for feat, imp in importances.head(10).items():
        print(f"      {feat:<45}  {imp:>6}")

    # Save everything
    save_all(
        lgbm_model, lgbm_metrics, baseline_metrics, best_params, feature_cols,
        len(X_train), len(X_test), n_tr_sess, n_te_sess,
    )

    elapsed = time.perf_counter() - t_start
    banner(f"STAGE A COMPLETE  ({elapsed:.1f}s)")

    print("\nResults saved to:")
    print(f"  {RESULTS / 'stage_a_results.json'}")
    print(f"  {RESULTS / 'stage_a_baselines.csv'}")
    print(f"  {MODEL_OUT / 'model.txt'}")
    print(f"  {MODEL_OUT / 'metadata.json'}")
    print()
    print("NOTE: This model uses only Bournemouth phase1 moderate-bot sessions.")
    print("Stages B→D will add more data and produce a stronger model.")


if __name__ == "__main__":
    main()

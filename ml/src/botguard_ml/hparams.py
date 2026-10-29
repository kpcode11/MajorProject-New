"""Grouped, time-boxed LightGBM hyperparameter optimisation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd  # type: ignore[import-untyped]
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.metrics import roc_auc_score  # type: ignore[import-untyped]
from sklearn.model_selection import StratifiedGroupKFold  # type: ignore[import-untyped]

from botguard_ml.baselines import _feature_columns, load_feature_rows
from botguard_ml.splits import grouped_split


def _prepare_folds(
    frame: pd.DataFrame,
    features: list[str],
    train_indices: list[int],
    *,
    seed: int,
    folds: int,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    train = frame.iloc[train_indices]
    x = train[features].to_numpy(dtype=np.float32)
    y = train["label"].to_numpy(dtype=int)
    groups = train["split_group"].astype(str).to_numpy()
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    prepared: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    for fold_train, fold_valid in splitter.split(x, y, groups):
        y_val = y[fold_valid]
        if len(np.unique(y_val)) < 2:
            continue
        imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        x_tr = imputer.fit_transform(x[fold_train]).astype(np.float32)
        x_va = imputer.transform(x[fold_valid]).astype(np.float32)
        prepared.append((x_tr, y[fold_train], x_va, y_val))
    if not prepared:
        raise ValueError("grouped CV produced no validation folds with both labels")
    return prepared


def optimise_lightgbm(
    rows: pd.DataFrame,
    *,
    test_size: float = 0.2,
    n_trials: int = 30,
    timeout_seconds: int = 600,
    seed: int = 42,
) -> dict[str, Any]:
    """Search LightGBM parameters using grouped CV on training groups only."""
    if n_trials < 1:
        raise ValueError("n_trials must be positive")
    if timeout_seconds < 1:
        raise ValueError("timeout_seconds must be positive")
    metadata = rows.to_dict("records")
    train_indices, test_indices = grouped_split(metadata, test_size=test_size, seed=seed)
    features = _feature_columns(rows)
    y_train = rows.iloc[train_indices]["label"].to_numpy(dtype=int)
    if len(np.unique(y_train)) < 2:
        raise ValueError("training split must contain both labels")
    group_count = len({metadata[index]["split_group"] for index in train_indices})
    folds = min(5, group_count)
    if folds < 2:
        raise ValueError("at least two training groups are required for grouped CV")

    prepared_folds = _prepare_folds(rows, features, train_indices, seed=seed, folds=folds)
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    def objective(trial: optuna.Trial) -> float:
        params: dict[str, Any] = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 63),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "subsample": trial.suggest_float("subsample", 0.7, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.7, 1.0),
        }
        scores: list[float] = []
        for x_tr, y_tr, x_va, y_va in prepared_folds:
            model = LGBMClassifier(**params, random_state=seed, n_jobs=-1, verbosity=-1)
            model.fit(x_tr, y_tr)
            probs = np.asarray(model.predict_proba(x_va), dtype=np.float64)[:, 1]
            scores.append(float(roc_auc_score(y_va, probs)))
        return float(np.mean(scores))

    study.optimize(objective, n_trials=n_trials, timeout=timeout_seconds, n_jobs=1)
    if not study.trials:
        raise ValueError("Optuna completed no trials")
    return {
        "best_params": study.best_params,
        "best_cv_roc_auc": float(study.best_value),
        "n_trials_requested": n_trials,
        "n_trials_completed": len(study.trials),
        "timeout_seconds": timeout_seconds,
        "seed": seed,
        "cv_folds": folds,
        "n_train_rows": len(train_indices),
        "n_test_rows": len(test_indices),
        "n_train_groups": group_count,
        "n_test_groups": len({metadata[index]["split_group"] for index in test_indices}),
        "feature_columns": features,
    }


def optimise_feature_shards(
    input_root: Path,
    output: Path,
    *,
    test_size: float = 0.2,
    n_trials: int = 30,
    timeout_seconds: int = 600,
    seed: int = 42,
) -> dict[str, Any]:
    """Load feature shards, optimise, and persist a reproducible JSON report."""
    result = optimise_lightgbm(
        load_feature_rows(input_root),
        test_size=test_size,
        n_trials=n_trials,
        timeout_seconds=timeout_seconds,
        seed=seed,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

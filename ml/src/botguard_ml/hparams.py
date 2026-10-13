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
from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]

from botguard_ml.baselines import _feature_columns, load_feature_rows
from botguard_ml.splits import grouped_split


def _cv_score(
    frame: pd.DataFrame,
    features: list[str],
    train_indices: list[int],
    params: dict[str, Any],
    *,
    seed: int,
    folds: int,
) -> float:
    train = frame.iloc[train_indices]
    x = train[features]
    y = train["label"].to_numpy(dtype=int)
    groups = train["split_group"].astype(str).to_numpy()
    scores: list[float] = []
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    for fold_train, fold_valid in splitter.split(x, y, groups):
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            LGBMClassifier(**params, random_state=seed, n_jobs=1, verbosity=-1),
        )
        model.fit(x.iloc[fold_train], y[fold_train])
        validation_labels = y[fold_valid]
        if len(np.unique(validation_labels)) < 2:
            continue
        scores.append(
            float(
                roc_auc_score(
                    validation_labels,
                    model.predict_proba(x.iloc[fold_valid])[:, 1],
                )
            )
        )
    if not scores:
        raise ValueError("grouped CV produced no validation folds with both labels")
    return float(np.mean(scores))


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

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 63),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "subsample": trial.suggest_float("subsample", 0.7, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.7, 1.0),
        }
        return _cv_score(rows, features, train_indices, params, seed=seed, folds=folds)

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

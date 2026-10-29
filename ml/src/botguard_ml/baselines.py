"""Reproducible mouse baseline training and evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score  # type: ignore[import-untyped]
from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from botguard_ml.splits import grouped_split

METADATA_COLUMNS = {
    "dataset",
    "domain",
    "session_id",
    "subject_id",
    "split_group",
    "label",
    "bot_type",
    "window_index",
    "session_index",
}


def load_feature_rows(input_root: Path) -> pd.DataFrame:
    """Load feature shards and reject missing required metadata."""
    paths = sorted(input_root.glob("*.parquet"))
    if not paths:
        raise ValueError(f"no feature shards found under {input_root}")
    frames = [pq.read_table(path).to_pandas() for path in paths]
    rows = pd.concat(frames, ignore_index=True)
    required = {"split_group", "label", "dataset", "domain", "bot_type"}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"feature shards missing columns: {', '.join(sorted(missing))}")
    return rows


def _feature_columns(rows: pd.DataFrame) -> list[str]:
    columns = [
        column
        for column in rows.columns
        if column not in METADATA_COLUMNS and pd.api.types.is_numeric_dtype(rows[column])
    ]
    if not columns:
        raise ValueError("feature shards contain no numeric feature columns")
    return columns


def _metrics(y_true: np.ndarray, scores: np.ndarray, predictions: np.ndarray) -> dict[str, float]:
    result = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
    }
    result["roc_auc"] = (
        float(roc_auc_score(y_true, scores)) if len(np.unique(y_true)) == 2 else float("nan")
    )
    return result


def run_baselines(
    rows: Sequence[dict[str, Any]] | pd.DataFrame,
    *,
    test_size: float = 0.2,
    seed: int = 42,
) -> pd.DataFrame:
    """Fit four baselines on one identical grouped train/test split."""
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    metadata = frame.to_dict("records")
    train_indices, test_indices = grouped_split(metadata, test_size=test_size, seed=seed)
    features = _feature_columns(frame)
    x_train = frame.iloc[train_indices][features]
    x_test = frame.iloc[test_indices][features]
    y_train = frame.iloc[train_indices]["label"].to_numpy(dtype=int)
    y_test = frame.iloc[test_indices]["label"].to_numpy(dtype=int)
    if len(np.unique(y_train)) < 2:
        raise ValueError("training split must contain both labels")

    models: dict[str, Any] = {
        "logistic_regression": make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=seed),
        ),
        "random_forest": make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=1),
        ),
        "lightgbm": make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                num_leaves=31,
                random_state=seed,
                verbosity=-1,
            ),
        ),
    }
    majority = int(np.mean(y_train) >= 0.5)
    results = [
        {
            "model": "majority",
            **_metrics(
                y_test, np.full(len(y_test), majority, dtype=float), np.full(len(y_test), majority)
            ),
            "n_train": len(train_indices),
            "n_test": len(test_indices),
            "n_train_groups": len({metadata[index]["split_group"] for index in train_indices}),
            "n_test_groups": len({metadata[index]["split_group"] for index in test_indices}),
        }
    ]
    for name, model in models.items():
        model.fit(x_train, y_train)
        scores = model.predict_proba(x_test)[:, 1]
        predictions = (scores >= 0.5).astype(int)
        results.append(
            {
                "model": name,
                **_metrics(y_test, scores, predictions),
                "n_train": len(train_indices),
                "n_test": len(test_indices),
                "n_train_groups": len({metadata[index]["split_group"] for index in train_indices}),
                "n_test_groups": len({metadata[index]["split_group"] for index in test_indices}),
            }
        )
    return pd.DataFrame(results)

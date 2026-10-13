"""SHAP explanations for mouse LightGBM scores."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import shap  # type: ignore[import-untyped]
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]


def top_contributing_features(
    shap_values: np.ndarray,
    feature_names: Sequence[str],
    *,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Return the largest absolute SHAP contributors for each scored row."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    values = np.asarray(shap_values, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(feature_names):
        raise ValueError("SHAP values must be a 2D array matching feature_names")
    count = min(top_k, values.shape[1])
    result = []
    for row_index, row in enumerate(values):
        indices = np.argsort(-np.abs(row), kind="stable")[:count]
        result.append(
            {
                "row_index": row_index,
                "features": [
                    {
                        "feature": feature_names[index],
                        "contribution": float(row[index]),
                        "abs_contribution": float(abs(row[index])),
                    }
                    for index in indices
                ],
            }
        )
    return result


def shap_summary(
    shap_values: np.ndarray,
    feature_names: Sequence[str],
) -> pd.DataFrame:
    """Summarize mean signed and absolute SHAP contributions by feature."""
    values = np.asarray(shap_values, dtype=float)
    if values.ndim != 2 or values.shape[1] != len(feature_names):
        raise ValueError("SHAP values must be a 2D array matching feature_names")
    summary = pd.DataFrame(
        {
            "feature": list(feature_names),
            "mean_abs_shap": np.mean(np.abs(values), axis=0),
            "mean_shap": np.mean(values, axis=0),
        }
    )
    return summary.sort_values("mean_abs_shap", ascending=False, ignore_index=True).assign(
        rank=lambda frame: np.arange(1, len(frame) + 1)
    )


def explain_lightgbm(
    x_train: pd.DataFrame,
    x_scored: pd.DataFrame,
    y_train: np.ndarray,
    *,
    seed: int = 42,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Fit the baseline LightGBM model and explain scored rows with SHAP."""
    if len(np.unique(y_train)) < 2:
        raise ValueError("training data must contain both labels")
    if list(x_train.columns) != list(x_scored.columns):
        raise ValueError("training and scored features must have identical columns")
    imputer = SimpleImputer(strategy="median")
    train_values = imputer.fit_transform(x_train)
    scored_values = imputer.transform(x_scored)
    model = LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        num_leaves=31,
        random_state=seed,
        n_jobs=1,
        verbosity=-1,
    )
    model.fit(train_values, y_train)
    values = shap.TreeExplainer(model).shap_values(scored_values)
    if isinstance(values, list):
        values = values[1]
    array = np.asarray(values, dtype=float)
    return shap_summary(array, list(x_train.columns)), top_contributing_features(
        array, list(x_train.columns)
    )

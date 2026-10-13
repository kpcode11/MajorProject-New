"""Feature-group and shortcut-feature ablation experiments."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.impute import SimpleImputer  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import roc_auc_score  # type: ignore[import-untyped]
from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from botguard_ml.baselines import _feature_columns
from botguard_ml.splits import grouped_split

SHORTCUTS = {"n_points", "duration_ms", "dt_mean", "dt_mode_fraction"}
GROUP_PREFIXES = {
    "kinematics": (
        "speed_",
        "acc_",
        "jerk_",
        "ang_vel_",
        "curvature_",
    ),
    "geometry": (
        "path_length",
        "displacement",
        "straightness",
        "n_direction_changes",
        "direction_change_rate",
        "bbox_area_norm",
        "tail_reversal_ratio",
    ),
    "timing": (
        "duration_ms",
        "n_points",
        "dt_",
        "pause_",
        "speed_peak_position",
        "accel_phase_ratio",
        "window_",
    ),
    "click": ("click_", "pre_click_"),
}


def _base_name(column: str) -> str:
    for suffix in ("_mean", "_std", "_max"):
        if column.endswith(suffix):
            return column[: -len(suffix)]
    return column


def _group_columns(columns: Sequence[str], group: str) -> list[str]:
    prefixes = GROUP_PREFIXES[group]
    selected = [column for column in columns if _base_name(column).startswith(prefixes)]
    if not selected:
        raise ValueError(f"no columns found for feature group {group}")
    return selected


def run_ablations(
    rows: pd.DataFrame,
    *,
    test_size: float = 0.2,
    seed: int = 42,
) -> pd.DataFrame:
    """Evaluate feature groups and shortcut inclusion on one grouped split."""
    metadata = rows.to_dict("records")
    train_indices, test_indices = grouped_split(metadata, test_size=test_size, seed=seed)
    all_features = _feature_columns(rows)
    configurations: list[tuple[str, list[str]]] = [
        ("all_with_shortcuts", all_features),
        (
            "all_without_shortcuts",
            [column for column in all_features if _base_name(column) not in SHORTCUTS],
        ),
    ]
    configurations.extend(
        (f"group_{group}", _group_columns(all_features, group)) for group in GROUP_PREFIXES
    )
    y_train = rows.iloc[train_indices]["label"].to_numpy(dtype=int)
    y_test = rows.iloc[test_indices]["label"].to_numpy(dtype=int)
    if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        raise ValueError("both split partitions must contain both labels")
    results: list[dict[str, Any]] = []
    for name, features in configurations:
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=seed),
        )
        model.fit(rows.iloc[train_indices][features], y_train)
        scores = model.predict_proba(rows.iloc[test_indices][features])[:, 1]
        results.append(
            {
                "configuration": name,
                "model": "logistic_regression",
                "roc_auc": float(roc_auc_score(y_test, scores)),
                "n_features": len(features),
                "n_train_groups": len({metadata[i]["split_group"] for i in train_indices}),
                "n_test_groups": len({metadata[i]["split_group"] for i in test_indices}),
            }
        )
    return pd.DataFrame(results)

"""Tests for identical-split mouse baselines."""

from __future__ import annotations

import numpy as np
import pandas as pd

from botguard_ml.baselines import run_baselines


def _rows() -> pd.DataFrame:
    rows = []
    for group in range(12):
        label = group % 2
        for window in range(2):
            rows.append(
                {
                    "dataset": "fixture",
                    "domain": "test",
                    "session_id": f"s{group}",
                    "subject_id": f"s{group}",
                    "split_group": f"g{group}",
                    "label": label,
                    "bot_type": "bot" if label else "human",
                    "speed_mean_mean": float(label * 10 + window),
                    "straightness_mean": float(1 - label * 0.5),
                }
            )
    return pd.DataFrame(rows)


def test_baselines_share_split_and_return_all_models() -> None:
    result = run_baselines(_rows(), test_size=0.25, seed=3)

    assert set(result["model"]) == {
        "majority",
        "logistic_regression",
        "random_forest",
        "lightgbm",
    }
    assert result["n_train_groups"].nunique() == 1
    assert result["n_test_groups"].nunique() == 1
    assert np.all((result["accuracy"] >= 0) & (result["accuracy"] <= 1))

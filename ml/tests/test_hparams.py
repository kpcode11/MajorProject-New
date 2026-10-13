"""Tests for grouped LightGBM hyperparameter optimisation."""

from __future__ import annotations

import pandas as pd

from botguard_ml.hparams import optimise_lightgbm


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


def test_optimisation_uses_grouped_training_cv() -> None:
    result = optimise_lightgbm(_rows(), n_trials=2, timeout_seconds=30, seed=3)

    assert result["n_trials_completed"] == 2
    assert result["cv_folds"] == 5
    assert result["n_train_groups"] == 10
    assert result["n_test_groups"] == 2
    assert result["feature_columns"] == ["speed_mean_mean", "straightness_mean"]

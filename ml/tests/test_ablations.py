"""Tests for mouse feature ablations."""

from __future__ import annotations

import pandas as pd

from botguard_ml.ablations import run_ablations


def test_ablation_configurations_share_grouped_split() -> None:
    rows = []
    for group in range(10):
        label = int(group >= 5)
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
                    "speed_mean_mean": float(label + window),
                    "path_length_mean": float(label + window),
                    "duration_ms_mean": float(100 + window),
                    "click_dwell_mean_mean": float(label),
                }
            )
    result = run_ablations(pd.DataFrame(rows), test_size=0.2, seed=3)

    assert set(result["configuration"]) == {
        "all_with_shortcuts",
        "all_without_shortcuts",
        "group_kinematics",
        "group_geometry",
        "group_timing",
        "group_click",
    }
    assert result["n_train_groups"].nunique() == 1
    assert result["n_test_groups"].nunique() == 1

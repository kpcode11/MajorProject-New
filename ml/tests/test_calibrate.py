"""Tests for grouped score calibration."""

from __future__ import annotations

import pandas as pd
import pytest

from botguard_ml.calibrate import calibrate_scores


def _rows() -> pd.DataFrame:
    rows = []
    for group in range(20):
        label = group % 2
        for window in range(2):
            rows.append(
                {
                    "split_group": f"g{group}",
                    "label": label,
                    "score": 0.15 + 0.7 * label + 0.01 * window,
                }
            )
    return pd.DataFrame(rows)


@pytest.mark.parametrize("method", ["isotonic", "platt"])
def test_calibration_uses_disjoint_group_partitions(method: str) -> None:
    result = calibrate_scores(_rows(), method=method, calibration_size=0.2, test_size=0.2, seed=4)

    assert result["method"] == method
    assert result["n_train_groups"] == 12
    assert result["n_calibration_groups"] == 4
    assert result["n_test_groups"] == 4
    assert 0.0 <= result["calibrated_brier"] <= 1.0
    assert result["reliability"]


def test_rejects_unknown_method() -> None:
    with pytest.raises(ValueError, match="isotonic or platt"):
        calibrate_scores(_rows(), method="unknown")

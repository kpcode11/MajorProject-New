"""Tests for session-level mouse score aggregation."""

from __future__ import annotations

import pandas as pd
import pytest

from botguard_ml.aggregation import aggregate_scores, compare_aggregators


def _rows() -> pd.DataFrame:
    rows = []
    for session in range(12):
        label = session % 2
        for window in range(3):
            rows.append(
                {
                    "dataset": "fixture",
                    "domain": "test",
                    "session_id": f"s{session}",
                    "split_group": f"g{session}",
                    "label": label,
                    "bot_type": "bot" if label else "human",
                    "score": 0.1 + 0.2 * label + 0.1 * window,
                }
            )
    return pd.DataFrame(rows)


def test_aggregate_rules() -> None:
    assert aggregate_scores([0.1, 0.5, 0.2], "mean") == pytest.approx(0.2666667)
    assert aggregate_scores([0.1, 0.5, 0.2], "max") == 0.5
    assert aggregate_scores([0.1, 0.5, 0.2], "top_k_mean", top_k=2) == pytest.approx(0.35)


def test_comparison_uses_validation_sessions() -> None:
    result, selected = compare_aggregators(_rows(), test_size=0.25, seed=3)

    assert set(result["method"]) == {"mean", "top_k_mean", "max", "learned_logistic"}
    assert selected in set(result["method"])
    assert result["n_train_sessions"].nunique() == 1
    assert result["n_validation_sessions"].nunique() == 1

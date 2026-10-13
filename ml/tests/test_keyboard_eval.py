"""Tests for grouped keyboard evaluation."""

from __future__ import annotations

import pandas as pd

from botguard_ml.keyboard_eval import evaluate_keyboard


def test_keyboard_evaluation_reports_generators_and_speed_terciles() -> None:
    rows = []
    for group in range(12):
        label = int(group >= 6)
        bot_type = "human" if not label else ("K1" if group % 2 else "K2")
        for window in range(2):
            rows.append(
                {
                    "dataset": "synthetic",
                    "domain": "typing_test",
                    "session_id": f"s{group}",
                    "subject_id": f"s{group}",
                    "split_group": f"g{group}",
                    "label": label,
                    "bot_type": bot_type,
                    "typing_speed_cps": float(group + window + 1),
                    "dwell_mean": float(40 - 10 * label),
                    "flight_mean": float(100 - 20 * label),
                }
            )
    result = evaluate_keyboard(pd.DataFrame(rows), test_size=0.5, n_bootstrap=10, seed=3)

    groups = set(result["group"])
    assert "overall" in groups
    assert "generator:K1" in groups
    assert "generator:K2" in groups
    assert "human_fpr" in groups
    assert any(group.startswith("speed_tercile:") for group in groups)


def test_k3_is_forced_into_test_and_not_training() -> None:
    rows = []
    for group in range(8):
        label = int(group >= 4)
        rows.append(
            {
                "dataset": "synthetic",
                "domain": "typing_test",
                "session_id": f"s{group}",
                "subject_id": f"s{group}",
                "split_group": f"g{group}",
                "label": label,
                "bot_type": "K3" if group == 7 else ("human" if not label else "K1"),
                "typing_speed_cps": float(group + 1),
                "dwell_mean": float(40 - 5 * label),
            }
        )
    result = evaluate_keyboard(pd.DataFrame(rows), n_bootstrap=5)

    assert "generator:K3" in set(result["group"])

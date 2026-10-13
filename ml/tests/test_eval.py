"""Tests for mouse evaluation and group bootstrap metrics."""

from __future__ import annotations

import pandas as pd
import pytest

from botguard_ml.eval import evaluate_scores, grouped_bootstrap, human_fpr_by_game_type


def _rows() -> pd.DataFrame:
    rows = []
    for group in range(10):
        label = int(group >= 5)
        for window in range(2):
            rows.append(
                {
                    "dataset": "bournemouth",
                    "domain": "wiki_part1" if group < 5 else "wiki_part2",
                    "bot_type": "human" if not label else "moderate",
                    "split_group": f"g{group}",
                    "label": label,
                    "score": 0.1 + 0.8 * label + 0.01 * window,
                }
            )
    return pd.DataFrame(rows)


def test_evaluation_reports_metrics_and_group_ci() -> None:
    result = evaluate_scores(_rows(), n_bootstrap=20, seed=4)

    assert result.loc[0, "status"] == "ok"
    assert result.loc[0, "n_groups"] == 2
    assert (
        result.loc[0, "roc_auc_ci_low"]
        <= result.loc[0, "roc_auc"]
        <= result.loc[0, "roc_auc_ci_high"]
    )


def test_cross_phase_and_human_fpr_report() -> None:
    result = evaluate_scores(_rows(), split="cross_phase", n_bootstrap=10)
    assert result.loc[0, "n_groups"] == 5
    games = _rows().assign(gameType=["grid" if index % 2 else "image" for index in range(20)])
    fpr = human_fpr_by_game_type(games, threshold=0.5)
    assert set(fpr["game_type"]) == {"grid", "image"}


def test_bootstrap_requires_multiple_groups() -> None:
    with pytest.raises(ValueError, match="two groups"):
        grouped_bootstrap(_rows().iloc[:2], lambda labels, scores: float(scores.mean()))

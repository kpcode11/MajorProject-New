"""Evaluation and reporting utilities for model experiments."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)

from botguard_ml.splits import (
    cross_dataset_split,
    cross_phase_split,
    grouped_split,
    leave_one_bot_type_out,
)


def _metric_values(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    if len(np.unique(labels)) < 2:
        return {"status": "insufficient_data"}
    human = scores[labels == 0]
    bot = scores[labels == 1]
    threshold = float(np.quantile(human, 0.99)) if len(human) else 0.5
    predicted = scores >= threshold
    matrix = confusion_matrix(labels, predicted, labels=[0, 1])
    fpr = np.mean(predicted[labels == 0]) if len(human) else float("nan")
    return {
        "status": "ok",
        "roc_auc": float(roc_auc_score(labels, scores)),
        "pr_auc": float(average_precision_score(labels, scores)),
        "brier": float(brier_score_loss(labels, scores)),
        "threshold_1pct_human_fpr": threshold,
        "bot_recall_at_1pct_human_fpr": float(np.mean(predicted[labels == 1]))
        if len(bot)
        else float("nan"),
        "human_fpr_at_threshold": float(fpr),
        "tn": float(matrix[0, 0]),
        "fp": float(matrix[0, 1]),
        "fn": float(matrix[1, 0]),
        "tp": float(matrix[1, 1]),
    }


def grouped_bootstrap(
    rows: pd.DataFrame,
    metric: Callable[[np.ndarray, np.ndarray], float],
    *,
    n_resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    """Return a 95% group-bootstrap interval for a score metric."""
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    if "split_group" not in rows:
        raise ValueError("rows must include split_group")
    groups = [group for _, group in rows.groupby("split_group", sort=True)]
    if len(groups) < 2:
        raise ValueError("at least two groups are required for bootstrap")
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(n_resamples):
        sample = [groups[index] for index in rng.integers(0, len(groups), len(groups))]
        frame = pd.concat(sample, ignore_index=True)
        labels = frame["label"].to_numpy(dtype=int)
        if len(np.unique(labels)) < 2:
            continue
        try:
            value = float(
                metric(frame["label"].to_numpy(dtype=int), frame["score"].to_numpy(dtype=float))
            )
        except ValueError:
            continue
        if np.isfinite(value):
            values.append(value)
    if not values:
        raise ValueError("bootstrap produced no valid metric values")
    return tuple(np.quantile(values, [0.025, 0.975]).tolist())


def evaluate_scores(
    rows: pd.DataFrame,
    *,
    split: str = "in_distribution",
    test_phase: str = "wiki_part2",
    test_dataset: str | None = None,
    test_bot_type: str | None = None,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """Evaluate precomputed scores using an Appendix E split."""
    required = {"label", "score", "split_group", "dataset", "domain", "bot_type"}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"rows missing columns: {', '.join(sorted(missing))}")
    metadata = rows.to_dict("records")
    if split == "in_distribution":
        _, test_indices = grouped_split(metadata, test_size=0.2, seed=seed)
    elif split == "cross_phase":
        _, test_indices = cross_phase_split(metadata, test_phase=test_phase)
    elif split == "cross_dataset":
        if test_dataset is None:
            raise ValueError("test_dataset is required for cross_dataset")
        _, test_indices = cross_dataset_split(metadata, test_dataset=test_dataset)
    elif split == "leave_one_bot_type_out":
        if test_bot_type is None:
            raise ValueError("test_bot_type is required for leave_one_bot_type_out")
        _, test_indices = leave_one_bot_type_out(metadata, test_bot_type=test_bot_type)
    else:
        raise ValueError(f"unknown evaluation split: {split}")
    test = rows.iloc[test_indices].copy()
    labels = test["label"].to_numpy(dtype=int)
    scores = test["score"].to_numpy(dtype=float)
    metrics: dict[str, Any] = _metric_values(labels, scores)
    result: dict[str, Any] = {
        "split": split,
        "n_rows": len(test),
        "n_groups": test["split_group"].nunique(),
        **metrics,
    }
    if metrics.get("status") == "ok":
        for name, function in (
            ("roc_auc", roc_auc_score),
            ("pr_auc", average_precision_score),
        ):
            low, high = grouped_bootstrap(test, function, n_resamples=n_bootstrap, seed=seed)
            result[f"{name}_ci_low"] = low
            result[f"{name}_ci_high"] = high
    else:
        result["roc_auc_ci_low"] = float("nan")
        result["roc_auc_ci_high"] = float("nan")
    return pd.DataFrame([result])


def human_fpr_by_game_type(
    rows: pd.DataFrame, *, threshold: float, score_column: str = "score"
) -> pd.DataFrame:
    """Report flagged human share by CaptchaSolve30k game type."""
    required = {"gameType", "label", score_column}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"rows missing columns: {', '.join(sorted(missing))}")
    humans = rows[rows["label"] == 0].copy()
    if humans.empty:
        return pd.DataFrame(columns=["game_type", "n_rows", "flagged_share"])
    return (
        humans.assign(flagged=humans[score_column] >= threshold)
        .groupby("gameType", as_index=False)
        .agg(n_rows=(score_column, "size"), flagged_share=("flagged", "mean"))
        .rename(columns={"gameType": "game_type"})
    )

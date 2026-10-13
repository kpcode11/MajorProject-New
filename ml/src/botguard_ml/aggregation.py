"""Session-level aggregation of window bot scores."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import roc_auc_score  # type: ignore[import-untyped]
from sklearn.pipeline import make_pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from botguard_ml.splits import grouped_split


def aggregate_scores(scores: Sequence[float], method: str, *, top_k: int = 3) -> float:
    """Aggregate one session's window scores using a named rule."""
    values = np.asarray(scores, dtype=float)
    if values.size == 0:
        raise ValueError("at least one window score is required")
    if not np.all(np.isfinite(values)):
        raise ValueError("window scores must be finite")
    if method == "mean":
        return float(np.mean(values))
    if method == "max":
        return float(np.max(values))
    if method == "top_k_mean":
        if top_k < 1:
            raise ValueError("top_k must be positive")
        return float(np.mean(np.sort(values)[-top_k:]))
    raise ValueError(f"unknown aggregation method: {method}")


def _session_table(rows: pd.DataFrame, score_column: str) -> pd.DataFrame:
    required = {"session_id", "split_group", "label", score_column}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"rows missing columns: {', '.join(sorted(missing))}")
    records: list[dict[str, Any]] = []
    for session_id, group in rows.groupby("session_id", sort=True):
        scores = group[score_column].to_numpy(dtype=float)
        records.append(
            {
                "session_id": str(session_id),
                "split_group": str(group["split_group"].iloc[0]),
                "label": int(group["label"].iloc[0]),
                "dataset": str(group["dataset"].iloc[0]),
                "domain": str(group["domain"].iloc[0]),
                "bot_type": str(group["bot_type"].iloc[0]),
                "mean": aggregate_scores(scores, "mean"),
                "max": aggregate_scores(scores, "max"),
                "top_k_mean": aggregate_scores(scores, "top_k_mean"),
                "std": float(np.std(scores)),
            }
        )
    if len(records) < 2:
        raise ValueError("at least two sessions are required")
    return pd.DataFrame(records)


def compare_aggregators(
    rows: pd.DataFrame,
    *,
    score_column: str = "score",
    test_size: float = 0.2,
    seed: int = 42,
) -> tuple[pd.DataFrame, str]:
    """Compare rules and a learned aggregator on a grouped validation split."""
    sessions = _session_table(rows, score_column)
    metadata = sessions.to_dict("records")
    train_indices, valid_indices = grouped_split(metadata, test_size=test_size, seed=seed)
    train = sessions.iloc[train_indices]
    valid = sessions.iloc[valid_indices]
    results: list[dict[str, Any]] = []
    for method in ("mean", "top_k_mean", "max"):
        scores = valid[method].to_numpy(dtype=float)
        results.append(
            {
                "method": method,
                "validation_roc_auc": float(roc_auc_score(valid["label"], scores)),
                "n_train_sessions": len(train),
                "n_validation_sessions": len(valid),
            }
        )

    learned_features = ["mean", "top_k_mean", "max", "std"]
    learned = make_pipeline(StandardScaler(), LogisticRegression(random_state=seed))
    learned.fit(train[learned_features], train["label"])
    learned_scores = learned.predict_proba(valid[learned_features])[:, 1]
    results.append(
        {
            "method": "learned_logistic",
            "validation_roc_auc": float(roc_auc_score(valid["label"], learned_scores)),
            "n_train_sessions": len(train),
            "n_validation_sessions": len(valid),
        }
    )
    result_frame = pd.DataFrame(results).sort_values(
        ["validation_roc_auc", "method"], ascending=[False, True]
    )
    return result_frame.reset_index(drop=True), str(result_frame.iloc[0]["method"])

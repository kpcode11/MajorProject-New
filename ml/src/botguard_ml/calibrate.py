"""Probability calibration utilities."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.metrics import brier_score_loss  # type: ignore[import-untyped]


def _three_way_groups(
    rows: Sequence[dict[str, Any]], *, calibration_size: float, test_size: float, seed: int
) -> tuple[list[int], list[int], list[int]]:
    if calibration_size <= 0 or test_size <= 0 or calibration_size + test_size >= 1:
        raise ValueError("calibration_size and test_size must be positive and sum below one")
    groups = sorted({str(row["split_group"]) for row in rows})
    if len(groups) < 3:
        raise ValueError("at least three split groups are required")
    shuffled = groups[:]
    rng = np.random.default_rng(seed)
    rng.shuffle(shuffled)
    n_calibration = max(1, round(len(groups) * calibration_size))
    n_test = max(1, round(len(groups) * test_size))
    if n_calibration + n_test >= len(groups):
        n_test = len(groups) - n_calibration - 1
    calibration_groups = set(shuffled[:n_calibration])
    test_groups = set(shuffled[n_calibration : n_calibration + n_test])
    train = [
        i
        for i, row in enumerate(rows)
        if str(row["split_group"]) not in calibration_groups | test_groups
    ]
    calibration = [i for i, row in enumerate(rows) if str(row["split_group"]) in calibration_groups]
    test = [i for i, row in enumerate(rows) if str(row["split_group"]) in test_groups]
    if not train or not calibration or not test:
        raise ValueError("three-way split produced an empty partition")
    return train, calibration, test


def _reliability(
    labels: np.ndarray, probabilities: np.ndarray, *, bins: int
) -> list[dict[str, float]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    records: list[dict[str, float]] = []
    for index in range(bins):
        mask = (probabilities >= edges[index]) & (
            probabilities <= edges[index + 1]
            if index == bins - 1
            else probabilities < edges[index + 1]
        )
        if not np.any(mask):
            continue
        records.append(
            {
                "bin_lower": float(edges[index]),
                "bin_upper": float(edges[index + 1]),
                "mean_predicted": float(np.mean(probabilities[mask])),
                "fraction_positive": float(np.mean(labels[mask])),
                "count": float(np.sum(mask)),
            }
        )
    return records


def calibrate_scores(
    rows: pd.DataFrame,
    *,
    score_column: str = "score",
    method: str = "isotonic",
    calibration_size: float = 0.15,
    test_size: float = 0.2,
    bins: int = 10,
    seed: int = 42,
) -> dict[str, Any]:
    """Fit calibration on separate groups and evaluate held-out probabilities."""
    if method not in {"isotonic", "platt"}:
        raise ValueError("method must be isotonic or platt")
    if bins < 2:
        raise ValueError("bins must be at least two")
    required = {"split_group", "label", score_column}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"rows missing columns: {', '.join(sorted(missing))}")
    frame = rows.copy()
    metadata = frame.to_dict("records")
    train, calibration, test = _three_way_groups(
        metadata, calibration_size=calibration_size, test_size=test_size, seed=seed
    )
    raw_calibration = frame.iloc[calibration][score_column].to_numpy(dtype=float)
    y_calibration = frame.iloc[calibration]["label"].to_numpy(dtype=int)
    raw_test = frame.iloc[test][score_column].to_numpy(dtype=float)
    y_test = frame.iloc[test]["label"].to_numpy(dtype=int)
    if len(np.unique(y_calibration)) < 2 or len(np.unique(y_test)) < 2:
        raise ValueError("calibration and test partitions must contain both labels")
    if method == "isotonic":
        calibrator: Any = IsotonicRegression(out_of_bounds="clip")
        calibrator.fit(raw_calibration, y_calibration)
        calibrated = np.asarray(calibrator.predict(raw_test), dtype=float)
    else:
        calibrator = LogisticRegression(random_state=seed)
        calibrator.fit(raw_calibration.reshape(-1, 1), y_calibration)
        calibrated = calibrator.predict_proba(raw_test.reshape(-1, 1))[:, 1]
    calibrated = np.clip(calibrated, 0.0, 1.0)
    return {
        "method": method,
        "seed": seed,
        "calibration_size": calibration_size,
        "test_size": test_size,
        "n_train_rows": len(train),
        "n_calibration_rows": len(calibration),
        "n_test_rows": len(test),
        "n_train_groups": len({metadata[i]["split_group"] for i in train}),
        "n_calibration_groups": len({metadata[i]["split_group"] for i in calibration}),
        "n_test_groups": len({metadata[i]["split_group"] for i in test}),
        "raw_brier": float(brier_score_loss(y_test, raw_test)),
        "calibrated_brier": float(brier_score_loss(y_test, calibrated)),
        "reliability": _reliability(y_test, calibrated, bins=bins),
    }

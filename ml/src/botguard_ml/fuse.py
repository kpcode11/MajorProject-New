"""Multimodal score-fusion utilities for pseudo-session evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]

from botguard_ml.splits import grouped_split


def fuse_scores(
    mouse_score: float | None,
    keyboard_score: float | None,
    method: str,
) -> float | None:
    """Fuse available calibrated probabilities without treating absence as bot."""
    values = [score for score in (mouse_score, keyboard_score) if score is not None]
    if not values:
        return None
    if method == "mouse_only":
        return mouse_score
    if method == "keyboard_only":
        return keyboard_score
    if method == "average":
        return float(np.mean(values))
    if method == "noisy_or":
        return float(1.0 - np.prod([1.0 - value for value in values]))
    raise ValueError(f"unknown fusion method: {method}")


def pair_pseudo_sessions(
    mouse: pd.DataFrame,
    keyboard: pd.DataFrame,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    """Pair same-class windows into deterministic pseudo-sessions."""
    required = {"label", "score"}
    for name, frame in (("mouse", mouse), ("keyboard", keyboard)):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} rows missing columns: {', '.join(sorted(missing))}")
    rng = np.random.default_rng(seed)
    records: list[dict[str, Any]] = []
    for label in sorted(set(mouse["label"]) | set(keyboard["label"])):
        mouse_rows = mouse[mouse["label"] == label].reset_index(drop=True)
        keyboard_rows = keyboard[keyboard["label"] == label].reset_index(drop=True)
        count = min(len(mouse_rows), len(keyboard_rows))
        if count == 0:
            continue
        mouse_indices = rng.permutation(len(mouse_rows))[:count]
        keyboard_indices = rng.permutation(len(keyboard_rows))[:count]
        for index, (mouse_index, keyboard_index) in enumerate(
            zip(mouse_indices, keyboard_indices, strict=True)
        ):
            records.append(
                {
                    "session_id": f"pseudo:{label}:{index}",
                    "label": int(label),
                    "split_group": f"pseudo:{label}:{index}",
                    "mouse_score": float(mouse_rows.iloc[mouse_index]["score"]),
                    "keyboard_score": float(keyboard_rows.iloc[keyboard_index]["score"]),
                }
            )
    return pd.DataFrame(records)


def evaluate_fusion(rows: pd.DataFrame, *, seed: int = 42) -> pd.DataFrame:
    """Compare mouse-only, keyboard-only, average, noisy-OR, and stacker scores."""
    required = {"label", "mouse_score", "keyboard_score"}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"rows missing columns: {', '.join(sorted(missing))}")
    result: list[dict[str, Any]] = []
    for method in ("mouse_only", "keyboard_only", "average", "noisy_or"):
        records = rows.itertuples()
        scores = [fuse_scores(row.mouse_score, row.keyboard_score, method) for row in records]
        usable = np.asarray([score for score in scores if score is not None], dtype=float)
        labels = rows["label"].to_numpy(dtype=int)
        result.append(
            {
                "method": method,
                "n_rows": len(usable),
                "evaluation_label": "pseudo-session evaluation (simulated pairing)",
                "scores": usable,
                "labels": labels,
            }
        )
    both = rows.dropna(subset=["mouse_score", "keyboard_score"]).reset_index(drop=True)
    if len(both) >= 4 and both["label"].nunique() == 2:
        if "split_group" in both:
            train_indices, valid_indices = grouped_split(
                both.to_dict("records"), test_size=0.25, seed=seed
            )
            train = both.iloc[train_indices]
            valid = both.iloc[valid_indices]
        else:
            train = both
            valid = both
        if train["label"].nunique() < 2 or valid["label"].nunique() < 2:
            return pd.DataFrame(result).drop(columns=["scores", "labels"])
        stacker = LogisticRegression(random_state=seed)
        stacker.fit(train[["mouse_score", "keyboard_score"]], train["label"])
        result.append(
            {
                "method": "stacker",
                "n_rows": len(valid),
                "evaluation_label": "pseudo-session evaluation (simulated pairing)",
                "scores": stacker.predict_proba(valid[["mouse_score", "keyboard_score"]])[:, 1],
                "labels": valid["label"].to_numpy(dtype=int),
            }
        )
    return pd.DataFrame(result).drop(columns=["scores", "labels"])


def write_fusion_metadata(
    output_dir: Path,
    *,
    version: str = "v1",
    seed: int = 42,
) -> dict[str, Any]:
    """Write deployment metadata for pseudo-session fusion."""
    metadata = {
        "version": version,
        "seed": seed,
        "evaluation_label": "pseudo-session evaluation (simulated pairing)",
        "methods": ["mouse_only", "keyboard_only", "average", "noisy_or", "stacker"],
        "missing_modality_policy": "fuse only modalities that are available",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata

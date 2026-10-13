"""Tests for score-level desktop fusion."""

from __future__ import annotations

import pandas as pd

from botguard_ml.fuse import (
    evaluate_fusion,
    fuse_scores,
    pair_pseudo_sessions,
    write_fusion_metadata,
)


def test_missing_modalities_are_not_treated_as_bot() -> None:
    assert fuse_scores(None, None, "average") is None
    assert fuse_scores(0.2, None, "average") == 0.2
    assert fuse_scores(None, 0.7, "noisy_or") == 0.7
    assert fuse_scores(0.2, 0.7, "noisy_or") == 0.76


def test_pairing_is_same_class_and_seeded() -> None:
    mouse = pd.DataFrame({"label": [0, 0, 1], "score": [0.1, 0.2, 0.9]})
    keyboard = pd.DataFrame({"label": [0, 1, 1], "score": [0.3, 0.8, 0.95]})
    first = pair_pseudo_sessions(mouse, keyboard, seed=4)
    second = pair_pseudo_sessions(mouse, keyboard, seed=4)
    pd.testing.assert_frame_equal(first, second)
    assert set(first["label"]) == {0, 1}
    assert len(first) == 2


def test_fusion_evaluation_reports_required_rules() -> None:
    rows = pd.DataFrame(
        {
            "label": [0, 0, 1, 1],
            "mouse_score": [0.1, 0.2, 0.8, 0.9],
            "keyboard_score": [0.2, 0.3, 0.7, 0.95],
        }
    )
    result = evaluate_fusion(rows)
    assert {"mouse_only", "keyboard_only", "average", "noisy_or", "stacker"} == set(
        result["method"]
    )
    assert set(result["evaluation_label"]) == {"pseudo-session evaluation (simulated pairing)"}


def test_fusion_metadata_is_written(tmp_path) -> None:
    metadata = write_fusion_metadata(tmp_path)
    assert metadata["evaluation_label"] == "pseudo-session evaluation (simulated pairing)"
    assert (tmp_path / "metadata.json").exists()

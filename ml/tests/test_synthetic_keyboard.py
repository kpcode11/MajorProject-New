"""Tests for synthetic keyboard bot generators."""

from __future__ import annotations

import numpy as np
import pytest

from botguard_ml.synthetic.keyboard import (
    fit_human_timing,
    generate_keyboard,
)


@pytest.mark.parametrize("bot_type", ["K1", "K2", "K4"])
def test_generators_are_deterministic_and_labelled(bot_type: str) -> None:
    first = generate_keyboard(bot_type, n_keys=12, seed=4)
    second = generate_keyboard(bot_type, n_keys=12, seed=4)

    assert first == second
    assert len(first) == 12
    assert {event["label"] for event in first} == {1}
    assert {event["bot_type"] for event in first} == {bot_type}


def test_k3_requires_training_profile_and_uses_fitted_parameters() -> None:
    humans = [
        [
            {"down_ms": 0.0, "up_ms": 50.0},
            {"down_ms": 100.0, "up_ms": 150.0},
            {"down_ms": 200.0, "up_ms": 250.0},
        ]
    ]
    profile = fit_human_timing(humans)

    assert profile.dwell_mean == pytest.approx(np.log(50.0))
    assert profile.flight_mean == pytest.approx(np.log(50.0))
    with pytest.raises(ValueError, match="profile"):
        generate_keyboard("K3", n_keys=10, seed=1)
    assert generate_keyboard("K3", n_keys=10, seed=1, profile=profile)[0]["bot_type"] == "K3"


def test_k4_contains_burst_and_pause() -> None:
    events = generate_keyboard("K4", n_keys=20, seed=2)

    flights = [
        current["down_ms"] - previous["up_ms"] for previous, current in zip(events, events[1:])
    ]
    assert max(flights) > 500

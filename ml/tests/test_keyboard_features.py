"""Tests for text-agnostic keyboard features."""

from __future__ import annotations

import pytest

from botguard_ml.features.keyboard import keyboard_features


def test_constant_intervals_have_zero_dwell_cv() -> None:
    events = [
        {"down_ms": index * 120.0, "up_ms": index * 120.0 + 40.0, "key_class": "letter"}
        for index in range(10)
    ]

    features = keyboard_features(events)

    assert features["dwell_mean"] == pytest.approx(40.0)
    assert features["dwell_cv"] == pytest.approx(0.0)
    assert features["flight_mean"] == pytest.approx(80.0)
    assert features["n_keys"] == 10


def test_long_flights_create_pauses_and_burst_boundaries() -> None:
    events = [
        {"down_ms": 0.0, "up_ms": 20.0, "key_class": "letter"},
        {"down_ms": 100.0, "up_ms": 120.0, "key_class": "letter"},
        {"down_ms": 700.0, "up_ms": 720.0, "key_class": "letter"},
    ]

    features = keyboard_features(events)

    assert features["pause_count"] == 1
    assert features["burst_count"] == 2

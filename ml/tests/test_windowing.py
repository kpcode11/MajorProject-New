"""Tests for canonical mouse-event windowing."""

import pytest

from botguard_ml.features.windowing import window_events


def _move(t_ms: float, x: float = 1.0, y: float = 2.0) -> dict[str, object]:
    return {"t_ms": t_ms, "x": x, "y": y, "event": "move"}


def test_creates_overlapping_windows_and_drops_sparse_windows() -> None:
    events = [_move(float(index * 500)) for index in range(31)]

    windows = window_events(events, min_moves=2)

    assert len(windows) == 3
    assert [window[0]["t_ms"] for window in windows] == [0.0, 5000.0, 10000.0]
    assert windows[0][-1]["t_ms"] == 9500.0
    assert windows[1][0]["t_ms"] == 5000.0


def test_sorts_and_removes_duplicate_timestamp_coordinates() -> None:
    events = [
        _move(1000.0, 3.0, 4.0),
        {"t_ms": 1000.0, "x": 3.0, "y": 4.0, "event": "move"},
        {"t_ms": 1200.0, "x": 3.0, "y": 4.0, "event": "click"},
    ]

    windows = window_events(events, window_s=1.0, hop_s=1.0, min_moves=1)

    assert len(windows) == 1
    assert [event["t_ms"] for event in windows[0]] == [1000.0, 1200.0]


def test_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="window_s"):
        window_events([], window_s=0)
    with pytest.raises(ValueError, match="hop_s"):
        window_events([], hop_s=-1)
    with pytest.raises(ValueError, match="min_moves"):
        window_events([], min_moves=-1)

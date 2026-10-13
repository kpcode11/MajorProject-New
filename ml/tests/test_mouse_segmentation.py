"""Tests for mouse trajectory segmentation inside a window."""

import pytest

from botguard_ml.features.mouse import segment_trajectory


def _move(t_ms: float, x: float, y: float = 0.0) -> dict[str, object]:
    return {"t_ms": t_ms, "x": x, "y": y, "event": "move"}


def _stroke(start_t: float, start_x: float, n_points: int = 8, dt: float = 10.0, dx: float = 5.0):
    return [_move(start_t + index * dt, start_x + index * dx) for index in range(n_points)]


def test_splits_after_pause_without_move_events() -> None:
    first = _stroke(0.0, 0.0)
    second = _stroke(170.0, 100.0)

    segments = segment_trajectory([*first, *second], pause_ms=100.0)

    assert len(segments) == 2
    assert [event["t_ms"] for event in segments[0]] == [event["t_ms"] for event in first]
    assert [event["t_ms"] for event in segments[1]] == [event["t_ms"] for event in second]


def test_splits_at_click_down_and_up_boundaries() -> None:
    before = _stroke(0.0, 0.0)
    click = {"t_ms": 80.0, "x": 35.0, "y": 0.0, "event": "click"}
    after = _stroke(90.0, 50.0)
    down = {"t_ms": 200.0, "x": 85.0, "y": 0.0, "event": "down"}
    dragged = _stroke(210.0, 90.0)
    up = {"t_ms": 290.0, "x": 125.0, "y": 0.0, "event": "up"}

    segments = segment_trajectory([*before, click, *after, down, *dragged, up], pause_ms=1000.0)

    assert len(segments) == 3
    assert segments[0][-1]["event"] == "click"
    assert [event["event"] for event in segments[1]] == ["move"] * 8 + ["down"]
    assert segments[2][-1]["event"] == "up"


def test_drops_short_and_low_path_segments() -> None:
    too_few = _stroke(0.0, 0.0, n_points=7, dx=10.0)
    too_short = _stroke(200.0, 0.0, n_points=8, dx=1.0)
    kept = _stroke(400.0, 0.0, n_points=8, dx=5.0)

    segments = segment_trajectory([*too_few, *too_short, *kept], min_points=8, min_path_px=20.0)

    assert len(segments) == 1
    assert [event["t_ms"] for event in segments[0]] == [event["t_ms"] for event in kept]


def test_sorts_and_removes_duplicate_timestamp_coordinates() -> None:
    events = [
        _move(20.0, 10.0),
        _move(0.0, 0.0),
        _move(20.0, 10.0),
        _move(40.0, 20.0),
        _move(60.0, 30.0),
        _move(80.0, 40.0),
        _move(100.0, 50.0),
        _move(120.0, 60.0),
        _move(140.0, 70.0),
    ]

    segments = segment_trajectory(events, min_points=8, min_path_px=20.0)

    assert len(segments) == 1
    assert [event["t_ms"] for event in segments[0]] == [
        0.0,
        20.0,
        40.0,
        60.0,
        80.0,
        100.0,
        120.0,
        140.0,
    ]


def test_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="pause_ms"):
        segment_trajectory([], pause_ms=-1)
    with pytest.raises(ValueError, match="min_points"):
        segment_trajectory([], min_points=-1)
    with pytest.raises(ValueError, match="min_path_px"):
        segment_trajectory([], min_path_px=-1)

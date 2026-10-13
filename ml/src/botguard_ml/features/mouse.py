"""Segment canonical mouse-event windows into movement trajectories."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from botguard_ml.features.windowing import _deduplicate

BOUNDARY_EVENTS = frozenset({"down", "up", "click"})


def _validate_parameters(pause_ms: float, min_points: int, min_path_px: float) -> None:
    if not math.isfinite(pause_ms) or pause_ms < 0:
        raise ValueError("pause_ms must be finite and not negative")
    if min_points < 0:
        raise ValueError("min_points must not be negative")
    if not math.isfinite(min_path_px) or min_path_px < 0:
        raise ValueError("min_path_px must be finite and not negative")


def _path_length_px(events: list[dict[str, Any]]) -> float:
    length = 0.0
    previous: tuple[float, float] | None = None
    for event in events:
        x = event.get("x")
        y = event.get("y")
        if x is None or y is None:
            continue
        point = (float(x), float(y))
        if previous is not None:
            length += math.hypot(point[0] - previous[0], point[1] - previous[1])
        previous = point
    return length


def _keep_segment(events: list[dict[str, Any]], min_points: int, min_path_px: float) -> bool:
    return len(events) >= min_points and _path_length_px(events) >= min_path_px


def segment_trajectory(
    events: Iterable[dict[str, Any]],
    *,
    pause_ms: float = 100.0,
    min_points: int = 8,
    min_path_px: float = 20.0,
) -> list[list[dict[str, Any]]]:
    """Split one window into movement segments (Appendix A.1).

    Events are sorted and exact timestamp/coordinate duplicates are dropped.
    A new segment starts after ``pause_ms`` with no ``move`` events, or when a
    ``down``/``up``/``click`` boundary closes the current segment. Segments
    shorter than ``min_points`` or ``min_path_px`` are discarded. Returned
    events are copies.
    """
    _validate_parameters(pause_ms, min_points, min_path_px)
    cleaned = _deduplicate(events)
    segments: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    last_move_t: float | None = None

    def flush() -> None:
        nonlocal current
        if _keep_segment(current, min_points, min_path_px):
            segments.append(current)
        current = []

    for event in cleaned:
        item = dict(event)
        t_ms = float(item["t_ms"])
        kind = item.get("event")
        paused = current and last_move_t is not None and (t_ms - last_move_t) >= pause_ms
        if paused:
            flush()
            last_move_t = None
        if kind in BOUNDARY_EVENTS:
            current.append(item)
            flush()
            last_move_t = None
            continue
        current.append(item)
        if kind == "move":
            last_move_t = t_ms
    flush()
    return segments

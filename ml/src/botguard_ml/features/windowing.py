"""Window canonical mouse-event sessions for model training and serving."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any


def _validate_parameters(window_s: float, hop_s: float, min_moves: int) -> None:
    if not math.isfinite(window_s) or window_s <= 0:
        raise ValueError("window_s must be finite and greater than zero")
    if not math.isfinite(hop_s) or hop_s <= 0:
        raise ValueError("hop_s must be finite and greater than zero")
    if min_moves < 0:
        raise ValueError("min_moves must not be negative")


def _deduplicate(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort events and drop exact timestamp/coordinate duplicates."""
    ordered = sorted(events, key=lambda event: float(event["t_ms"]))
    result: list[dict[str, Any]] = []
    seen: set[tuple[float, Any, Any]] = set()
    for event in ordered:
        t_ms = float(event["t_ms"])
        key = (t_ms, event.get("x"), event.get("y"))
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(event))
    return result


def window_events(
    events: Iterable[dict[str, Any]],
    *,
    window_s: float = 10.0,
    hop_s: float = 5.0,
    min_moves: int = 20,
) -> list[list[dict[str, Any]]]:
    """Cut one canonical session into overlapping event windows.

    Windows use half-open time intervals ``[start, end)`` and begin at the
    session's first event timestamp. Events are copied so callers can safely
    modify a returned window without changing the source session.
    """
    _validate_parameters(window_s, hop_s, min_moves)
    cleaned = _deduplicate(events)
    if not cleaned:
        return []

    window_ms = window_s * 1000.0
    hop_ms = hop_s * 1000.0
    first_t = float(cleaned[0]["t_ms"])
    last_t = float(cleaned[-1]["t_ms"])
    windows: list[list[dict[str, Any]]] = []
    start = first_t
    while start <= last_t:
        end = start + window_ms
        batch = [dict(event) for event in cleaned if start <= float(event["t_ms"]) < end]
        move_count = sum(event.get("event") == "move" for event in batch)
        if move_count >= min_moves:
            windows.append(batch)
        start += hop_ms
    return windows

"""Segment canonical mouse-event windows and extract Appendix A.2 features."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from typing import Any

import numpy as np

from botguard_ml.features.windowing import _deduplicate

BOUNDARY_EVENTS = frozenset({"down", "up", "click"})
CLICK_EVENTS = frozenset({"down", "up", "click"})
SHORTCUT_FEATURES = frozenset({"n_points", "duration_ms", "dt_mean", "dt_mode_fraction"})
WINDOW_SHORTCUT_FEATURES = frozenset(
    {
        "window_n_points",
        "window_duration_ms",
        "window_dt_mean",
        "window_dt_mode_fraction",
    }
)
AGGREGATE_STATS = ("mean", "std", "max")
HEADING_CHANGE_RAD = math.radians(10.0)
DT_ROUND_MS = 1.0
PRE_CLICK_MS = 100.0

SEGMENT_FEATURE_DOCS: dict[str, str] = {
    "speed_mean": "Mean of interval speeds ds/dt. Units: px/s.",
    "speed_std": "Sample std of interval speeds. Units: px/s.",
    "speed_max": "Maximum interval speed. Units: px/s.",
    "speed_p25": "25th percentile of interval speeds. Units: px/s.",
    "speed_p50": "50th percentile of interval speeds. Units: px/s.",
    "speed_p75": "75th percentile of interval speeds. Units: px/s.",
    "speed_p95": "95th percentile of interval speeds. Units: px/s.",
    "acc_mean": "Mean of dv/dt on consecutive speeds. Units: px/s^2.",
    "acc_std": "Sample std of acceleration. Units: px/s^2.",
    "acc_max_abs": "Maximum |acceleration|. Units: px/s^2.",
    "acc_sign_change_rate": (
        "Fraction of consecutive non-zero accelerations that change sign. Units: 1."
    ),
    "jerk_mean_abs": "Mean |da/dt| of consecutive accelerations. Units: px/s^3.",
    "jerk_std": "Sample std of jerk. Units: px/s^3.",
    "ang_vel_mean_abs": "Mean |dtheta/dt| of heading changes. Units: rad/s.",
    "ang_vel_std": "Sample std of angular velocity. Units: rad/s.",
    "curvature_mean_abs": "Mean |dtheta/ds| of heading changes. Units: 1/px.",
    "curvature_std": "Sample std of curvature. Units: 1/px.",
    "path_length": "Sum of consecutive Euclidean steps. Units: px.",
    "displacement": "Straight-line distance from first to last point. Units: px.",
    "straightness": "displacement / path_length, clipped to [0, 1]. Units: 1.",
    "n_direction_changes": (
        "Sign changes of heading deltas with |dtheta| >= threshold. Units: count."
    ),
    "direction_change_rate": "n_direction_changes per 100 px of path. Units: 1/100px.",
    "bbox_area_norm": "Axis-aligned bbox area / (screen_w * screen_h), else NaN. Units: 1.",
    "tail_reversal_ratio": (
        "Path length after the interior point nearest the endpoint / path_length. Units: 1."
    ),
    "duration_ms": "Last timestamp minus first timestamp. Units: ms.",
    "n_points": "Number of coordinate samples in the segment. Units: count.",
    "dt_mean": "Mean of positive inter-sample intervals. Units: ms.",
    "dt_std": "Sample std of positive inter-sample intervals. Units: ms.",
    "dt_cv": "dt_std / dt_mean. Units: 1.",
    "dt_mode_fraction": "Share of intervals equal to the modal 1 ms-rounded interval. Units: 1.",
    "pause_count": "Number of inter-sample gaps strictly greater than pause_ms. Units: count.",
    "pause_total_ms": "Sum of inter-sample gaps strictly greater than pause_ms. Units: ms.",
    "speed_peak_position": "Time of first peak speed / duration_ms. Units: 1.",
    "accel_phase_ratio": "Time to peak speed / time from peak speed to end. Units: 1.",
    "click_dwell_mean": "Mean down-to-up dwell. Units: ms.",
    "click_dwell_std": "Sample std of down-to-up dwells. Units: ms.",
    "pre_click_slowdown": (
        "Mean speed in the 100 ms before the last click-like event / speed_mean. Units: 1."
    ),
}

SEGMENT_FEATURE_NAMES = tuple(SEGMENT_FEATURE_DOCS)


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


def _nan() -> float:
    return math.nan


def _mean(values: list[float]) -> float:
    if not values:
        return _nan()
    return float(sum(values) / len(values))


def _std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return _nan()
    mean = sum(values) / n
    return float(math.sqrt(sum((value - mean) ** 2 for value in values) / (n - 1)))


def _max(values: list[float]) -> float:
    return float(max(values)) if values else _nan()


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return _nan()
    return float(np.percentile(values, q))


def _percentiles_4(values: list[float]) -> tuple[float, float, float, float]:
    if not values:
        nan = _nan()
        return nan, nan, nan, nan
    p25, p50, p75, p95 = np.percentile(values, (25.0, 50.0, 75.0, 95.0))
    return float(p25), float(p50), float(p75), float(p95)


def _safe_div(numerator: float, denominator: float) -> float:
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator == 0:
        return _nan()
    return numerator / denominator


def _wrap_delta(delta: float) -> float:
    return float(math.atan2(math.sin(delta), math.cos(delta)))


def _sign_change_rate(values: list[float]) -> float:
    signs = [math.copysign(1.0, value) for value in values if value != 0]
    if not values:
        return _nan()
    if len(signs) < 2:
        return 0.0
    changes = sum(left != right for left, right in zip(signs, signs[1:], strict=False))
    return changes / (len(signs) - 1)


def _coordinate_points(events: Iterable[dict[str, Any]]) -> list[tuple[float, float, float]]:
    points: list[tuple[float, float, float]] = []
    for event in events:
        x = event.get("x")
        y = event.get("y")
        if x is None or y is None:
            continue
        points.append((float(event["t_ms"]), float(x), float(y)))
    points.sort(key=lambda point: point[0])
    return points


def _positive_intervals(
    points: list[tuple[float, float, float]],
) -> tuple[list[float], list[float], list[float], list[float], list[float], list[float]]:
    dt_ms: list[float] = []
    speeds: list[float] = []
    speed_end_t: list[float] = []
    headings: list[float] = []
    heading_end_t: list[float] = []
    heading_steps: list[float] = []
    for (t0, x0, y0), (t1, x1, y1) in zip(points, points[1:], strict=False):
        delta_t = t1 - t0
        if delta_t <= 0:
            continue
        dx = 0.0 if x1 - x0 == 0.0 else x1 - x0
        dy = 0.0 if y1 - y0 == 0.0 else y1 - y0
        step = math.hypot(dx, dy)
        dt_ms.append(delta_t)
        speeds.append(step / (delta_t / 1000.0))
        speed_end_t.append(t1)
        if step > 0:
            headings.append(math.atan2(dy, dx))
            heading_end_t.append(t1)
            heading_steps.append(step)
    return dt_ms, speeds, speed_end_t, headings, heading_end_t, heading_steps


def _derivative(values: list[float], times_ms: list[float]) -> tuple[list[float], list[float]]:
    derived: list[float] = []
    derived_t: list[float] = []
    for index in range(len(values) - 1):
        delta_t_s = (times_ms[index + 1] - times_ms[index]) / 1000.0
        if delta_t_s <= 0:
            continue
        derived.append((values[index + 1] - values[index]) / delta_t_s)
        derived_t.append(times_ms[index + 1])
    return derived, derived_t


def _mode_fraction(dt_ms: list[float], round_ms: float = DT_ROUND_MS) -> float:
    if not dt_ms:
        return _nan()
    rounded = [round(value / round_ms) * round_ms for value in dt_ms]
    counts = Counter(rounded)
    return max(counts.values()) / len(rounded)


def _screen_area(events: list[dict[str, Any]]) -> float:
    for event in events:
        width = event.get("screen_w")
        height = event.get("screen_h")
        if width is None or height is None:
            continue
        area = float(width) * float(height)
        if area > 0 and math.isfinite(area):
            return area
    return _nan()


def _tail_reversal_ratio(points: list[tuple[float, float, float]], path_length: float) -> float:
    if len(points) < 2 or path_length <= 0:
        return _nan()
    end_x, end_y = points[-1][1], points[-1][2]
    closest_index = min(
        range(len(points) - 1),
        key=lambda index: math.hypot(points[index][1] - end_x, points[index][2] - end_y),
    )
    tail = 0.0
    for (_, x0, y0), (_, x1, y1) in zip(
        points[closest_index:], points[closest_index + 1 :], strict=False
    ):
        tail += math.hypot(x1 - x0, y1 - y0)
    return tail / path_length


def _click_dwells(events: list[dict[str, Any]]) -> list[float]:
    dwells: list[float] = []
    down_t: float | None = None
    for event in events:
        kind = event.get("event")
        if kind == "down":
            down_t = float(event["t_ms"])
        elif kind == "up" and down_t is not None:
            dwell = float(event["t_ms"]) - down_t
            if dwell >= 0:
                dwells.append(dwell)
            down_t = None
    return dwells


def _timing_features(
    points: list[tuple[float, float, float]],
    dt_ms: list[float],
    *,
    pause_ms: float,
) -> dict[str, float]:
    duration_ms = points[-1][0] - points[0][0] if len(points) >= 2 else 0.0
    pauses = [value for value in dt_ms if value > pause_ms]
    dt_mean = _mean(dt_ms)
    dt_std = _std(dt_ms)
    return {
        "duration_ms": duration_ms,
        "n_points": float(len(points)),
        "dt_mean": dt_mean,
        "dt_std": dt_std,
        "dt_cv": _safe_div(dt_std, dt_mean),
        "dt_mode_fraction": _mode_fraction(dt_ms),
        "pause_count": float(len(pauses)),
        "pause_total_ms": float(sum(pauses)),
    }


def extract_segment_features(
    events: Iterable[dict[str, Any]],
    *,
    pause_ms: float = 100.0,
    heading_change_rad: float = HEADING_CHANGE_RAD,
) -> dict[str, float]:
    """Compute Appendix A.2 features for one movement segment.

    Kinematics use finite differences on ``(x, y, t)`` and skip non-positive
    ``dt``. Missing values are ``NaN``. See ``SEGMENT_FEATURE_DOCS`` for
    formulas and units.
    """
    if not math.isfinite(pause_ms) or pause_ms < 0:
        raise ValueError("pause_ms must be finite and not negative")
    if not math.isfinite(heading_change_rad) or heading_change_rad < 0:
        raise ValueError("heading_change_rad must be finite and not negative")

    rows = [dict(event) for event in events]
    points = _coordinate_points(rows)
    if len(points) < 2:
        return {name: _nan() for name in SEGMENT_FEATURE_NAMES}
    dt_ms, speeds, speed_end_t, headings, heading_end_t, heading_steps = _positive_intervals(points)
    accelerations, acc_t = _derivative(speeds, speed_end_t)
    jerks, _ = _derivative(accelerations, acc_t)

    angular_velocities: list[float] = []
    curvatures: list[float] = []
    heading_deltas: list[float] = []
    for index in range(len(headings) - 1):
        delta = _wrap_delta(headings[index + 1] - headings[index])
        heading_deltas.append(delta)
        delta_t_s = (heading_end_t[index + 1] - heading_end_t[index]) / 1000.0
        step = heading_steps[index + 1]
        if delta_t_s > 0:
            angular_velocities.append(delta / delta_t_s)
        if step > 0:
            curvatures.append(delta / step)

    path_length = _path_length_px(rows)
    displacement = math.hypot(points[-1][1] - points[0][1], points[-1][2] - points[0][2])
    straightness = _safe_div(displacement, path_length)
    if math.isfinite(straightness):
        straightness = min(1.0, max(0.0, straightness))
    significant = [delta for delta in heading_deltas if abs(delta) >= heading_change_rad]
    n_direction_changes = 0.0
    if len(significant) >= 2:
        n_direction_changes = float(
            sum(
                math.copysign(1.0, left) != math.copysign(1.0, right)
                for left, right in zip(significant, significant[1:], strict=False)
                if left != 0 and right != 0
            )
        )

    min_x = min((point[1] for point in points), default=_nan())
    max_x = max((point[1] for point in points), default=_nan())
    min_y = min((point[2] for point in points), default=_nan())
    max_y = max((point[2] for point in points), default=_nan())
    bbox_area = (max_x - min_x) * (max_y - min_y) if points else _nan()
    timing = _timing_features(points, dt_ms, pause_ms=pause_ms)
    duration_ms = timing["duration_ms"]

    peak_index = int(np.argmax(speeds)) if speeds else 0
    peak_t = speed_end_t[peak_index] - points[0][0] if speeds and points else _nan()
    time_after_peak = duration_ms - peak_t if math.isfinite(peak_t) else _nan()

    dwells = _click_dwells(rows)
    click_times = [float(event["t_ms"]) for event in rows if event.get("event") in CLICK_EVENTS]
    pre_click_speeds: list[float] = []
    if click_times:
        last_click = max(click_times)
        pre_click_speeds = [
            speed
            for speed, end_t in zip(speeds, speed_end_t, strict=False)
            if last_click - PRE_CLICK_MS <= end_t <= last_click
        ]

    speed_p25, speed_p50, speed_p75, speed_p95 = _percentiles_4(speeds)
    speed_mean = _mean(speeds)
    features = {
        "speed_mean": speed_mean,
        "speed_std": _std(speeds),
        "speed_max": _max(speeds),
        "speed_p25": speed_p25,
        "speed_p50": speed_p50,
        "speed_p75": speed_p75,
        "speed_p95": speed_p95,
        "acc_mean": _mean(accelerations),
        "acc_std": _std(accelerations),
        "acc_max_abs": _max([abs(value) for value in accelerations]),
        "acc_sign_change_rate": _sign_change_rate(accelerations),
        "jerk_mean_abs": _mean([abs(value) for value in jerks]),
        "jerk_std": _std(jerks),
        "ang_vel_mean_abs": _mean([abs(value) for value in angular_velocities]),
        "ang_vel_std": _std(angular_velocities),
        "curvature_mean_abs": _mean([abs(value) for value in curvatures]),
        "curvature_std": _std(curvatures),
        "path_length": path_length,
        "displacement": displacement,
        "straightness": straightness,
        "n_direction_changes": n_direction_changes,
        "direction_change_rate": _safe_div(n_direction_changes * 100.0, path_length),
        "bbox_area_norm": _safe_div(bbox_area, _screen_area(rows)),
        "tail_reversal_ratio": _tail_reversal_ratio(points, path_length),
        **timing,
        "speed_peak_position": _safe_div(peak_t, duration_ms),
        "accel_phase_ratio": _safe_div(peak_t, time_after_peak),
        "click_dwell_mean": _mean(dwells),
        "click_dwell_std": _std(dwells),
        "pre_click_slowdown": _safe_div(_mean(pre_click_speeds), speed_mean),
    }
    return {name: features[name] for name in SEGMENT_FEATURE_NAMES}


def _window_timing_features(events: list[dict[str, Any]], *, pause_ms: float) -> dict[str, float]:
    points = _coordinate_points(events)
    dt_ms, _, _, _, _, _ = _positive_intervals(points)
    timing = _timing_features(points, dt_ms, pause_ms=pause_ms)
    return {
        "window_duration_ms": timing["duration_ms"],
        "window_n_points": timing["n_points"],
        "window_dt_mean": timing["dt_mean"],
        "window_dt_std": timing["dt_std"],
        "window_dt_cv": timing["dt_cv"],
        "window_dt_mode_fraction": timing["dt_mode_fraction"],
        "window_pause_count": timing["pause_count"],
        "window_pause_total_ms": timing["pause_total_ms"],
    }


def extract_window_features(
    events: Iterable[dict[str, Any]],
    *,
    pause_ms: float = 100.0,
    min_points: int = 8,
    min_path_px: float = 20.0,
    heading_change_rad: float = HEADING_CHANGE_RAD,
    include_shortcut_features: bool = True,
) -> dict[str, float]:
    """Aggregate segment features with mean/std/max plus window timing stats."""
    rows = [dict(event) for event in events]
    segments = segment_trajectory(
        rows, pause_ms=pause_ms, min_points=min_points, min_path_px=min_path_px
    )
    segment_rows = [
        extract_segment_features(segment, pause_ms=pause_ms, heading_change_rad=heading_change_rad)
        for segment in segments
    ]
    window_dwells = _click_dwells(rows)
    aggregated: dict[str, float] = {}
    for name in SEGMENT_FEATURE_NAMES:
        if not include_shortcut_features and name in SHORTCUT_FEATURES:
            continue
        values = [row[name] for row in segment_rows if math.isfinite(row[name])]
        if not values and window_dwells:
            if name == "click_dwell_mean":
                values = window_dwells
            elif name == "click_dwell_std" and len(window_dwells) >= 2:
                values = [_std(window_dwells)]
        aggregated[f"{name}_mean"] = _mean(values)
        aggregated[f"{name}_std"] = _std(values)
        aggregated[f"{name}_max"] = _max(values)
    window_timing = _window_timing_features(rows, pause_ms=pause_ms)
    if not include_shortcut_features:
        window_timing = {
            key: value
            for key, value in window_timing.items()
            if key not in WINDOW_SHORTCUT_FEATURES
        }
    aggregated.update(window_timing)
    aggregated["n_segments"] = float(len(segments))
    return aggregated

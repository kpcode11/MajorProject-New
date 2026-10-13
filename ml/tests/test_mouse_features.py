"""Hand-computed and property tests for Appendix A.2 mouse features."""

from __future__ import annotations

import math

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from botguard_ml.features.mouse import (
    SEGMENT_FEATURE_DOCS,
    SEGMENT_FEATURE_NAMES,
    extract_segment_features,
    extract_window_features,
)


def _move(t_ms: float, x: float, y: float = 0.0, **extra: object) -> dict[str, object]:
    row: dict[str, object] = {"t_ms": t_ms, "x": x, "y": y, "event": "move"}
    row.update(extra)
    return row


def _straight_line() -> list[dict[str, object]]:
    return [_move(float(index * 100), float(index * 10)) for index in range(5)]


def _is_close(actual: float, expected: float, *, abs_tol: float = 1e-9) -> bool:
    if math.isnan(expected):
        return math.isnan(actual)
    return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=abs_tol)


def test_every_feature_has_formula_and_units_doc() -> None:
    assert tuple(SEGMENT_FEATURE_DOCS) == SEGMENT_FEATURE_NAMES
    for name, doc in SEGMENT_FEATURE_DOCS.items():
        assert "Units:" in doc, name
        assert len(doc) > 10, name


def test_straight_line_has_unit_straightness_and_zero_acceleration() -> None:
    features = extract_segment_features(_straight_line())

    expected = {
        "speed_mean": 100.0,
        "speed_std": 0.0,
        "speed_max": 100.0,
        "speed_p25": 100.0,
        "speed_p50": 100.0,
        "speed_p75": 100.0,
        "speed_p95": 100.0,
        "acc_mean": 0.0,
        "acc_std": 0.0,
        "acc_max_abs": 0.0,
        "acc_sign_change_rate": 0.0,
        "jerk_mean_abs": 0.0,
        "jerk_std": 0.0,
        "ang_vel_mean_abs": 0.0,
        "ang_vel_std": 0.0,
        "curvature_mean_abs": 0.0,
        "curvature_std": 0.0,
        "path_length": 40.0,
        "displacement": 40.0,
        "straightness": 1.0,
        "n_direction_changes": 0.0,
        "direction_change_rate": 0.0,
        "bbox_area_norm": math.nan,
        "tail_reversal_ratio": 0.25,
        "duration_ms": 400.0,
        "n_points": 5.0,
        "dt_mean": 100.0,
        "dt_std": 0.0,
        "dt_cv": 0.0,
        "dt_mode_fraction": 1.0,
        "pause_count": 0.0,
        "pause_total_ms": 0.0,
        "speed_peak_position": 0.25,
        "accel_phase_ratio": 100.0 / 300.0,
        "click_dwell_mean": math.nan,
        "click_dwell_std": math.nan,
        "pre_click_slowdown": math.nan,
    }
    assert set(features) == set(SEGMENT_FEATURE_NAMES)
    for name, value in expected.items():
        assert _is_close(features[name], value), f"{name}: {features[name]} != {value}"


def test_bbox_area_norm_uses_screen_size() -> None:
    events = [
        _move(float(index * 100), float(index * 10), 0.0, screen_w=200.0, screen_h=100.0)
        for index in range(5)
    ]

    features = extract_segment_features(events)

    assert _is_close(features["bbox_area_norm"], 0.0)


def test_direction_change_rate_is_per_100_px() -> None:
    events = [
        _move(0.0, 0.0, 0.0),
        _move(100.0, 10.0, 0.0),
        _move(200.0, 10.0, 10.0),
        _move(300.0, 20.0, 10.0),
    ]

    features = extract_segment_features(events)

    assert features["n_direction_changes"] == 1.0
    assert _is_close(features["path_length"], 30.0)
    assert _is_close(features["direction_change_rate"], 100.0 / 30.0)
    assert _is_close(features["displacement"], math.hypot(20.0, 10.0))
    assert _is_close(features["straightness"], math.hypot(20.0, 10.0) / 30.0)


def test_click_dwell_and_pre_click_slowdown() -> None:
    events = [
        {"t_ms": 0.0, "x": 0.0, "y": 0.0, "event": "down"},
        _move(0.0, 0.0),
        _move(100.0, 10.0),
        _move(200.0, 20.0),
        _move(300.0, 30.0),
        {"t_ms": 300.0, "x": 30.0, "y": 0.0, "event": "up"},
    ]

    features = extract_segment_features(events)

    assert _is_close(features["click_dwell_mean"], 300.0)
    assert math.isnan(features["click_dwell_std"])
    assert _is_close(features["pre_click_slowdown"], 1.0)
    assert _is_close(features["speed_mean"], 100.0)


def test_dt_mode_fraction_and_pause_timing() -> None:
    events = [
        _move(0.0, 0.0),
        _move(10.0, 5.0),
        _move(20.0, 10.0),
        _move(170.0, 15.0),
    ]

    features = extract_segment_features(events, pause_ms=100.0)

    assert _is_close(features["dt_mode_fraction"], 2.0 / 3.0)
    assert features["pause_count"] == 1.0
    assert _is_close(features["pause_total_ms"], 150.0)
    assert _is_close(features["dt_mean"], (10.0 + 10.0 + 150.0) / 3.0)


def test_window_aggregation_mean_std_max_and_shortcut_toggle() -> None:
    first = [_move(float(index * 10), float(index * 5)) for index in range(8)]
    second = [_move(170.0 + index * 10, 100.0 + index * 5) for index in range(8)]

    features = extract_window_features([*first, *second])
    without_shortcuts = extract_window_features([*first, *second], include_shortcut_features=False)

    assert features["n_segments"] == 2.0
    assert _is_close(features["straightness_mean"], 1.0)
    assert _is_close(features["straightness_std"], 0.0)
    assert _is_close(features["straightness_max"], 1.0)
    assert _is_close(features["path_length_mean"], 35.0)
    assert "n_points_mean" in features
    assert "window_dt_mean" in features
    assert "n_points_mean" not in without_shortcuts
    assert "window_dt_mean" not in without_shortcuts
    assert "speed_mean_mean" in without_shortcuts


def _polyline_events(xs: list[float], ys: list[float], dts: list[float]) -> list[dict[str, object]]:
    times = [0.0]
    for delta in dts:
        times.append(times[-1] + float(delta))
    return [_move(time, x, y) for time, x, y in zip(times, xs, ys, strict=True)]


@given(
    st.integers(8, 16).flatmap(
        lambda count: st.tuples(
            st.lists(
                st.floats(-50.0, 50.0, allow_nan=False, allow_infinity=False, width=32),
                min_size=count,
                max_size=count,
            ),
            st.lists(
                st.floats(-50.0, 50.0, allow_nan=False, allow_infinity=False, width=32),
                min_size=count,
                max_size=count,
            ),
            st.lists(
                st.floats(1.0, 40.0, allow_nan=False, allow_infinity=False, width=32),
                min_size=count - 1,
                max_size=count - 1,
            ),
            st.floats(-25.0, 25.0, allow_nan=False, allow_infinity=False, width=32),
            st.floats(-25.0, 25.0, allow_nan=False, allow_infinity=False, width=32),
        )
    )
)
@settings(max_examples=40, deadline=None)
def test_features_are_finite_bounded_and_translation_invariant(
    payload: tuple[list[float], list[float], list[float], float, float],
) -> None:
    xs, ys, dts, dx, dy = payload
    features = extract_segment_features(_polyline_events(xs, ys, dts))
    shifted = extract_segment_features(
        _polyline_events([value + dx for value in xs], [value + dy for value in ys], dts)
    )
    assume(
        min(
            math.hypot(x1 - x0, y1 - y0)
            for x0, y0, x1, y1 in zip(xs[:-1], ys[:-1], xs[1:], ys[1:], strict=True)
        )
        > 1e-6
    )
    assume(all(value == 0.0 or abs(value) > 1e-6 for value in [*xs, *ys]))
    assume(features["path_length"] > 1e-8)
    assume(shifted["path_length"] > 1e-8)

    assert set(features) == set(SEGMENT_FEATURE_NAMES)
    for name, value in features.items():
        assert math.isnan(value) or math.isfinite(value), name
        if not math.isnan(value):
            assert not math.isinf(value), name
    straightness = features["straightness"]
    assert math.isnan(straightness) or 0.0 <= straightness <= 1.0
    for name in SEGMENT_FEATURE_NAMES:
        assert _is_close(features[name], shifted[name], abs_tol=1e-6), name


def test_rejects_invalid_heading_threshold() -> None:
    with pytest.raises(ValueError, match="heading_change_rad"):
        extract_segment_features(_straight_line(), heading_change_rad=-1)

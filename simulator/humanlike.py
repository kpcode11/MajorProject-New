"""Human-like Bezier mouse path and randomised typing generators (Appendix D.3, P7-15).

Used only to exercise the live mock portal system in Phase 7 (Tier 4 and the P7-17 reference run).
Never used as training or validation data.
Privacy: key events contain only coarse ``key_class`` labels and ``[down_ms, up_ms]`` timestamps.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

Point2DLike = tuple[float, float] | Sequence[float] | NDArray[np.float64]

VALID_KEY_CLASSES: tuple[str, ...] = (
    "letter",
    "digit",
    "space",
    "punct",
    "modifier",
    "enter",
    "backspace",
    "other",
)


def bezier_path(
    p0: Point2DLike,
    p3: Point2DLike,
    n: int = 60,
    jitter: float = 1.5,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Generate a 2D cubic Bezier trajectory with smoothstep easing and Gaussian jitter.

    Args:
        p0: Starting ``(x, y)`` coordinate in pixels.
        p3: Target ``(x, y)`` coordinate in pixels.
        n: Number of sample points along the curve (at least 2).
        jitter: Standard deviation of Gaussian positional noise in pixels.
        rng: Optional NumPy random generator for deterministic seeding.

    Returns:
        Array of shape ``(n, 2)`` containing ``[x, y]`` coordinates.
    """
    gen = rng if rng is not None else np.random.default_rng()
    num_pts = max(2, int(n))
    start: NDArray[np.float64] = np.asarray(p0, dtype=np.float64)[:2]
    end: NDArray[np.float64] = np.asarray(p3, dtype=np.float64)[:2]
    d = end - start
    p1 = start + d * gen.uniform(0.2, 0.4) + gen.normal(0.0, 30.0, size=2)
    p2 = start + d * gen.uniform(0.6, 0.8) + gen.normal(0.0, 30.0, size=2)

    t = np.linspace(0.0, 1.0, num_pts, dtype=np.float64)
    t = t * t * (3.0 - 2.0 * t)  # smoothstep easing
    t_col = t[:, None]

    pts: NDArray[np.float64] = (
        ((1.0 - t_col) ** 3) * start
        + 3.0 * ((1.0 - t_col) ** 2) * t_col * p1
        + 3.0 * (1.0 - t_col) * (t_col**2) * p2
        + (t_col**3) * end
    )
    if jitter > 0.0:
        noise = gen.normal(0.0, float(jitter), size=pts.shape)
        # Taper noise at the very last sample so the cursor finishes near the target
        noise[-1] *= 0.25
        pts = pts + noise
    return pts


def generate_humanlike_mouse_trajectory(
    p0: Point2DLike,
    p3: Point2DLike,
    *,
    n: int = 60,
    jitter: float = 1.5,
    duration_ms: float = 620.0,
    start_t_ms: float = 340.0,
    include_correction: bool = True,
    rng: np.random.Generator | None = None,
) -> list[list[float]]:
    """Build ``[[x, y, t_ms], ...]`` mouse points with Bezier curve, pauses, and end correction."""
    gen = rng if rng is not None else np.random.default_rng()
    num_pts = max(8, min(int(n), 250))
    end_xy = np.asarray(p3, dtype=np.float64)[:2]

    if include_correction and num_pts >= 14:
        main_n = num_pts - 5
        corr_n = 5
        overshoot = end_xy + gen.normal(0.0, 6.0, size=2)
        main_pts = bezier_path(p0, overshoot, n=main_n, jitter=jitter, rng=gen)
        corr_pts = bezier_path(
            overshoot,
            end_xy,
            n=corr_n + 1,
            jitter=max(0.3, jitter * 0.35),
            rng=gen,
        )[1:]
        all_pts = np.vstack([main_pts, corr_pts])
    else:
        all_pts = bezier_path(p0, end_xy, n=num_pts, jitter=jitter, rng=gen)

    total_pts = int(all_pts.shape[0])
    mean_dt = max(6.0, float(duration_ms) / max(1, total_pts - 1))
    raw_dts = gen.normal(mean_dt, max(1.5, mean_dt * 0.22), size=total_pts - 1)
    dts = np.clip(raw_dts, 4.0, mean_dt * 2.5)

    # Insert a small pause before the final end-of-path correction when enabled
    if include_correction and total_pts >= 14:
        pause_idx = total_pts - 6
        dts[pause_idx] += float(gen.uniform(25.0, 65.0))

    t_cursor = max(0.0, float(start_t_ms))
    samples: list[list[float]] = [
        [
            round(float(all_pts[0, 0]), 2),
            round(float(all_pts[0, 1]), 2),
            round(t_cursor, 2),
        ]
    ]
    for idx in range(1, total_pts):
        t_cursor += float(dts[idx - 1])
        samples.append(
            [
                round(float(all_pts[idx, 0]), 2),
                round(float(all_pts[idx, 1]), 2),
                round(t_cursor, 2),
            ]
        )
    return samples


def generate_humanlike_key_events(
    num_keys: int = 12,
    *,
    key_class: str = "digit",
    start_t_ms: float = 1100.0,
    mean_dwell_ms: float = 92.0,
    std_dwell_ms: float = 24.0,
    mean_flight_ms: float = 135.0,
    std_flight_ms: float = 42.0,
    typo_prob: float = 0.08,
    rng: np.random.Generator | None = None,
) -> list[list[object]]:
    """Build ``[[key_class, down_ms, up_ms], ...]`` with randomised human-like dwell/flight timing.

    Never records character values—only coarse ``key_class`` categories.
    """
    gen = rng if rng is not None else np.random.default_rng()
    cls_name = key_class if key_class in VALID_KEY_CLASSES else "digit"
    count = max(1, min(int(num_keys), 120))

    events: list[list[object]] = []
    t_cursor = max(10.0, float(start_t_ms))

    for i in range(count):
        dwell = float(np.clip(gen.normal(mean_dwell_ms, std_dwell_ms), 28.0, 260.0))
        down_ms = round(t_cursor, 2)
        up_ms = round(down_ms + dwell, 2)
        events.append([cls_name, down_ms, up_ms])

        # Occasional backspace + re-type burst to mimic natural correction rhythm
        if 1 < i < count - 1 and typo_prob > 0.0 and float(gen.random()) < typo_prob:
            pause_before_bs = float(np.clip(gen.normal(170.0, 35.0), 80.0, 320.0))
            bs_down = round(up_ms + pause_before_bs, 2)
            bs_dwell = float(np.clip(gen.normal(80.0, 18.0), 30.0, 180.0))
            bs_up = round(bs_down + bs_dwell, 2)
            events.append(["backspace", bs_down, bs_up])

            retype_flight = float(np.clip(gen.normal(145.0, 35.0), 55.0, 280.0))
            re_down = round(bs_up + retype_flight, 2)
            re_dwell = float(
                np.clip(gen.normal(mean_dwell_ms, std_dwell_ms), 30.0, 240.0)
            )
            re_up = round(re_down + re_dwell, 2)
            events.append([cls_name, re_down, re_up])
            up_ms = re_up

        # Natural flight interval (occasionally slight rollover or cognitive chunk pause)
        flight = float(np.clip(gen.normal(mean_flight_ms, std_flight_ms), -18.0, 420.0))
        if i in (3, 7):
            # Subtle chunking pause every 4 digits (e.g. 9999-0000-1234)
            flight += float(gen.uniform(45.0, 130.0))
        t_cursor = max(down_ms + 18.0, up_ms + flight)

    return events

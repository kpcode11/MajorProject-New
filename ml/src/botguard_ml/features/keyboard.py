"""Text-agnostic keyboard timing features."""

from __future__ import annotations

from typing import Any

import numpy as np

KEYBOARD_FEATURE_NAMES = (
    "n_keys",
    "typing_speed_cps",
    "dwell_mean",
    "dwell_std",
    "dwell_median",
    "dwell_mad",
    "dwell_cv",
    "dwell_skew",
    "dwell_kurt",
    "flight_mean",
    "flight_std",
    "flight_median",
    "flight_mad",
    "flight_cv",
    "flight_skew",
    "flight_kurt",
    "flight_min",
    "flight_p5",
    "flight_p95",
    "dd_mean",
    "dd_std",
    "rollover_ratio",
    "burst_count",
    "burst_len_mean",
    "pause_count",
    "pause_mean",
    "lag1_autocorr_flight",
    "dwell_flight_corr",
    "identical_interval_fraction",
    "backspace_ratio",
    "paste_events",
)


def _stats(values: np.ndarray, prefix: str) -> dict[str, float]:
    if len(values) == 0:
        return {
            f"{prefix}_{name}": float("nan")
            for name in ("mean", "std", "median", "mad", "cv", "skew", "kurt")
        }
    mean = float(np.mean(values))
    std = float(np.std(values))
    centered = values - mean
    scale = std if std > 0 else float("nan")
    return {
        f"{prefix}_mean": mean,
        f"{prefix}_std": std,
        f"{prefix}_median": float(np.median(values)),
        f"{prefix}_mad": float(np.median(np.abs(centered))),
        f"{prefix}_cv": std / mean if mean else float("nan"),
        f"{prefix}_skew": float(np.mean(centered**3) / scale**3) if std else 0.0,
        f"{prefix}_kurt": float(np.mean(centered**4) / scale**4 - 3) if std else 0.0,
    }


def keyboard_features(events: list[dict[str, Any]]) -> dict[str, float]:
    """Compute Appendix A.3 features from one canonical typing window."""
    ordered = sorted(events, key=lambda event: float(event["down_ms"]))
    if not ordered:
        raise ValueError("keyboard window must contain at least one event")
    down = np.asarray([float(event["down_ms"]) for event in ordered])
    up = np.asarray([float(event["up_ms"]) for event in ordered])
    dwell = up - down
    flight = down[1:] - up[:-1]
    down_delta = np.diff(down)
    features: dict[str, float] = {"n_keys": float(len(ordered))}
    duration = down[-1] - down[0]
    features["typing_speed_cps"] = (
        len(ordered) / (duration / 1000.0) if duration > 0 else float("nan")
    )
    features.update(_stats(dwell, "dwell"))
    features.update(_stats(flight, "flight"))
    features.update(
        {
            "flight_min": float(np.min(flight)) if len(flight) else float("nan"),
            "flight_p5": float(np.percentile(flight, 5)) if len(flight) else float("nan"),
            "flight_p95": float(np.percentile(flight, 95)) if len(flight) else float("nan"),
            "dd_mean": float(np.mean(down_delta)) if len(down_delta) else float("nan"),
            "dd_std": float(np.std(down_delta)) if len(down_delta) else float("nan"),
            "rollover_ratio": float(np.mean(flight < 0)) if len(flight) else 0.0,
        }
    )
    burst_lengths: list[int] = []
    current = 1
    for value in flight:
        if value > 300:
            burst_lengths.append(current)
            current = 1
        else:
            current += 1
    burst_lengths.append(current)
    pauses = flight[flight > 500]
    features.update(
        {
            "burst_count": float(len(burst_lengths)),
            "burst_len_mean": float(np.mean(burst_lengths)),
            "pause_count": float(len(pauses)),
            "pause_mean": float(np.mean(pauses)) if len(pauses) else float("nan"),
            "lag1_autocorr_flight": (
                float(np.corrcoef(flight[:-1], flight[1:])[0, 1])
                if len(flight) > 2 and np.std(flight) > 0
                else float("nan")
            ),
            "dwell_flight_corr": (
                float(np.corrcoef(dwell[1:], flight)[0, 1])
                if len(flight) > 1 and np.std(dwell[1:]) > 0 and np.std(flight) > 0
                else float("nan")
            ),
            "identical_interval_fraction": (
                float(np.mean(np.diff(np.round(down_delta)) == 0))
                if len(down_delta) > 1
                else float("nan")
            ),
            "backspace_ratio": float(
                sum(event.get("key_class") == "control" for event in ordered) / len(ordered)
            ),
            "paste_events": float("nan"),
        }
    )
    return features


def validate_keyboard_features(features: dict[str, float]) -> None:
    """Ensure the feature mapping has the complete Appendix A.3 schema."""
    missing = set(KEYBOARD_FEATURE_NAMES).difference(features)
    if missing:
        raise ValueError(f"missing keyboard features: {', '.join(sorted(missing))}")

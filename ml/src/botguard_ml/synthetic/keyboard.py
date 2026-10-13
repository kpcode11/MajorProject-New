"""Deterministic synthetic keyboard bot generators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class TimingProfile:
    """Log-normal timing parameters fitted from training human windows."""

    dwell_mean: float
    dwell_sigma: float
    flight_mean: float
    flight_sigma: float


def fit_human_timing(windows: list[list[dict[str, Any]]]) -> TimingProfile:
    """Fit K3 timing parameters from training human windows only."""
    dwell: list[float] = []
    flight: list[float] = []
    for window in windows:
        ordered = sorted(window, key=lambda event: float(event["down_ms"]))
        dwell.extend(
            max(0.001, float(event["up_ms"]) - float(event["down_ms"])) for event in ordered
        )
        flight.extend(
            max(0.001, float(current["down_ms"]) - float(previous["up_ms"]))
            for previous, current in zip(ordered, ordered[1:])
        )
    if not dwell or not flight:
        raise ValueError("training human windows must contain dwell and flight intervals")
    log_dwell = np.log(dwell)
    log_flight = np.log(flight)
    return TimingProfile(
        dwell_mean=float(np.mean(log_dwell)),
        dwell_sigma=float(np.std(log_dwell)),
        flight_mean=float(np.mean(log_flight)),
        flight_sigma=float(np.std(log_flight)),
    )


def _events(
    *,
    n_keys: int,
    dwell: np.ndarray,
    flight: np.ndarray,
    bot_type: str,
    seed: int,
) -> list[dict[str, Any]]:
    down = 0.0
    events: list[dict[str, Any]] = []
    for index in range(n_keys):
        up = down + float(dwell[index])
        events.append(
            {
                "dataset": "synthetic_keyboard",
                "session_id": f"{bot_type}/{seed}",
                "subject_id": f"{bot_type}/{seed}",
                "split_group": f"{bot_type}:seed_block:{seed}",
                "label": 1,
                "bot_type": bot_type,
                "down_ms": down,
                "up_ms": up,
                "key_class": "letter",
                "domain": "synthetic",
            }
        )
        if index < n_keys - 1:
            down = up + float(flight[index])
    return events


def generate_keyboard(
    bot_type: str,
    *,
    n_keys: int,
    seed: int,
    profile: TimingProfile | None = None,
    slow: bool = False,
) -> list[dict[str, Any]]:
    """Generate one K1, K2, K3, or K4 keyboard session."""
    if bot_type not in {"K1", "K2", "K3", "K4"}:
        raise ValueError("bot_type must be K1, K2, K3, or K4")
    if n_keys < 1:
        raise ValueError("n_keys must be positive")
    rng = np.random.default_rng(seed)
    if bot_type == "K1":
        dwell = np.maximum(0.1, 90.0 + rng.normal(0, 1.0, n_keys))
        flight = np.maximum(0.1, (200.0 if slow else 120.0) + rng.normal(0, 1.0, n_keys - 1))
    elif bot_type == "K2":
        dwell = rng.uniform(40.0, 160.0, n_keys)
        flight = rng.uniform(50.0, 300.0, n_keys - 1)
    elif bot_type == "K3":
        if profile is None:
            raise ValueError("K3 requires a training-human timing profile")
        dwell = rng.lognormal(profile.dwell_mean, max(profile.dwell_sigma, 1e-6), n_keys)
        flight = rng.lognormal(profile.flight_mean, max(profile.flight_sigma, 1e-6), n_keys - 1)
    else:
        dwell = np.maximum(0.1, rng.uniform(1.0, 4.0, n_keys))
        flight = np.maximum(0.1, rng.uniform(1.0, 4.0, n_keys - 1))
        if n_keys > 2:
            flight[n_keys // 2 - 1] += 1000.0
    return _events(n_keys=n_keys, dwell=dwell, flight=flight, bot_type=bot_type, seed=seed)

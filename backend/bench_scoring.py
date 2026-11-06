"""Latency micro-benchmark for BotGuard model & rule scoring (P5-14).

Runs 1,000 end-to-end ``ModelScorer.score(AssessRequest)`` calls (alternating
human and bot multimodal payloads), prints p50 / p95 / p99 latency in
milliseconds, asserts p95 < 200 ms, and writes results with hardware metadata
to ``results/system/scoring_latency.json``.
"""

from __future__ import annotations

import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.config import load_rule_config, load_settings
from app.schemas import (
    AssessRequest,
    BehaviourPayload,
    EnvSignals,
    KeyBehaviour,
    MouseBehaviour,
)
from app.scoring import load_scorer

BACKEND_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_ROOT.parent
RESULTS_PATH = REPO_ROOT / "results" / "system" / "scoring_latency.json"


def _build_sample_requests() -> tuple[AssessRequest, AssessRequest]:
    """Build representative human and bot multimodal AssessRequest fixtures."""
    rng = np.random.default_rng(42)

    # 45-point human curve
    human_pts: list[list[float]] = []
    t = 0.0
    for i in range(45):
        u = i / 44.0
        x = 200.0 + 500.0 * (3 * u**2 - 2 * u**3) + float(rng.normal(0.0, 1.5))
        y = 300.0 + 250.0 * u + float(rng.normal(0.0, 1.5))
        human_pts.append([round(x, 2), round(y, 2), round(t, 1)])
        t += float(rng.uniform(11.0, 22.0))

    human_keys: list[list[Any]] = []
    tk = 100.0
    for i in range(25):
        dwell = float(rng.lognormal(4.55, 0.30))
        cls = "backspace" if i % 8 == 3 else "letter"
        human_keys.append([cls, round(tk, 1), round(tk + dwell, 1)])
        tk += dwell + float(rng.lognormal(4.6, 0.50))

    human_req = AssessRequest(
        nonce="bench-nonce-human-12345",
        action="login",
        env=EnvSignals(
            ua_family="Chrome",
            ua_os="Windows",
            platform="Win32",
            webdriver=False,
            plugins_count=5,
            viewport_w=1440,
            viewport_h=900,
            screen_w=1920,
            screen_h=1080,
            dpr=1.0,
            languages=["en-US", "en"],
            tz_offset_min=-330,
            touch_points=0,
            hw_concurrency=8,
            device_memory_gb=8.0,
            has_mouse=True,
            has_touch=False,
            has_keyboard=True,
        ),
        behaviour=BehaviourPayload(
            mouse=MouseBehaviour(points=human_pts),
            keys=KeyBehaviour(events=human_keys),
            device_class="desktop",
        ),
    )

    bot_pts = [
        [round(120.0 + (i / 44.0) * 660.0, 2), round(150.0 + (i / 44.0) * 370.0, 2), i * 16.0]
        for i in range(45)
    ]
    bot_keys: list[list[Any]] = [["letter", i * 210.0, i * 210.0 + 90.0] for i in range(25)]

    bot_req = AssessRequest(
        nonce="bench-nonce-bot-12345",
        action="otp_request",
        env=EnvSignals(
            ua_family="Chrome",
            ua_os="Windows",
            platform="Linux x86_64",
            webdriver=True,
            plugins_count=0,
        ),
        behaviour=BehaviourPayload(
            mouse=MouseBehaviour(points=bot_pts),
            keys=KeyBehaviour(events=bot_keys),
            device_class="desktop",
        ),
    )
    return human_req, bot_req


def run_benchmark(n_calls: int = 1000) -> dict[str, Any]:
    """Run ``n_calls`` scoring invocations and record latency percentiles."""
    settings = load_settings()
    rule_cfg = load_rule_config(settings.rules_config_file)
    scorer = load_scorer(settings.models_dir, rule_config=rule_cfg)
    human_req, bot_req = _build_sample_requests()

    # Warm-up (10 calls) so ONNX Runtime arenas are initialised
    for i in range(10):
        scorer.score(human_req if i % 2 == 0 else bot_req)

    latencies_ms: list[float] = []
    t_total_start = time.perf_counter()
    for i in range(n_calls):
        req = human_req if i % 2 == 0 else bot_req
        t0 = time.perf_counter()
        scorer.score(req)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)
    total_elapsed_s = time.perf_counter() - t_total_start

    arr = np.asarray(latencies_ms, dtype=np.float64)
    p50 = float(np.percentile(arr, 50))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))
    mean_ms = float(np.mean(arr))
    min_ms = float(np.min(arr))
    max_ms = float(np.max(arr))

    payload: dict[str, Any] = {
        "benchmark": "backend_model_and_rule_scoring",
        "task_id": "P5-14",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_calls": n_calls,
        "total_elapsed_s": round(total_elapsed_s, 4),
        "throughput_calls_per_sec": round(n_calls / max(total_elapsed_s, 1e-9), 2),
        "latency_ms": {
            "min": round(min_ms, 4),
            "p50": round(p50, 4),
            "mean": round(mean_ms, 4),
            "p95": round(p95, 4),
            "p99": round(p99, 4),
            "max": round(max_ms, 4),
        },
        "target_p95_ms": 200.0,
        "passes_target": bool(p95 < 200.0),
        "models_loaded": scorer.model_versions.model_dump(),
        "hardware": {
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(
        f"Benchmark ({n_calls} calls): "
        f"p50={p50:.3f} ms | p95={p95:.3f} ms | p99={p99:.3f} ms | "
        f"mean={mean_ms:.3f} ms | throughput={payload['throughput_calls_per_sec']:.1f} req/s"
    )
    print(f"Saved latency report to {RESULTS_PATH}")
    if p95 >= 200.0:
        raise RuntimeError(f"p95 latency {p95:.3f} ms exceeded 200 ms target!")
    return payload


if __name__ == "__main__":
    run_benchmark(1000)

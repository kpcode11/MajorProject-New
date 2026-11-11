"""Batch runner for Tiers 1-4 bot simulator sessions (P7-16).

Runs ``N`` sessions per tier with seeded parameter randomisation across ``protection_mode="off"``
and ``protection_mode="passive"``, and writes ``results/system/sim_runs.jsonl`` with each line
recording ``tier``, ``protection_mode``, ``action``, ``outcome`` (``allowed`` / ``challenged`` /
``denied`` / ``blocked-at-api``), ``portal_status``, ``assess_decision``, ``assess_band``,
``params``, and ``latency_ms``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.safety import validate_target_url  # noqa: E402
from simulator.tier1_http import (  # noqa: E402
    DEFAULT_TIER1_USER_AGENTS,
    HttpGetFn,
    HttpPostFn,
    SimRunResult,
    run_tier1_session,
)
from simulator.tier2_playwright import run_tier2_session  # noqa: E402
from simulator.tier3_stealth import TIER3_PROFILES, run_tier3_session  # noqa: E402
from simulator.tier4_humanlike import run_tier4_session  # noqa: E402

DEFAULT_OUTPUT_PATH: Path = ROOT / "results" / "system" / "sim_runs.jsonl"
ACTIONS: tuple[str, ...] = ("otp_request", "details_update", "centre_search")
ACTION_WEIGHTS: tuple[float, ...] = (0.70, 0.15, 0.15)
TransportFactory = Callable[[str, int], tuple[HttpPostFn | None, HttpGetFn | None]]


def _sample_action(rng: np.random.Generator) -> str:
    idx = int(rng.choice(len(ACTIONS), p=ACTION_WEIGHTS))
    return ACTIONS[idx]


def run_randomized_tier_session(
    tier: str,
    *,
    base_url: str,
    protection_mode: str,
    rng: np.random.Generator,
    allowlist_path: Path | None = None,
    post_fn: HttpPostFn | None = None,
    get_fn: HttpGetFn | None = None,
) -> SimRunResult:
    """Run one session of ``tier`` (``tier1``..``tier4``) with randomised parameters."""
    validate_target_url(base_url, allowlist_path=allowlist_path)
    action = _sample_action(rng)
    identifier_len = int(rng.integers(8, 17))

    if tier == "tier1":
        ua = str(rng.choice(DEFAULT_TIER1_USER_AGENTS))
        include_assess = bool(float(rng.random()) < 0.25)
        endpoint_map = {
            "otp_request": "/portal-api/otp/request",
            "details_update": "/portal-api/details/update",
            "centre_search": "/portal-api/centres/search",
        }
        return run_tier1_session(
            base_url,
            protection_mode=protection_mode,
            action=action,
            endpoint_path=endpoint_map[action],
            identifier_length=identifier_len,
            user_agent=ua,
            include_assess_attempt=include_assess,
            allowlist_path=allowlist_path,
            post_fn=post_fn,
            get_fn=get_fn,
        )

    if tier == "tier2":
        fill_delay = float(rng.uniform(20.0, 120.0))
        click_delay = float(rng.uniform(50.0, 170.0))
        click_hold = float(rng.uniform(8.0, 28.0))
        ua_major = int(rng.integers(128, 132))
        vw, vh = (1280, 720) if float(rng.random()) < 0.7 else (1920, 1080)
        attempt_stepup = bool(float(rng.random()) < 0.5)
        return run_tier2_session(
            base_url,
            protection_mode=protection_mode,
            action=action,
            identifier_length=identifier_len,
            fill_delay_ms=fill_delay,
            click_delay_ms=click_delay,
            click_hold_ms=click_hold,
            ua_major=ua_major,
            viewport_w=vw,
            viewport_h=vh,
            attempt_stepup=attempt_stepup,
            allowlist_path=allowlist_path,
            post_fn=post_fn,
            get_fn=get_fn,
        )

    if tier == "tier3":
        profile_idx = int(rng.integers(0, len(TIER3_PROFILES)))
        profile = TIER3_PROFILES[profile_idx]
        num_steps = int(rng.integers(14, 38))
        step_interval = float(rng.uniform(6.0, 16.0))
        key_dwell = float(rng.uniform(25.0, 55.0))
        key_flight = float(rng.uniform(28.0, 65.0))
        ua_major = int(rng.integers(128, 132))
        attempt_stepup = bool(float(rng.random()) < 0.5)
        return run_tier3_session(
            base_url,
            protection_mode=protection_mode,
            action=action,
            profile=profile,
            identifier_length=identifier_len,
            num_mouse_steps=num_steps,
            step_interval_ms=step_interval,
            key_dwell_ms=key_dwell,
            key_flight_ms=key_flight,
            ua_major=ua_major,
            attempt_stepup=attempt_stepup,
            allowlist_path=allowlist_path,
            post_fn=post_fn,
            get_fn=get_fn,
        )

    if tier == "tier4":
        n_curve = int(rng.integers(44, 88))
        jitter = float(rng.uniform(0.9, 2.3))
        mean_dwell = float(rng.uniform(76.0, 112.0))
        std_dwell = float(rng.uniform(16.0, 30.0))
        mean_flight = float(rng.uniform(108.0, 162.0))
        std_flight = float(rng.uniform(30.0, 52.0))
        typo_prob = float(rng.uniform(0.0, 0.14))
        headless_webgl = bool(float(rng.random()) < 0.4)
        attempt_stepup = bool(float(rng.random()) < 0.5)
        sub_seed = int(rng.integers(1, 1_000_000))
        return run_tier4_session(
            base_url,
            protection_mode=protection_mode,
            action=action,
            identifier_length=identifier_len,
            n_curve_points=n_curve,
            jitter=jitter,
            mean_dwell_ms=mean_dwell,
            std_dwell_ms=std_dwell,
            mean_flight_ms=mean_flight,
            std_flight_ms=std_flight,
            typo_prob=typo_prob,
            headless_webgl=headless_webgl,
            attempt_stepup=attempt_stepup,
            seed=sub_seed,
            allowlist_path=allowlist_path,
            post_fn=post_fn,
            get_fn=get_fn,
        )

    raise ValueError(f"Unsupported simulator tier: {tier!r}")


def summarize_sim_runs(results: Sequence[SimRunResult]) -> dict[str, Any]:
    """Aggregate simulator session outcomes per protection mode and tier."""
    summary: dict[str, dict[str, dict[str, int]]] = {}
    for res in results:
        mode_map = summary.setdefault(res.protection_mode, {})
        tier_counts = mode_map.setdefault(
            res.tier,
            {
                "total": 0,
                "allowed": 0,
                "challenged": 0,
                "denied": 0,
                "blocked-at-api": 0,
            },
        )
        tier_counts["total"] += 1
        tier_counts[res.outcome] = tier_counts.get(res.outcome, 0) + 1
    return {
        "total_runs": len(results),
        "by_mode": summary,
    }


def write_sim_runs_jsonl(
    results: Sequence[SimRunResult],
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """Write ``results`` as JSON Lines to ``output_path``."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r.to_dict(), sort_keys=False) for r in results]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path


def run_all_tiers(
    base_url: str = "http://127.0.0.1:8000",
    *,
    n_per_tier: int = 20,
    tiers: Sequence[str] = ("tier1", "tier2", "tier3", "tier4"),
    protection_modes: Sequence[str] = ("off", "passive"),
    seed: int = 42,
    output_path: Path | None = DEFAULT_OUTPUT_PATH,
    allowlist_path: Path | None = None,
    transport_factory: TransportFactory | None = None,
) -> list[SimRunResult]:
    """Run ``n_per_tier`` randomised sessions per tier across ``protection_modes``."""
    validate_target_url(base_url, allowlist_path=allowlist_path)
    rng = np.random.default_rng(seed)
    count = max(1, int(n_per_tier))

    all_results: list[SimRunResult] = []
    session_idx = 0
    for mode in protection_modes:
        for tier in tiers:
            for _ in range(count):
                session_idx += 1
                post_fn: HttpPostFn | None = None
                get_fn: HttpGetFn | None = None
                if transport_factory is not None:
                    post_fn, get_fn = transport_factory(mode, session_idx)
                res = run_randomized_tier_session(
                    tier,
                    base_url=base_url,
                    protection_mode=mode,
                    rng=rng,
                    allowlist_path=allowlist_path,
                    post_fn=post_fn,
                    get_fn=get_fn,
                )
                all_results.append(res)

    if output_path is not None:
        write_sim_runs_jsonl(all_results, output_path=output_path)

    return all_results


def _build_inprocess_asgi_factory(tmp_dir: Path | None = None) -> TransportFactory:
    """Create a socket-free in-process FastAPI transport factory using the real backend scorer."""
    _ = tmp_dir
    backend_dir = ROOT / "backend"
    ml_src_dir = ROOT / "ml" / "src"
    for p in (backend_dir, ml_src_dir):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))

    import dataclasses

    from app.config import load_settings
    from app.db import DatabaseManager
    from app.main import app as default_app
    from app.main import create_app
    from app.store import InMemoryStore

    base_settings = load_settings()
    apps_by_mode: dict[str, Any] = {}

    for mode in ("off", "passive"):
        cfg = dataclasses.replace(
            base_settings,
            protection_mode=mode,
            database_url="sqlite:///:memory:",
            jwt_secret="sim-batch-runner-secret-key-at-least-32-bytes-long",
            rate_limit_nonce_per_min=10_000,
            rate_limit_assess_per_min=10_000,
            rate_limit_challenge_per_min=10_000,
            rate_limit_challenge_session_per_min=10_000,
        )
        apps_by_mode[mode] = create_app(
            settings=cfg,
            store=InMemoryStore(),
            scorer=default_app.state.scorer,
            db=DatabaseManager(cfg.database_url),
        )

    def _call_asgi(
        app: Any,
        method: str,
        path: str,
        body_bytes: bytes,
        headers: dict[str, str],
        client_ip: str,
    ) -> tuple[int, dict[str, Any]]:
        req_headers: dict[str, str] = {"host": "127.0.0.1:8000"}
        for k, v in headers.items():
            req_headers[k.lower()] = v
        if body_bytes:
            req_headers.setdefault("content-type", "application/json")
            req_headers.setdefault("content-length", str(len(body_bytes)))

        raw_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in req_headers.items()]
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": raw_headers,
            "client": (client_ip, 50000),
            "server": ("127.0.0.1", 8000),
        }
        sent = False
        status_code = 500
        resp_chunks: list[bytes] = []

        async def receive() -> dict[str, Any]:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            elif message["type"] == "http.response.body":
                resp_chunks.append(message.get("body", b""))

        coro = app(scope, receive, send)
        try:
            coro.send(None)
        except StopIteration:
            pass

        raw_text = b"".join(resp_chunks).decode("utf-8")
        try:
            parsed = json.loads(raw_text) if raw_text else {}
        except Exception:
            parsed = {}
        return status_code, parsed if isinstance(parsed, dict) else {}

    def factory(mode: str, session_idx: int) -> tuple[HttpPostFn | None, HttpGetFn | None]:
        app = apps_by_mode[mode]
        client_ip = f"10.{(session_idx // 250) % 250 + 1}.{(session_idx % 250) + 1}.10"

        def post_fn(
            url: str,
            body: dict[str, Any],
            headers: dict[str, str],
        ) -> tuple[int, dict[str, Any]]:
            validate_target_url(url)
            path = urlsplit(url).path or "/"
            payload = json.dumps(body).encode("utf-8")
            return _call_asgi(app, "POST", path, payload, headers, client_ip)

        def get_fn(url: str, headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
            validate_target_url(url)
            path = urlsplit(url).path or "/"
            return _call_asgi(app, "GET", path, b"", headers, client_ip)

        return post_fn, get_fn

    return factory


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for ``simulator/run_all.py``."""
    parser = argparse.ArgumentParser(description="Run Tiers 1-4 bot simulator sessions.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Target local portal/backend base URL (must be in allowlist.txt).",
    )
    parser.add_argument(
        "--n-per-tier",
        type=int,
        default=25,
        help="Number of sessions per tier per protection mode (default: 25).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for parameter randomisation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSONL path (default: results/system/sim_runs.jsonl).",
    )
    parser.add_argument(
        "--live-http",
        action="store_true",
        help="Send live HTTP requests to --base-url instead of using in-process ASGI.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    validate_target_url(args.base_url)

    factory = None if args.live_http else _build_inprocess_asgi_factory()
    results = run_all_tiers(
        args.base_url,
        n_per_tier=args.n_per_tier,
        seed=args.seed,
        output_path=args.output,
        transport_factory=factory,
    )

    summary = summarize_sim_runs(results)
    print(f"Wrote {summary['total_runs']} simulator runs to {args.output}")
    for mode, tiers_map in summary["by_mode"].items():
        print(f"  protection_mode={mode}:")
        for tier, counts in tiers_map.items():
            print(
                f"    {tier}: total={counts['total']} "
                f"allowed={counts['allowed']} "
                f"challenged={counts['challenged']} "
                f"denied={counts['denied']} "
                f"blocked-at-api={counts['blocked-at-api']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

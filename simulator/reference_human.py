"""Scripted 'human-like reference' run for the mock portal (P7-17).

IMPORTANT — DEMO SCRIPT ONLY (NOT A VALIDATION DATASET):
This script uses recorded/hand-written realistic input telemetry solely to verify and
demonstrate that:
1. A normal multimodal human session (curved mouse trajectory + log-normal typing rhythm)
   passes passive verification on the mock portal (``decision="allow"``, ``band="low"``,
   HTTP 200 on ``/portal-api/*``).
2. A keyboard-only scripted session (Tab navigation + typing + Enter, zero mouse events)
   is **never** denied automatically (missing modality != bot) and succeeds directly or
   via the accessible keyboard step-up challenge path.

Do NOT cite or use this script as an evaluation or validation dataset. All model evaluation
metrics come exclusively from held-out public dataset splits under ``results/``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

import numpy as np

from simulator.safety import validate_target_url
from simulator.tier1_http import (
    HttpGetFn,
    HttpPostFn,
    SimOutcome,
    SimRunResult,
    _urllib_get,
    _urllib_post,
)
from simulator.tier2_playwright import (
    ACTION_ENDPOINT_MAP,
    ACTION_PAGE_MAP,
    PlaywrightPageLike,
    build_portal_request_body,
)

DEMO_SCRIPT_DISCLAIMER: str = (
    "DEMO SCRIPT ONLY — NOT A VALIDATION DATASET. "
    "Used solely to demonstrate that normal and keyboard-only sessions pass the mock portal."
)

ReferenceMode = Literal["multimodal_desktop", "keyboard_only"]

# Recorded realistic human cursor arc (39 samples, ~633 ms duration) used as a deterministic
# reference fixture in API & portal tests.
REFERENCE_HUMAN_MOUSE_POINTS: list[list[float]] = [
    [756.0, 273.0, 191.0],
    [744.0, 273.0, 199.3],
    [711.0, 280.0, 220.7],
    [687.0, 291.0, 241.5],
    [676.0, 301.0, 256.5],
    [667.0, 315.0, 271.9],
    [657.0, 334.0, 293.8],
    [653.0, 347.0, 309.2],
    [652.0, 359.0, 323.9],
    [653.0, 370.0, 337.8],
    [657.0, 383.0, 360.3],
    [661.0, 391.0, 374.8],
    [670.0, 400.0, 389.2],
    [681.0, 405.0, 404.4],
    [701.0, 411.0, 426.4],
    [715.0, 413.0, 441.1],
    [733.0, 411.0, 455.7],
    [750.0, 405.0, 470.7],
    [777.0, 391.0, 492.8],
    [786.0, 384.0, 507.1],
    [793.0, 379.0, 522.2],
    [802.0, 367.0, 544.1],
    [807.0, 354.0, 558.4],
    [812.0, 342.0, 574.2],
    [813.0, 332.0, 588.7],
    [815.0, 315.0, 610.5],
    [814.0, 306.0, 625.0],
    [813.0, 299.0, 640.0],
    [810.0, 294.0, 654.7],
    [808.0, 289.0, 676.8],
    [805.0, 285.0, 691.4],
    [801.0, 283.0, 706.3],
    [799.0, 281.0, 720.9],
    [793.0, 277.0, 743.4],
    [787.0, 273.0, 757.8],
    [783.0, 271.0, 772.6],
    [778.0, 269.0, 787.0],
    [769.0, 267.0, 809.8],
    [767.0, 267.0, 823.8],
]


def build_reference_human_env_signals() -> dict[str, Any]:
    """Return consistent desktop browser environment signals for the reference run."""
    return {
        "webdriver": False,
        "ua_family": "chrome",
        "ua_major": 130,
        "ua_os": "windows",
        "platform": "Win32",
        "hints_brands": ["Chromium", "Google Chrome"],
        "hints_platform": "Windows",
        "languages_count": 2,
        "lang_primary": "en-IN",
        "timezone_offset_min": -330,
        "screen_w_bucket": 1920,
        "screen_h_bucket": 1080,
        "viewport_w": 1440,
        "viewport_h": 900,
        "outer_w": 1456,
        "outer_h": 988,
        "dpr_bucket": 1.0,
        "hw_concurrency_bucket": 8,
        "device_memory_bucket": 8.0,
        "webgl_renderer_class": "hardware",
        "plugins_count": 5,
        "max_touch_points": 0,
        "touch_event_supported": False,
        "native_fn_integrity_ok": True,
        "storage_available": True,
        "visibility": "visible",
    }


def build_reference_human_key_events(
    *,
    seed: int = 7,
    include_tab_and_enter: bool = False,
) -> list[list[object]]:
    """Build realistic log-normal keystroke timing events (coarse ``key_class`` only)."""
    rng = np.random.default_rng(seed)
    events: list[list[object]] = []
    t = 120.0

    if include_tab_and_enter:
        # Tab into the identifier input field
        events.append(["other", round(t, 1), round(t + 78.0, 1)])
        t += 265.0

    for i in range(30):
        dwell = float(rng.lognormal(4.55, 0.32))
        key_cls = "backspace" if i % 9 == 4 else "letter"
        events.append([key_cls, round(t, 1), round(t + dwell, 1)])
        flight = -15.0 if i % 5 == 0 else float(rng.lognormal(4.6, 0.55))
        t = max(t + 5.0, t + dwell + flight)

    if include_tab_and_enter:
        # Tab to the submit button and press Enter
        t += 210.0
        events.append(["other", round(t, 1), round(t + 82.0, 1)])
        t += 240.0
        events.append(["enter", round(t, 1), round(t + 94.0, 1)])

    return events


def build_reference_human_behaviour_payload(
    *,
    mode: ReferenceMode = "multimodal_desktop",
    seed: int = 7,
) -> dict[str, Any]:
    """Build the behaviour payload for ``multimodal_desktop`` or ``keyboard_only`` runs."""
    if mode == "keyboard_only":
        key_events = build_reference_human_key_events(seed=seed, include_tab_and_enter=True)
        last_up = (
            float(key_events[-1][2]) if isinstance(key_events[-1][2], (int, float)) else 3500.0
        )
        return {
            "keys": {
                "events": key_events,
                "paste_events": 0,
                "autofill_suspected": False,
                "untrusted_count": 0,
            },
            "timing": {
                "ms_since_load": round(last_up + 180.0, 2),
                "ms_to_first_interaction": 120.0,
                "ms_since_nonce": round(last_up + 60.0, 2),
                "scroll_events": 0,
                "focus_changes": 4,
            },
            "device_class": "desktop",
        }

    key_events = build_reference_human_key_events(seed=seed, include_tab_and_enter=False)
    last_up = float(key_events[-1][2]) if isinstance(key_events[-1][2], (int, float)) else 3500.0
    return {
        "mouse": {
            "points": [list(pt) for pt in REFERENCE_HUMAN_MOUSE_POINTS],
            "clicks": [[767.0, 267.0, 835.0, 912.0]],
            "untrusted_count": 0,
            "wheel_events": 1,
        },
        "keys": {
            "events": key_events,
            "paste_events": 0,
            "autofill_suspected": False,
            "untrusted_count": 0,
        },
        "timing": {
            "ms_since_load": round(max(1200.0, last_up + 160.0), 2),
            "ms_to_first_interaction": 191.0,
            "ms_since_nonce": round(max(950.0, last_up + 40.0), 2),
            "scroll_events": 1,
            "focus_changes": 2,
        },
        "device_class": "desktop",
    }


def run_reference_human_session(
    base_url: str = "http://127.0.0.1:8000",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    mode: ReferenceMode = "multimodal_desktop",
    endpoint_path: str | None = None,
    identifier_length: int = 12,
    seed: int = 7,
    allowlist_path: Path | None = None,
    page: PlaywrightPageLike | None = None,
    post_fn: HttpPostFn | None = None,
    get_fn: HttpGetFn | None = None,
) -> SimRunResult:
    """Execute a scripted human-like reference session (DEMO SCRIPT ONLY, P7-17).

    Validates ``base_url`` against ``simulator/allowlist.txt`` before making any call.
    When ``mode="keyboard_only"``, sends only keyboard + timing telemetry (zero mouse points)
    and, if challenged, completes the step-up via the keyboard alternative path.
    """
    clean_base = validate_target_url(base_url, allowlist_path=allowlist_path).rstrip("/")
    if page is not None:
        page_id = ACTION_PAGE_MAP.get(action, "login")
        target_page_url = validate_target_url(
            f"{clean_base}/?page={page_id}",
            allowlist_path=allowlist_path,
        )
        t0 = time.perf_counter()
        page.goto(target_page_url)
        page.fill('[data-testid="identifier-input"]', "9" * max(4, identifier_length))
        page.click('[data-testid="send-otp-btn"]')
        if page.is_visible('[data-testid="stepup-dialog"]'):
            page.click('[data-testid="stepup-kb-btn"]')
        latency_ms = (time.perf_counter() - t0) * 1000.0
        dom_outcome = page.get_attribute('[data-testid="otp-result"]', "data-outcome")
        allowed = dom_outcome == "accepted"
        return SimRunResult(
            tier="reference_human",
            protection_mode=protection_mode,
            action=action,
            outcome="allowed" if allowed else "denied",
            portal_status=200 if allowed else 401,
            assess_decision="allow" if allowed else "deny",
            assess_band="low" if allowed else "high",
            params={
                "mode": mode,
                "demo_script_only": True,
                "not_a_validation_dataset": True,
                "disclaimer": DEMO_SCRIPT_DISCLAIMER,
                "seed": seed,
            },
            latency_ms=latency_ms,
        )

    resolved_endpoint = endpoint_path or ACTION_ENDPOINT_MAP.get(action, "/portal-api/otp/request")
    nonce_url = validate_target_url(f"{clean_base}/v1/nonce", allowlist_path=allowlist_path)
    assess_url = validate_target_url(f"{clean_base}/v1/assess", allowlist_path=allowlist_path)
    challenge_url = validate_target_url(
        f"{clean_base}/v1/assess/challenge", allowlist_path=allowlist_path
    )
    portal_url = validate_target_url(
        f"{clean_base}/{resolved_endpoint.lstrip('/')}",
        allowlist_path=allowlist_path,
    )

    do_post: HttpPostFn = post_fn if post_fn is not None else _urllib_post
    do_get: HttpGetFn = get_fn if get_fn is not None else _urllib_get

    t0 = time.perf_counter()
    headers: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
    }
    env_signals = build_reference_human_env_signals()
    behaviour_payload = build_reference_human_behaviour_payload(mode=mode, seed=seed)

    initial_decision: str | None = None
    assess_decision: str | None = None
    assess_band: str | None = None
    token: str | None = None
    completed_via_stepup = False

    n_status, n_body = do_get(nonce_url, headers)
    nonce = str(n_body.get("nonce", "")) if n_status == 200 else ""
    if nonce:
        a_status, a_body = do_post(
            assess_url,
            {
                "nonce": nonce,
                "action": action,
                "sdk_version": "1.0.0",
                "env": env_signals,
                "behaviour": behaviour_payload,
                "context": {
                    "page_id": ACTION_PAGE_MAP.get(action, "login"),
                    "attempt_count": 1,
                },
            },
            headers,
        )
        if a_status == 200:
            raw_dec = a_body.get("decision")
            raw_band = a_body.get("band")
            initial_decision = str(raw_dec) if isinstance(raw_dec, str) else None
            assess_decision = initial_decision
            assess_band = str(raw_band) if isinstance(raw_band, str) else None
            raw_tok = a_body.get("token")
            if isinstance(raw_tok, str) and raw_tok:
                token = raw_tok

            if assess_decision == "challenge":
                challenge_obj = a_body.get("challenge")
                challenge_id = (
                    str(challenge_obj.get("id", "")) if isinstance(challenge_obj, dict) else ""
                )
                req_hold_ms = (
                    float(challenge_obj.get("hold_ms", 1000.0))
                    if isinstance(challenge_obj, dict)
                    else 1000.0
                )
                if challenge_id:
                    n2_status, n2_body = do_get(nonce_url, headers)
                    nonce2 = str(n2_body.get("nonce", "")) if n2_status == 200 else ""
                    if nonce2:
                        c_status, c_body = do_post(
                            challenge_url,
                            {
                                "nonce": nonce2,
                                "challenge_id": challenge_id,
                                "action": action,
                                "hold_start_ms": 1000.0,
                                "hold_end_ms": round(1000.0 + req_hold_ms + 85.0, 2),
                                "env": env_signals,
                                "behaviour": behaviour_payload,
                            },
                            headers,
                        )
                        if c_status == 200:
                            c_dec = c_body.get("decision")
                            c_band = c_body.get("band")
                            assess_decision = (
                                str(c_dec) if isinstance(c_dec, str) else assess_decision
                            )
                            assess_band = str(c_band) if isinstance(c_band, str) else assess_band
                            c_tok = c_body.get("token")
                            if isinstance(c_tok, str) and c_tok:
                                token = c_tok
                                completed_via_stepup = True

    if token:
        headers["X-Human-Token"] = token

    portal_body = build_portal_request_body(action, identifier_length=identifier_length)
    portal_status, _ = do_post(portal_url, portal_body, headers)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    outcome: SimOutcome
    if portal_status == 200:
        outcome = "allowed"
    elif assess_decision == "challenge":
        outcome = "challenged"
    elif assess_decision == "deny":
        outcome = "denied"
    else:
        outcome = "blocked-at-api"

    return SimRunResult(
        tier="reference_human",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "mode": mode,
            "initial_decision": initial_decision,
            "completed_via_stepup": completed_via_stepup,
            "demo_script_only": True,
            "not_a_validation_dataset": True,
            "disclaimer": DEMO_SCRIPT_DISCLAIMER,
            "seed": seed,
        },
        latency_ms=latency_ms,
    )

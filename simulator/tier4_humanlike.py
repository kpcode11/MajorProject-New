"""Tier 4 bot simulator: Playwright with human-like Bezier paths and typing (P7-15).

Behaviour:
- Validates the target URL against ``simulator/allowlist.txt`` via :func:`validate_target_url`
  before any navigation or HTTP request.
- Uses :func:`simulator.humanlike.bezier_path`,
  :func:`simulator.humanlike.generate_humanlike_mouse_trajectory` (Appendix D.3 cubic Bezier
  with smoothstep ease-in/out, Gaussian jitter, and end-of-path correction), and
  :func:`simulator.humanlike.generate_humanlike_key_events` (randomised dwell/flight intervals).
- Supports both live Playwright ``Page`` driving (:func:`drive_tier4_playwright_page`) and
  protocol/ASGI execution (:func:`run_tier4_session`).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from simulator.humanlike import (
    bezier_path,
    generate_humanlike_key_events,
    generate_humanlike_mouse_trajectory,
)
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
from simulator.tier3_stealth import apply_tier3_context_adjustments


def build_tier4_env_signals(
    *,
    ua_major: int = 130,
    viewport_w: int = 1366,
    viewport_h: int = 768,
    headless_webgl: bool = False,
) -> dict[str, Any]:
    """Build environment signals for a Tier 4 browser context."""
    return {
        "webdriver": False,
        "ua_family": "chrome",
        "ua_major": ua_major,
        "ua_os": "windows",
        "platform": "Win32",
        "hints_brands": ["Chromium", "Google Chrome"],
        "hints_platform": "Windows",
        "languages_count": 2,
        "lang_primary": "en-IN",
        "timezone_offset_min": -330,
        "screen_w_bucket": 1920,
        "screen_h_bucket": 1080,
        "viewport_w": viewport_w,
        "viewport_h": viewport_h,
        "outer_w": viewport_w + 16,
        "outer_h": viewport_h + 88,
        "dpr_bucket": 1.0,
        "hw_concurrency_bucket": 8,
        "device_memory_bucket": 8.0,
        "webgl_renderer_class": "software" if headless_webgl else "hardware",
        "plugins_count": 5,
        "max_touch_points": 0,
        "touch_event_supported": False,
        "native_fn_integrity_ok": True,
        "storage_available": True,
        "visibility": "visible",
    }


def build_tier4_behaviour_payload(
    *,
    num_keys: int = 12,
    n_curve_points: int = 60,
    jitter: float = 1.5,
    mean_dwell_ms: float = 92.0,
    std_dwell_ms: float = 24.0,
    mean_flight_ms: float = 135.0,
    std_flight_ms: float = 42.0,
    typo_prob: float = 0.08,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Build a Tier 4 behaviour payload using Appendix D.3 Bezier curves and randomised typing."""
    gen = rng if rng is not None else np.random.default_rng()

    start_xy = (float(gen.uniform(60.0, 180.0)), float(gen.uniform(70.0, 160.0)))
    input_xy = (float(gen.uniform(210.0, 280.0)), float(gen.uniform(210.0, 250.0)))
    submit_xy = (float(gen.uniform(190.0, 260.0)), float(gen.uniform(310.0, 350.0)))

    first_t = float(gen.uniform(320.0, 620.0))
    seg1_dur = float(gen.uniform(480.0, 780.0))
    pts_to_input = generate_humanlike_mouse_trajectory(
        start_xy,
        input_xy,
        n=max(20, n_curve_points // 2),
        jitter=jitter,
        duration_ms=seg1_dur,
        start_t_ms=first_t,
        include_correction=True,
        rng=gen,
    )
    input_click_down = round(pts_to_input[-1][2] + float(gen.uniform(35.0, 95.0)), 2)
    input_click_up = round(input_click_down + float(gen.uniform(55.0, 115.0)), 2)

    typing_start = input_click_up + float(gen.uniform(140.0, 290.0))
    key_events = generate_humanlike_key_events(
        num_keys=num_keys,
        key_class="digit",
        start_t_ms=typing_start,
        mean_dwell_ms=mean_dwell_ms,
        std_dwell_ms=std_dwell_ms,
        mean_flight_ms=mean_flight_ms,
        std_flight_ms=std_flight_ms,
        typo_prob=typo_prob,
        rng=gen,
    )
    last_up_val = key_events[-1][2] if key_events else None
    last_key_up = (
        float(last_up_val)
        if isinstance(last_up_val, (int, float))
        else typing_start + 500.0
    )

    move2_start = last_key_up + float(gen.uniform(120.0, 260.0))
    seg2_dur = float(gen.uniform(420.0, 680.0))
    pts_to_submit = generate_humanlike_mouse_trajectory(
        input_xy,
        submit_xy,
        n=max(20, n_curve_points - len(pts_to_input)),
        jitter=jitter,
        duration_ms=seg2_dur,
        start_t_ms=move2_start,
        include_correction=True,
        rng=gen,
    )
    submit_click_down = round(pts_to_submit[-1][2] + float(gen.uniform(40.0, 110.0)), 2)
    submit_click_up = round(submit_click_down + float(gen.uniform(60.0, 125.0)), 2)

    all_points = (pts_to_input + pts_to_submit)[:600]
    clicks = [
        [
            round(input_xy[0], 2),
            round(input_xy[1], 2),
            input_click_down,
            input_click_up,
        ],
        [
            round(submit_xy[0], 2),
            round(submit_xy[1], 2),
            submit_click_down,
            submit_click_up,
        ],
    ]

    return {
        "mouse": {
            "points": all_points,
            "clicks": clicks,
            "untrusted_count": 0,
            "wheel_events": int(gen.integers(0, 3)),
        },
        "keys": {
            "events": key_events,
            "paste_events": 0,
            "autofill_suspected": False,
            "untrusted_count": 0,
        },
        "timing": {
            "ms_since_load": round(
                submit_click_up + float(gen.uniform(45.0, 120.0)), 2
            ),
            "ms_to_first_interaction": round(first_t, 2),
            "ms_since_nonce": round(
                submit_click_up - first_t + float(gen.uniform(60.0, 140.0)), 2
            ),
            "scroll_events": int(gen.integers(0, 2)),
            "focus_changes": 2,
        },
        "device_class": "desktop",
    }


def drive_tier4_playwright_page(
    page: PlaywrightPageLike,
    portal_url: str = "http://127.0.0.1:5173",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    identifier: str = "999900001234",
    n_curve_points: int = 40,
    jitter: float = 1.5,
    attempt_stepup: bool = True,
    seed: int | None = None,
    allowlist_path: Path | None = None,
) -> SimRunResult:
    """Drive a Playwright ``Page`` using Appendix D.3 Bezier cursor movements and human-like typing.

    Validates ``portal_url`` against ``simulator/allowlist.txt`` before navigating.
    """
    clean_portal = validate_target_url(
        portal_url, allowlist_path=allowlist_path
    ).rstrip("/")
    page_id = ACTION_PAGE_MAP.get(action, "login")
    target_page_url = validate_target_url(
        f"{clean_portal}/?page={page_id}",
        allowlist_path=allowlist_path,
    )

    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()
    apply_tier3_context_adjustments(page)
    page.goto(target_page_url)

    # Move mouse along Bezier path if page exposes a Playwright mouse controller
    mouse_obj = getattr(page, "mouse", None)
    move_fn = getattr(mouse_obj, "move", None) if mouse_obj is not None else None
    curve = bezier_path(
        (90.0, 110.0), (235.0, 295.0), n=n_curve_points, jitter=jitter, rng=rng
    )
    if callable(move_fn):
        for pt in curve:
            move_fn(float(pt[0]), float(pt[1]))

    result_selector = '[data-testid="otp-result"]'
    if action == "details_update":
        page.fill('[data-testid="detail-name-input"]', "Tier4 Bezier Bot")
        page.fill('[data-testid="detail-address-input"]', "400 Curve Boulevard")
        page.fill('[data-testid="detail-pincode-input"]', "560001")
        page.click('[data-testid="detail-confirm-checkbox"]')
        page.click('[data-testid="submit-details-btn"]')
        result_selector = '[data-testid="details-result"]'
    elif action == "centre_search":
        page.fill('[data-testid="centre-query-input"]', "560001")
        page.click('[data-testid="search-centres-btn"]')
        result_selector = '[data-testid="centre-search-status"]'
    else:
        page.fill('[data-testid="identifier-input"]', identifier)
        page.click('[data-testid="send-otp-btn"]')

    challenged = page.is_visible('[data-testid="stepup-dialog"]')
    if challenged and attempt_stepup:
        page.click('[data-testid="stepup-kb-btn"]')

    latency_ms = (time.perf_counter() - t0) * 1000.0
    dom_outcome = page.get_attribute(result_selector, "data-outcome")

    outcome: SimOutcome
    portal_status: int
    assess_decision: str | None = None
    assess_band: str | None = None

    if dom_outcome == "accepted":
        outcome = "allowed"
        portal_status = 200
        assess_decision = "allow"
        assess_band = "low"
    elif challenged and not attempt_stepup:
        outcome = "challenged"
        portal_status = 401
        assess_decision = "challenge"
        assess_band = "medium"
    else:
        outcome = "denied"
        portal_status = 401
        assess_decision = "deny"
        assess_band = "high"

    return SimRunResult(
        tier="tier4",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "mode": "playwright_page",
            "n_curve_points": int(curve.shape[0]),
            "jitter": round(jitter, 2),
            "attempt_stepup": attempt_stepup,
            "seed": seed,
        },
        latency_ms=latency_ms,
    )


def run_tier4_session(
    base_url: str = "http://127.0.0.1:8000",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    endpoint_path: str | None = None,
    identifier_length: int = 12,
    n_curve_points: int = 60,
    jitter: float = 1.5,
    mean_dwell_ms: float = 92.0,
    std_dwell_ms: float = 24.0,
    mean_flight_ms: float = 135.0,
    std_flight_ms: float = 42.0,
    typo_prob: float = 0.08,
    headless_webgl: bool = False,
    ua_major: int = 130,
    attempt_stepup: bool = False,
    seed: int | None = None,
    allowlist_path: Path | None = None,
    page: PlaywrightPageLike | None = None,
    post_fn: HttpPostFn | None = None,
    get_fn: HttpGetFn | None = None,
) -> SimRunResult:
    """Execute one Tier 4 human-like Bezier + randomised typing bot session against ``base_url``.

    Validates ``base_url`` against ``simulator/allowlist.txt`` before making any call.
    """
    clean_base = validate_target_url(base_url, allowlist_path=allowlist_path).rstrip(
        "/"
    )
    if page is not None:
        return drive_tier4_playwright_page(
            page,
            clean_base,
            protection_mode=protection_mode,
            action=action,
            identifier="9" * max(4, identifier_length),
            n_curve_points=n_curve_points,
            jitter=jitter,
            attempt_stepup=attempt_stepup,
            seed=seed,
            allowlist_path=allowlist_path,
        )

    resolved_endpoint = endpoint_path or ACTION_ENDPOINT_MAP.get(
        action, "/portal-api/otp/request"
    )
    nonce_url = validate_target_url(
        f"{clean_base}/v1/nonce", allowlist_path=allowlist_path
    )
    assess_url = validate_target_url(
        f"{clean_base}/v1/assess", allowlist_path=allowlist_path
    )
    challenge_url = validate_target_url(
        f"{clean_base}/v1/assess/challenge", allowlist_path=allowlist_path
    )
    portal_url = validate_target_url(
        f"{clean_base}/{resolved_endpoint.lstrip('/')}",
        allowlist_path=allowlist_path,
    )

    do_post: HttpPostFn = post_fn if post_fn is not None else _urllib_post
    do_get: HttpGetFn = get_fn if get_fn is not None else _urllib_get

    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()
    user_agent = (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{ua_major}.0.0.0 Safari/537.36"
    )
    headers: dict[str, str] = {"User-Agent": user_agent}

    env_signals = build_tier4_env_signals(
        ua_major=ua_major,
        headless_webgl=headless_webgl,
    )
    behaviour_payload = build_tier4_behaviour_payload(
        num_keys=max(4, identifier_length),
        n_curve_points=n_curve_points,
        jitter=jitter,
        mean_dwell_ms=mean_dwell_ms,
        std_dwell_ms=std_dwell_ms,
        mean_flight_ms=mean_flight_ms,
        std_flight_ms=std_flight_ms,
        typo_prob=typo_prob,
        rng=rng,
    )

    assess_decision: str | None = None
    assess_band: str | None = None
    token: str | None = None

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
            assess_decision = str(raw_dec) if isinstance(raw_dec, str) else None
            assess_band = str(raw_band) if isinstance(raw_band, str) else None
            raw_tok = a_body.get("token")
            if isinstance(raw_tok, str) and raw_tok:
                token = raw_tok

            if assess_decision == "challenge" and attempt_stepup:
                challenge_obj = a_body.get("challenge")
                challenge_id = (
                    str(challenge_obj.get("id", ""))
                    if isinstance(challenge_obj, dict)
                    else ""
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
                        actual_hold = round(
                            req_hold_ms + float(rng.uniform(110.0, 260.0)), 2
                        )
                        c_status, c_body = do_post(
                            challenge_url,
                            {
                                "nonce": nonce2,
                                "challenge_id": challenge_id,
                                "action": action,
                                "hold_start_ms": 1000.0,
                                "hold_end_ms": round(1000.0 + actual_hold, 2),
                                "env": env_signals,
                                "behaviour": behaviour_payload,
                            },
                            headers,
                        )
                        if c_status == 200:
                            c_dec = c_body.get("decision")
                            c_band = c_body.get("band")
                            assess_decision = (
                                str(c_dec)
                                if isinstance(c_dec, str)
                                else assess_decision
                            )
                            assess_band = (
                                str(c_band) if isinstance(c_band, str) else assess_band
                            )
                            c_tok = c_body.get("token")
                            if isinstance(c_tok, str) and c_tok:
                                token = c_tok

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
        tier="tier4",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "n_curve_points": n_curve_points,
            "jitter": round(jitter, 2),
            "mean_dwell_ms": round(mean_dwell_ms, 2),
            "std_dwell_ms": round(std_dwell_ms, 2),
            "mean_flight_ms": round(mean_flight_ms, 2),
            "std_flight_ms": round(std_flight_ms, 2),
            "typo_prob": round(typo_prob, 3),
            "headless_webgl": headless_webgl,
            "attempt_stepup": attempt_stepup,
            "seed": seed,
        },
        latency_ms=latency_ms,
    )

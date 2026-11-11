"""Tier 2 bot simulator: Playwright (default settings) performing direct clicks and fills (P7-13).

Behaviour:
- Validates the target URL against ``simulator/allowlist.txt`` via :func:`validate_target_url`
  before any navigation or HTTP request.
- Supports two execution modes:
  1. **Live Playwright Page driving** (:func:`drive_tier2_playwright_page`): drives a Playwright
     ``Page`` (or protocol-compatible browser page) using default settings—direct ``page.fill()``
     and ``page.click()`` with no mouse trajectory interpolation or per-key timing delays.
  2. **Protocol / ASGI session runner** (:func:`run_tier2_session`): executes the exact telemetry
     profile emitted by ``@botguard/sdk`` inside a default headless Playwright browser
     (``navigator.webdriver=True``, SwiftShader software WebGL, 0 desktop plugins, zero mouse
     trajectory points before click, zero individual keystrokes from ``page.fill()``) against
     ``/v1/nonce``, ``/v1/assess``, and ``/portal-api/*``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Protocol

from simulator.safety import validate_target_url
from simulator.tier1_http import (
    HttpGetFn,
    HttpPostFn,
    SimOutcome,
    SimRunResult,
    _urllib_get,
    _urllib_post,
)


class PlaywrightPageLike(Protocol):
    """Minimal structural protocol matching ``playwright.sync_api.Page`` for Tier 2 automation."""

    def goto(self, url: str, **kwargs: Any) -> Any: ...
    def fill(self, selector: str, value: str, **kwargs: Any) -> None: ...
    def click(self, selector: str, **kwargs: Any) -> None: ...
    def get_attribute(self, selector: str, name: str, **kwargs: Any) -> str | None: ...
    def is_visible(self, selector: str, **kwargs: Any) -> bool: ...


ACTION_ENDPOINT_MAP: dict[str, str] = {
    "otp_request": "/portal-api/otp/request",
    "details_update": "/portal-api/details/update",
    "centre_search": "/portal-api/centres/search",
}

ACTION_PAGE_MAP: dict[str, str] = {
    "otp_request": "login",
    "details_update": "update-details",
    "centre_search": "centre-search",
}


def build_tier2_env_signals(
    *,
    ua_major: int = 130,
    viewport_w: int = 1280,
    viewport_h: int = 720,
) -> dict[str, Any]:
    """Return the coarse environment signals captured inside default headless Playwright Chromium.

    Default Playwright settings leave ``navigator.webdriver = true``, use software WebGL
    rendering (SwiftShader), report ``plugins.length = 0`` on desktop, and match
    ``outerWidth/Height`` to ``innerWidth/Height``.
    """
    return {
        "webdriver": True,
        "ua_family": "chrome",
        "ua_major": ua_major,
        "ua_os": "windows",
        "platform": "Win32",
        "hints_brands": ["HeadlessChrome", "Chromium"],
        "hints_platform": "Windows",
        "languages_count": 1,
        "lang_primary": "en-US",
        "timezone_offset_min": 0,
        "screen_w_bucket": viewport_w,
        "screen_h_bucket": viewport_h,
        "viewport_w": viewport_w,
        "viewport_h": viewport_h,
        "outer_w": viewport_w,
        "outer_h": viewport_h,
        "dpr_bucket": 1.0,
        "hw_concurrency_bucket": 4,
        "device_memory_bucket": 8.0,
        "webgl_renderer_class": "software",
        "plugins_count": 0,
        "max_touch_points": 0,
        "touch_event_supported": False,
        "native_fn_integrity_ok": True,
        "storage_available": True,
        "visibility": "visible",
    }


def build_tier2_behaviour_payload(
    *,
    fill_delay_ms: float = 45.0,
    click_delay_ms: float = 85.0,
    click_hold_ms: float = 12.0,
    button_x: float = 220.0,
    button_y: float = 310.0,
) -> dict[str, Any]:
    """Return the behaviour payload produced by Playwright ``page.fill()`` + ``page.click()``.

    - ``page.fill()`` sets the input value directly without dispatching human keydown/keyup
      sequences (``keys.events = []``, ``autofill_suspected = True``).
    - ``page.click()`` dispatches a single instant click at the target element centre without
      intermediate mouse movement trajectory samples (``mouse.points = []``).
    - Interaction starts almost immediately after page load (``ms_to_first_interaction < 150 ms``).
    """
    first_ms = round(max(5.0, fill_delay_ms), 2)
    down_ms = round(first_ms + max(5.0, click_delay_ms), 2)
    up_ms = round(down_ms + max(1.0, click_hold_ms), 2)
    return {
        "mouse": {
            "points": [],
            "clicks": [[round(button_x, 1), round(button_y, 1), down_ms, up_ms]],
            "untrusted_count": 0,
            "wheel_events": 0,
        },
        "keys": {
            "events": [],
            "paste_events": 0,
            "autofill_suspected": True,
            "untrusted_count": 0,
        },
        "timing": {
            "ms_since_load": round(up_ms + 15.0, 2),
            "ms_to_first_interaction": first_ms,
            "ms_since_nonce": round(max(1.0, up_ms - first_ms + 10.0), 2),
            "scroll_events": 0,
            "focus_changes": 2,
        },
        "device_class": "desktop",
    }


def build_portal_request_body(
    action: str, *, identifier_length: int = 12
) -> dict[str, Any]:
    """Build the coarse portal API request body for ``action``."""
    if action == "details_update":
        return {
            "action": "details_update",
            "fields_updated": ["name", "address", "pincode"],
            "city_code": "BENGALURU",
            "language_code": "EN",
            "confirmed": True,
        }
    if action == "centre_search":
        return {
            "action": "centre_search",
            "service_type": "ALL",
            "query_length": max(2, identifier_length),
        }
    return {
        "action": action,
        "identifier_length": max(4, identifier_length),
    }


def drive_tier2_playwright_page(
    page: PlaywrightPageLike,
    portal_url: str = "http://127.0.0.1:5173",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    identifier: str = "999900001234",
    attempt_stepup: bool = False,
    allowlist_path: Path | None = None,
) -> SimRunResult:
    """Drive a Playwright ``Page`` using default direct ``fill`` and ``click`` calls.

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

    t0 = time.perf_counter()
    page.goto(target_page_url)

    result_selector = '[data-testid="otp-result"]'
    if action == "details_update":
        page.fill('[data-testid="detail-name-input"]', "Automated Tier2 Bot")
        page.fill('[data-testid="detail-address-input"]', "100 Bot Lane")
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
        # Naive Tier 2 bot performs a direct instant click instead of holding for hold_ms
        page.click('[data-testid="stepup-hold-btn"]')

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
        tier="tier2",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "mode": "playwright_page",
            "headless": True,
            "webdriver": True,
            "direct_fill": True,
            "direct_click": True,
            "attempt_stepup": attempt_stepup,
        },
        latency_ms=latency_ms,
    )


def run_tier2_session(
    base_url: str = "http://127.0.0.1:8000",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    endpoint_path: str | None = None,
    identifier_length: int = 12,
    fill_delay_ms: float = 45.0,
    click_delay_ms: float = 85.0,
    click_hold_ms: float = 12.0,
    ua_major: int = 130,
    viewport_w: int = 1280,
    viewport_h: int = 720,
    attempt_stepup: bool = False,
    allowlist_path: Path | None = None,
    page: PlaywrightPageLike | None = None,
    post_fn: HttpPostFn | None = None,
    get_fn: HttpGetFn | None = None,
) -> SimRunResult:
    """Execute one Tier 2 Playwright-default bot session against ``base_url``.

    Validates ``base_url`` against ``simulator/allowlist.txt`` before making any call.
    When ``page`` is supplied, drives the Playwright ``Page`` directly via
    :func:`drive_tier2_playwright_page`. Otherwise executes the exact SDK assessment and
    portal request flow produced by a default headless Playwright browser performing
    direct ``page.fill()`` and ``page.click()``.
    """
    clean_base = validate_target_url(base_url, allowlist_path=allowlist_path).rstrip(
        "/"
    )
    if page is not None:
        return drive_tier2_playwright_page(
            page,
            clean_base,
            protection_mode=protection_mode,
            action=action,
            identifier="9" * max(4, identifier_length),
            attempt_stepup=attempt_stepup,
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

    t0 = time.perf_counter()
    user_agent = (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) HeadlessChrome/{ua_major}.0.0.0 Safari/537.36"
    )
    headers: dict[str, str] = {"User-Agent": user_agent}

    env_signals = build_tier2_env_signals(
        ua_major=ua_major,
        viewport_w=viewport_w,
        viewport_h=viewport_h,
    )
    behaviour_payload = build_tier2_behaviour_payload(
        fill_delay_ms=fill_delay_ms,
        click_delay_ms=click_delay_ms,
        click_hold_ms=click_hold_ms,
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
                if challenge_id:
                    n2_status, n2_body = do_get(nonce_url, headers)
                    nonce2 = str(n2_body.get("nonce", "")) if n2_status == 200 else ""
                    if nonce2:
                        # Tier 2 naive direct click on step-up button (15 ms hold -> fails)
                        c_status, c_body = do_post(
                            challenge_url,
                            {
                                "nonce": nonce2,
                                "challenge_id": challenge_id,
                                "action": action,
                                "hold_start_ms": 1000.0,
                                "hold_end_ms": 1015.0,
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
        tier="tier2",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "headless": True,
            "webdriver": True,
            "direct_fill": True,
            "direct_click": True,
            "fill_delay_ms": round(fill_delay_ms, 2),
            "click_delay_ms": round(click_delay_ms, 2),
            "click_hold_ms": round(click_hold_ms, 2),
            "ua_major": ua_major,
            "attempt_stepup": attempt_stepup,
        },
        latency_ms=latency_ms,
    )

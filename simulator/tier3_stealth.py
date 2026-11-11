"""Tier 3 bot simulator: Playwright with basic automation-hiding adjustments (P7-14).

Purpose:
- This tier exists to test the **environment rule layer** (``R02``–``R12``) and its interaction
  with the behavioural models when a bot applies common, basic "stealth" adjustments to a
  Playwright browser context (such as overriding ``navigator.webdriver = false``).
- Keeps adjustments basic, transparent, and documented:
  1. ``"inconsistent_ua_platform"`` (default): hides ``navigator.webdriver`` (so ``R02_WEBDRIVER``
     does not fire) and spoofs a macOS User-Agent string, but forgets to align
     ``navigator.platform`` / ``userAgentData.platform`` (``Win32`` / ``Windows``), leaves
     headless SwiftShader software WebGL (``R06``), and trips ``Function.prototype.toString``
     native-function integrity (``R10``).
  2. ``"viewport_touch_mismatch"``: hides ``navigator.webdriver`` and spoofs an Android mobile
     User-Agent on a desktop headless context with ``max_touch_points=0`` and ``outer_w=0``,
     firing ``R08_VIEWPORT_ANOMALY`` and ``R09_TOUCH_INCONSISTENT``.
  3. ``"clean_env_linear_input"``: aligns environment fields so ``R02``–``R10`` do not fire, and
     uses Playwright's built-in linear ``mouse.move(..., steps=N)`` and fixed-delay
     ``keyboard.type(..., delay=D)`` (zero jitter, constant velocity, constant keystroke rhythm).
- Always validates the target URL against ``simulator/allowlist.txt`` via
  :func:`validate_target_url` before any navigation or HTTP request.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal, Protocol

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

Tier3Profile = Literal[
    "inconsistent_ua_platform",
    "viewport_touch_mismatch",
    "clean_env_linear_input",
]

TIER3_PROFILES: tuple[Tier3Profile, ...] = (
    "inconsistent_ua_platform",
    "viewport_touch_mismatch",
    "clean_env_linear_input",
)

# Documented basic context init script used by Tier 3 to hide navigator.webdriver
# and spoof non-zero desktop plugins. Because it redefines getters directly on navigator,
# naive property descriptor / Function.prototype.toString checks can detect tampering.
TIER3_INIT_SCRIPT: str = """
(() => {
  Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
    configurable: true,
  });
  Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3],
    configurable: true,
  });
  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-IN', 'en-US'],
    configurable: true,
  });
})();
""".strip()


class PlaywrightContextOrPageWithInitLike(Protocol):
    """Protocol for a Playwright ``BrowserContext`` or ``Page`` supporting ``add_init_script``."""

    def add_init_script(self, script: str) -> Any: ...


def apply_tier3_context_adjustments(
    target: PlaywrightContextOrPageWithInitLike | object,
) -> bool:
    """Apply basic documented automation-hiding adjustments to a Playwright context or page.

    Returns ``True`` if ``add_init_script`` was invoked on ``target``, ``False`` otherwise.
    """
    add_fn = getattr(target, "add_init_script", None)
    if callable(add_fn):
        add_fn(TIER3_INIT_SCRIPT)
        return True
    return False


def build_tier3_env_signals(
    profile: Tier3Profile = "inconsistent_ua_platform",
    *,
    ua_major: int = 130,
    viewport_w: int = 1280,
    viewport_h: int = 720,
) -> dict[str, Any]:
    """Build coarse environment signals for the chosen Tier 3 stealth profile.

    In all Tier 3 profiles, ``webdriver`` is ``False`` (bypassing ``R02_WEBDRIVER``).
    """
    if profile == "inconsistent_ua_platform":
        # Hides webdriver, sets a macOS UA, and spoofs 3 plugins, but leaves Win32 platform,
        # Windows client-hints, SwiftShader software WebGL, and fails native_fn_integrity_ok.
        return {
            "webdriver": False,
            "ua_family": "chrome",
            "ua_major": ua_major,
            "ua_os": "macos",
            "platform": "Win32",
            "hints_brands": ["Chromium", "Google Chrome"],
            "hints_platform": "Windows",
            "languages_count": 2,
            "lang_primary": "en-IN",
            "timezone_offset_min": 300,  # US UTC-5 offset with en-IN locale -> R05
            "screen_w_bucket": 1920,
            "screen_h_bucket": 1080,
            "viewport_w": viewport_w,
            "viewport_h": viewport_h,
            "outer_w": viewport_w,
            "outer_h": viewport_h,
            "dpr_bucket": 1.0,
            "hw_concurrency_bucket": 8,
            "device_memory_bucket": 8.0,
            "webgl_renderer_class": "software",
            "plugins_count": 3,
            "max_touch_points": 0,
            "touch_event_supported": False,
            "native_fn_integrity_ok": False,
            "storage_available": True,
            "visibility": "visible",
        }

    if profile == "viewport_touch_mismatch":
        # Hides webdriver and claims an Android mobile UA, but runs in a desktop headless
        # window with outer_w=0 and max_touch_points=0 (triggering R08 and R09).
        return {
            "webdriver": False,
            "ua_family": "chrome",
            "ua_major": ua_major,
            "ua_os": "android",
            "platform": "Linux armv8l",
            "hints_brands": ["Chromium", "Google Chrome"],
            "hints_platform": "Android",
            "languages_count": 2,
            "lang_primary": "en-IN",
            "timezone_offset_min": -330,
            "screen_w_bucket": 1280,
            "screen_h_bucket": 720,
            "viewport_w": viewport_w,
            "viewport_h": viewport_h,
            "outer_w": 0,
            "outer_h": 0,
            "dpr_bucket": 2.0,
            "hw_concurrency_bucket": 8,
            "device_memory_bucket": 4.0,
            "webgl_renderer_class": "software",
            "plugins_count": 0,
            "max_touch_points": 0,
            "touch_event_supported": False,
            "native_fn_integrity_ok": False,
            "storage_available": True,
            "visibility": "visible",
        }

    # "clean_env_linear_input": consistent desktop environment signals (R02-R10 clean)
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
        "webgl_renderer_class": "hardware",
        "plugins_count": 5,
        "max_touch_points": 0,
        "touch_event_supported": False,
        "native_fn_integrity_ok": True,
        "storage_available": True,
        "visibility": "visible",
    }


def build_tier3_behaviour_payload(
    *,
    num_mouse_steps: int = 24,
    step_interval_ms: float = 10.0,
    num_keys: int = 12,
    key_dwell_ms: float = 35.0,
    key_flight_ms: float = 40.0,
    start_x: float = 80.0,
    start_y: float = 90.0,
    end_x: float = 240.0,
    end_y: float = 320.0,
    initial_delay_ms: float = 160.0,
) -> dict[str, Any]:
    """Build mechanical linear-interpolation mouse and fixed-delay keystroke telemetry.

    Simulates Playwright's ``page.mouse.move(x, y, steps=N)`` (collinear points, zero
    curvature, constant speed) and ``page.keyboard.type(text, delay=D)`` (identical dwell
    and flight intervals).
    """
    steps = max(4, min(num_mouse_steps, 200))
    dt = max(2.0, step_interval_ms)
    t_cursor = max(20.0, initial_delay_ms)

    points: list[list[float]] = []
    for i in range(steps):
        frac = i / float(steps - 1)
        x = round(start_x + (end_x - start_x) * frac, 2)
        y = round(start_y + (end_y - start_y) * frac, 2)
        t_pt = round(t_cursor + i * dt, 2)
        points.append([x, y, t_pt])

    t_after_move = points[-1][2] + 20.0
    key_events: list[list[object]] = []
    k_count = max(4, min(num_keys, 64))
    dwell = max(5.0, key_dwell_ms)
    flight = max(5.0, key_flight_ms)

    t_key = t_after_move
    for _ in range(k_count):
        down_ms = round(t_key, 2)
        up_ms = round(down_ms + dwell, 2)
        key_events.append(["digit", down_ms, up_ms])
        t_key = up_ms + flight

    click_down = round(t_key + 25.0, 2)
    click_up = round(click_down + 20.0, 2)

    return {
        "mouse": {
            "points": points,
            "clicks": [[round(end_x, 2), round(end_y, 2), click_down, click_up]],
            "untrusted_count": 0,
            "wheel_events": 0,
        },
        "keys": {
            "events": key_events,
            "paste_events": 0,
            "autofill_suspected": False,
            "untrusted_count": 0,
        },
        "timing": {
            "ms_since_load": round(click_up + 30.0, 2),
            "ms_to_first_interaction": round(t_cursor, 2),
            "ms_since_nonce": round(click_up - t_cursor + 25.0, 2),
            "scroll_events": 0,
            "focus_changes": 2,
        },
        "device_class": "desktop",
    }


def drive_tier3_playwright_page(
    page: PlaywrightPageLike,
    portal_url: str = "http://127.0.0.1:5173",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    profile: Tier3Profile = "inconsistent_ua_platform",
    identifier: str = "999900001234",
    attempt_stepup: bool = False,
    allowlist_path: Path | None = None,
) -> SimRunResult:
    """Drive a Playwright ``Page`` after applying Tier 3 stealth init script adjustments.

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
    init_applied = apply_tier3_context_adjustments(page)
    page.goto(target_page_url)

    result_selector = '[data-testid="otp-result"]'
    if action == "details_update":
        page.fill('[data-testid="detail-name-input"]', "Tier3 Stealth Bot")
        page.fill('[data-testid="detail-address-input"]', "200 Stealth Road")
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
        tier="tier3",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "mode": "playwright_page",
            "profile": profile,
            "webdriver": False,
            "init_script_applied": init_applied,
            "attempt_stepup": attempt_stepup,
        },
        latency_ms=latency_ms,
    )


def run_tier3_session(
    base_url: str = "http://127.0.0.1:8000",
    *,
    protection_mode: str = "passive",
    action: str = "otp_request",
    profile: Tier3Profile = "inconsistent_ua_platform",
    endpoint_path: str | None = None,
    identifier_length: int = 12,
    num_mouse_steps: int = 24,
    step_interval_ms: float = 10.0,
    key_dwell_ms: float = 35.0,
    key_flight_ms: float = 40.0,
    ua_major: int = 130,
    viewport_w: int = 1280,
    viewport_h: int = 720,
    attempt_stepup: bool = False,
    allowlist_path: Path | None = None,
    page: PlaywrightPageLike | None = None,
    post_fn: HttpPostFn | None = None,
    get_fn: HttpGetFn | None = None,
) -> SimRunResult:
    """Execute one Tier 3 stealth-adjusted Playwright bot session against ``base_url``.

    Validates ``base_url`` against ``simulator/allowlist.txt`` before making any call.
    """
    clean_base = validate_target_url(base_url, allowlist_path=allowlist_path).rstrip(
        "/"
    )
    if page is not None:
        return drive_tier3_playwright_page(
            page,
            clean_base,
            protection_mode=protection_mode,
            action=action,
            profile=profile,
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
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{ua_major}.0.0.0 Safari/537.36"
        if profile == "inconsistent_ua_platform"
        else f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{ua_major}.0.0.0 Safari/537.36"
    )
    headers: dict[str, str] = {"User-Agent": user_agent}

    env_signals = build_tier3_env_signals(
        profile=profile,
        ua_major=ua_major,
        viewport_w=viewport_w,
        viewport_h=viewport_h,
    )
    behaviour_payload = build_tier3_behaviour_payload(
        num_mouse_steps=num_mouse_steps,
        step_interval_ms=step_interval_ms,
        num_keys=max(4, identifier_length),
        key_dwell_ms=key_dwell_ms,
        key_flight_ms=key_flight_ms,
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
                        # Tier 3 attempts a short 250ms hold
                        c_status, c_body = do_post(
                            challenge_url,
                            {
                                "nonce": nonce2,
                                "challenge_id": challenge_id,
                                "action": action,
                                "hold_start_ms": 1000.0,
                                "hold_end_ms": 1250.0,
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
        tier="tier3",
        protection_mode=protection_mode,
        action=action,
        outcome=outcome,
        portal_status=portal_status,
        assess_decision=assess_decision,
        assess_band=assess_band,
        params={
            "profile": profile,
            "webdriver": False,
            "num_mouse_steps": num_mouse_steps,
            "step_interval_ms": round(step_interval_ms, 2),
            "key_dwell_ms": round(key_dwell_ms, 2),
            "key_flight_ms": round(key_flight_ms, 2),
            "ua_major": ua_major,
            "attempt_stepup": attempt_stepup,
        },
        latency_ms=latency_ms,
    )

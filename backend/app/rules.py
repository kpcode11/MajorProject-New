"""Pure environment rule-layer checks (Phase 4, P4-02).

Deterministic, explainable checks that require no machine learning model.
They catch trivial automation and feed the final decision.

Each rule is implemented as a small pure function returning:
    RuleResult(id, fired: bool, weight: float, reason: str)

Privacy: rules operate solely on bucketed/coarse environment signals and
aggregate behaviour metrics. No unique fingerprint hash is computed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas import EnvSignals

# ---------------------------------------------------------------------------
# Rule result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleResult:
    """Outcome of evaluating a single detection rule.

    Attributes:
        id: Unique rule identifier (e.g. 'R02_WEBDRIVER').
        fired: True if the suspicious condition was triggered.
        weight: Default or configured weight of the rule in [0.0, 1.0].
        reason: Explanatory message indicating why the rule fired or passed.
    """

    id: str
    fired: bool
    weight: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Convert rule result to a dictionary representation."""
        return {
            "id": self.id,
            "fired": self.fired,
            "weight": self.weight,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Default rule weights (Appendix C.2 / Phase 4 plan)
# ---------------------------------------------------------------------------

DEFAULT_RULE_WEIGHTS: dict[str, float] = {
    "R01_NO_PAYLOAD": 0.80,
    "R02_WEBDRIVER": 0.60,
    "R03_UA_PLATFORM_MISMATCH": 0.30,
    "R04_UA_HINTS_MISMATCH": 0.30,
    "R05_TZ_LANG_MISMATCH": 0.10,
    "R06_SOFTWARE_RENDERER": 0.15,
    "R07_ZERO_PLUGINS_DESKTOP": 0.10,
    "R08_VIEWPORT_ANOMALY": 0.30,
    "R09_TOUCH_INCONSISTENT": 0.10,
    "R10_NATIVE_FUNCTION_TAMPER": 0.30,
    "R11_UNTRUSTED_EVENTS": 0.60,
    "R12_TOO_FAST": 0.30,
    "R13_RATE_LIMIT": 1.00,
}


def _coerce_env(env: EnvSignals | dict[str, Any] | None) -> EnvSignals | None:
    """Coerce input into an EnvSignals instance if a dictionary is provided."""
    if env is None or isinstance(env, EnvSignals):
        return env
    return EnvSignals(**env)


def _resolve_weight(rule_id: str, custom_weight: float | None) -> float:
    """Resolve weight using custom override or default dictionary."""
    if custom_weight is not None:
        return float(custom_weight)
    return DEFAULT_RULE_WEIGHTS.get(rule_id, 0.30)


# ---------------------------------------------------------------------------
# R01 — No behaviour/environment payload at all
# ---------------------------------------------------------------------------


def check_r01_no_payload(
    env: EnvSignals | dict[str, Any] | None = None,
    behaviour: dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R01: Fired when no environment or behaviour payload is provided."""
    rule_id = "R01_NO_PAYLOAD"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    env_empty = coerced_env is None or coerced_env.is_empty()
    behaviour_empty = (
        behaviour is None
        or len(behaviour) == 0
        or all(
            v is None or (isinstance(v, (dict, list)) and len(v) == 0) for v in behaviour.values()
        )
    )

    fired = env_empty and behaviour_empty
    reason = (
        "No environment or behaviour payload provided"
        if fired
        else "Environment or behaviour payload present"
    )
    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R02 — navigator.webdriver == true
# ---------------------------------------------------------------------------


def check_r02_webdriver(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R02: Fired when navigator.webdriver is true."""
    rule_id = "R02_WEBDRIVER"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = bool(coerced_env and coerced_env.webdriver is True)
    reason = (
        "navigator.webdriver flag is true"
        if fired
        else "navigator.webdriver flag is not set or false"
    )
    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R03 — UA OS family inconsistent with navigator.platform
# ---------------------------------------------------------------------------


def check_r03_ua_platform_mismatch(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R03: Fired when UA OS family is inconsistent with navigator.platform."""
    rule_id = "R03_UA_PLATFORM_MISMATCH"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = False
    reason = "UA OS and platform are consistent"

    if coerced_env and coerced_env.ua_os and coerced_env.platform:
        os_name = coerced_env.ua_os.strip().lower()
        platform_name = coerced_env.platform.strip().lower()

        if os_name == "windows" and not platform_name.startswith("win"):
            fired = True
        elif os_name == "macos" and not platform_name.startswith("mac"):
            fired = True
        elif os_name == "linux" and (
            platform_name.startswith("win") or platform_name.startswith("mac")
        ):
            fired = True
        elif os_name == "android" and (
            platform_name.startswith("win") or platform_name.startswith("mac")
        ):
            fired = True
        elif os_name == "ios" and not (
            any(k in platform_name for k in ("iphone", "ipad", "ipod"))
            or platform_name.startswith("mac")
        ):
            fired = True

        if fired:
            reason = (
                f"UA OS '{coerced_env.ua_os}' is inconsistent with "
                f"navigator.platform '{coerced_env.platform}'"
            )

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R04 — UA vs Client Hints brand/version/platform inconsistent
# ---------------------------------------------------------------------------


def check_r04_ua_hints_mismatch(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R04: Fired when UA contradicts Client Hints platform or brand values."""
    rule_id = "R04_UA_HINTS_MISMATCH"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = False
    reason = "UA and client hints are consistent"

    if coerced_env:
        # Check platform mismatch
        if coerced_env.ua_os and coerced_env.hints_platform:
            ua_os = coerced_env.ua_os.strip().lower()
            hp = coerced_env.hints_platform.strip().lower()
            if ua_os == "windows" and "win" not in hp:
                fired = True
            elif ua_os == "macos" and "mac" not in hp:
                fired = True
            elif ua_os == "linux" and "linux" not in hp and "android" not in hp:
                fired = True
            elif ua_os == "android" and "android" not in hp:
                fired = True
            elif ua_os == "ios" and "ios" not in hp:
                fired = True

            if fired:
                reason = (
                    f"UA OS '{coerced_env.ua_os}' contradicts "
                    f"client-hints platform '{coerced_env.hints_platform}'"
                )

        # Check browser family vs hints brands
        if not fired and coerced_env.ua_family and coerced_env.hints_brands:
            fam = coerced_env.ua_family.strip().lower()
            brands_text = " ".join(b.strip().lower() for b in coerced_env.hints_brands)
            if fam in ("firefox", "safari"):
                if "chromium" in brands_text or "google chrome" in brands_text:
                    fired = True
                    reason = (
                        f"UA browser '{coerced_env.ua_family}' contradicts "
                        f"Chromium client hints {coerced_env.hints_brands}"
                    )
            elif fam == "chrome":
                if (
                    "chromium" not in brands_text
                    and "google chrome" not in brands_text
                    and "chrome" not in brands_text
                ):
                    fired = True
                    reason = (
                        f"UA browser 'chrome' missing from client hints {coerced_env.hints_brands}"
                    )

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R05 — Timezone and language list implausible together (soft)
# ---------------------------------------------------------------------------


def check_r05_tz_lang_mismatch(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R05: Soft check for implausible timezone offset and primary language."""
    rule_id = "R05_TZ_LANG_MISMATCH"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = False
    reason = "Timezone offset and language are plausible"

    if coerced_env and coerced_env.timezone_offset_min is not None:
        offset = coerced_env.timezone_offset_min
        # Earth valid timezone offsets: UTC-12 (+720 min) to UTC+14 (-840 min)
        if offset < -840 or offset > 720:
            fired = True
            reason = (
                f"Timezone offset {offset} min is outside valid terrestrial range (-840 to +720)"
            )
        elif coerced_env.lang_primary:
            lang = coerced_env.lang_primary.strip()
            parts = lang.replace("_", "-").split("-")
            country = parts[-1].upper() if len(parts) > 1 and len(parts[-1]) == 2 else None

            # Standard regional bounds (min_offset_min, max_offset_min)
            regional_bounds: dict[str, tuple[int, int]] = {
                "IN": (-390, -270),  # India: UTC+5:30 = -330
                "JP": (-600, -480),  # Japan: UTC+9 = -540
                "KR": (-600, -480),  # Korea: UTC+9 = -540
                "CN": (-540, -420),  # China: UTC+8 = -480
                "TW": (-540, -420),  # Taiwan: UTC+8 = -480
                "AU": (-660, -480),  # Australia: -480 to -660
                "NZ": (-780, -660),  # New Zealand: -660 to -780
                "GB": (-60, 0),  # UK: 0 to -60
                "US": (240, 600),  # US: +240 to +600
                "CA": (210, 510),  # Canada: +210 to +510
            }

            if country and country in regional_bounds:
                min_exp, max_exp = regional_bounds[country]
                # Allow soft 6-hour tolerance before firing
                if offset < (min_exp - 360) or offset > (max_exp + 360):
                    fired = True
                    reason = (
                        f"Timezone offset {offset} min is implausible "
                        f"for region '{country}' in language '{lang}'"
                    )

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R06 — WebGL renderer class is a software renderer
# ---------------------------------------------------------------------------


def check_r06_software_renderer(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R06: Fired when WebGL renderer class is classified as software/virtual."""
    rule_id = "R06_SOFTWARE_RENDERER"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = False
    reason = "WebGL renderer is hardware or unclassified"

    if coerced_env and coerced_env.webgl_renderer_class:
        rend = coerced_env.webgl_renderer_class.strip().lower()
        if rend in ("software", "virtual", "swiftshader", "llvmpipe"):
            fired = True
            reason = (
                f"WebGL renderer classified as software/virtual: "
                f"'{coerced_env.webgl_renderer_class}'"
            )

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R07 — Desktop UA with zero plugins
# ---------------------------------------------------------------------------


def check_r07_zero_plugins_desktop(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R07: Fired when a desktop browser reports 0 plugins."""
    rule_id = "R07_ZERO_PLUGINS_DESKTOP"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = False
    reason = "Plugins count is consistent with platform"

    if coerced_env and coerced_env.plugins_count is not None and coerced_env.plugins_count == 0:
        is_desktop = False
        if coerced_env.ua_os and coerced_env.ua_os.strip().lower() in ("windows", "macos", "linux"):
            is_desktop = True
        elif coerced_env.platform:
            plat = coerced_env.platform.strip().lower()
            if any(k in plat for k in ("win", "mac", "linux")) and "android" not in plat:
                is_desktop = True

        if is_desktop:
            plat_name = coerced_env.ua_os or coerced_env.platform
            fired = True
            reason = f"Desktop platform ('{plat_name}') reported 0 plugins"

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R08 — Viewport anomaly
# ---------------------------------------------------------------------------


def check_r08_viewport_anomaly(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R08: Fired when viewport dimensions are non-positive or exceed screen/outer."""
    rule_id = "R08_VIEWPORT_ANOMALY"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = False
    reason = "Viewport and screen dimensions are consistent"

    if coerced_env:
        vw = coerced_env.viewport_w
        vh = coerced_env.viewport_h
        ow = coerced_env.outer_w
        oh = coerced_env.outer_h
        sw = coerced_env.screen_w_bucket
        sh = coerced_env.screen_h_bucket

        if (ow is not None and ow <= 0) or (oh is not None and oh <= 0):
            fired = True
            reason = f"Outer window dimensions are non-positive: ({ow}x{oh})"
        elif (vw is not None and vw <= 0) or (vh is not None and vh <= 0):
            fired = True
            reason = f"Viewport dimensions are non-positive: ({vw}x{vh})"
        elif (vw is not None and sw is not None and vw > sw) or (
            vh is not None and sh is not None and vh > sh
        ):
            fired = True
            reason = f"Viewport ({vw}x{vh}) is larger than screen resolution ({sw}x{sh})"
        elif (
            ow is not None
            and oh is not None
            and ow > 0
            and oh > 0
            and vw is not None
            and vh is not None
            and (vw > ow or vh > oh)
        ):
            fired = True
            reason = f"Viewport ({vw}x{vh}) is larger than outer window ({ow}x{oh})"

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R09 — Touch events vs claimed device class mismatch
# ---------------------------------------------------------------------------


def check_r09_touch_inconsistent(
    env: EnvSignals | dict[str, Any] | None = None,
    behaviour: dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R09: Fired when touch capabilities contradict claimed device class."""
    rule_id = "R09_TOUCH_INCONSISTENT"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = False
    reason = "Touch capabilities are consistent with claimed device"

    device_class = behaviour.get("device_class") if behaviour else None
    if coerced_env:
        is_mobile = False
        if coerced_env.ua_os and coerced_env.ua_os.strip().lower() in ("android", "ios"):
            is_mobile = True
        elif coerced_env.platform and any(
            k in coerced_env.platform.strip().lower() for k in ("iphone", "ipad", "android")
        ):
            is_mobile = True
        elif device_class and str(device_class).strip().lower() in ("mobile", "tablet"):
            is_mobile = True

        if is_mobile:
            dev_label = coerced_env.ua_os or device_class
            if coerced_env.max_touch_points is not None and coerced_env.max_touch_points == 0:
                fired = True
                reason = f"Mobile device ('{dev_label}') reported 0 maxTouchPoints"
            elif coerced_env.touch_event_supported is False:
                fired = True
                reason = f"Mobile device ('{dev_label}') reported touch_event_supported=False"
        elif (
            coerced_env.touch_event_supported is True
            and coerced_env.max_touch_points is not None
            and coerced_env.max_touch_points == 0
        ):
            fired = True
            reason = "touch_event_supported is True but maxTouchPoints is 0"

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R10 — Native-function integrity check failed
# ---------------------------------------------------------------------------


def check_r10_native_function_tamper(
    env: EnvSignals | dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R10: Fired when native-function integrity check failed."""
    rule_id = "R10_NATIVE_FUNCTION_TAMPER"
    w = _resolve_weight(rule_id, weight)
    coerced_env = _coerce_env(env)

    fired = bool(coerced_env and coerced_env.native_fn_integrity_ok is False)
    reason = (
        "Native function integrity check failed (function tampering detected)"
        if fired
        else "Native function integrity check passed or not evaluated"
    )
    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R11 — High fraction of isTrusted == false input events
# ---------------------------------------------------------------------------


def check_r11_untrusted_events(
    behaviour: dict[str, Any] | None = None,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R11: Fired when synthesized/untrusted input events are reported."""
    rule_id = "R11_UNTRUSTED_EVENTS"
    w = _resolve_weight(rule_id, weight)

    fired = False
    reason = "No untrusted input events detected"
    untrusted = 0

    if behaviour:
        if "mouse" in behaviour and isinstance(behaviour["mouse"], dict):
            untrusted += int(behaviour["mouse"].get("untrusted_count") or 0)
        if "keys" in behaviour and isinstance(behaviour["keys"], dict):
            untrusted += int(behaviour["keys"].get("untrusted_count") or 0)
        untrusted += int(behaviour.get("untrusted_count") or 0)

    if untrusted > 0:
        fired = True
        reason = f"Untrusted input events detected: count={untrusted}"

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R12 — Time from nonce issue to action under plausible minimum
# ---------------------------------------------------------------------------


def check_r12_too_fast(
    behaviour: dict[str, Any] | None = None,
    *,
    nonce_age_ms: float | None = None,
    min_ms: float = 200.0,
    weight: float | None = None,
) -> RuleResult:
    """Rule R12: Fired when action was completed unnaturally fast."""
    rule_id = "R12_TOO_FAST"
    w = _resolve_weight(rule_id, weight)

    fired = False
    reason = "Action timing within plausible limits"

    ms_since_nonce: float | None = None
    ms_to_first: float | None = None

    if behaviour and "timing" in behaviour and isinstance(behaviour["timing"], dict):
        ms_since_nonce = behaviour["timing"].get("ms_since_nonce")
        ms_to_first = behaviour["timing"].get("ms_to_first_interaction")

    if nonce_age_ms is not None:
        ms_since_nonce = (
            nonce_age_ms if ms_since_nonce is None else min(ms_since_nonce, nonce_age_ms)
        )

    if ms_since_nonce is not None and ms_since_nonce < min_ms:
        fired = True
        reason = f"Interaction submitted too fast after nonce: {ms_since_nonce}ms < {min_ms}ms"
    elif ms_to_first is not None and ms_to_first < 50.0:
        fired = True
        reason = f"First interaction occurred too fast after load: {ms_to_first}ms < 50ms"

    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# R13 — Request-rate caps exceeded (server-side, Store)
# ---------------------------------------------------------------------------


def check_r13_rate_limit(
    rate_limit_exceeded: bool = False,
    *,
    weight: float | None = None,
) -> RuleResult:
    """Rule R13: Hard rule fired when server-side request rate limit is exceeded."""
    rule_id = "R13_RATE_LIMIT"
    w = _resolve_weight(rule_id, weight)

    fired = bool(rate_limit_exceeded)
    reason = "Request rate limit exceeded" if fired else "Request rate within limits"
    return RuleResult(id=rule_id, fired=fired, weight=w, reason=reason)


# ---------------------------------------------------------------------------
# Convenience aliases (rule_r01_... -> check_r01_...)
# ---------------------------------------------------------------------------

rule_r01_no_payload = check_r01_no_payload
rule_r02_webdriver = check_r02_webdriver
rule_r03_ua_platform_mismatch = check_r03_ua_platform_mismatch
rule_r04_ua_hints_mismatch = check_r04_ua_hints_mismatch
rule_r05_tz_lang_mismatch = check_r05_tz_lang_mismatch
rule_r06_software_renderer = check_r06_software_renderer
rule_r07_zero_plugins_desktop = check_r07_zero_plugins_desktop
rule_r08_viewport_anomaly = check_r08_viewport_anomaly
rule_r09_touch_inconsistent = check_r09_touch_inconsistent
rule_r10_native_function_tamper = check_r10_native_function_tamper
rule_r11_untrusted_events = check_r11_untrusted_events
rule_r12_too_fast = check_r12_too_fast
rule_r13_rate_limit = check_r13_rate_limit


# ---------------------------------------------------------------------------
# Combined rule evaluation
# ---------------------------------------------------------------------------


def evaluate_all_rules(
    env: EnvSignals | dict[str, Any] | None,
    behaviour: dict[str, Any] | None = None,
    *,
    weights: dict[str, float] | None = None,
    rate_limit_exceeded: bool = False,
    nonce_age_ms: float | None = None,
    min_action_ms: float = 200.0,
) -> list[RuleResult]:
    """Evaluate all 13 rules in order and return their RuleResult list.

    Args:
        env: Environment signals (EnvSignals model or dictionary).
        behaviour: Behaviour payload dictionary.
        weights: Optional dictionary of rule ID to weight overrides.
        rate_limit_exceeded: Server-side flag indicating rate limit exceeded.
        nonce_age_ms: Server-side elapsed milliseconds since nonce was issued.
        min_action_ms: Plausible threshold in ms for minimum action time.

    Returns:
        List of RuleResult instances for R01 through R13.
    """
    w = weights or {}
    return [
        check_r01_no_payload(env, behaviour, weight=w.get("R01_NO_PAYLOAD")),
        check_r02_webdriver(env, weight=w.get("R02_WEBDRIVER")),
        check_r03_ua_platform_mismatch(env, weight=w.get("R03_UA_PLATFORM_MISMATCH")),
        check_r04_ua_hints_mismatch(env, weight=w.get("R04_UA_HINTS_MISMATCH")),
        check_r05_tz_lang_mismatch(env, weight=w.get("R05_TZ_LANG_MISMATCH")),
        check_r06_software_renderer(env, weight=w.get("R06_SOFTWARE_RENDERER")),
        check_r07_zero_plugins_desktop(env, weight=w.get("R07_ZERO_PLUGINS_DESKTOP")),
        check_r08_viewport_anomaly(env, weight=w.get("R08_VIEWPORT_ANOMALY")),
        check_r09_touch_inconsistent(env, behaviour, weight=w.get("R09_TOUCH_INCONSISTENT")),
        check_r10_native_function_tamper(env, weight=w.get("R10_NATIVE_FUNCTION_TAMPER")),
        check_r11_untrusted_events(behaviour, weight=w.get("R11_UNTRUSTED_EVENTS")),
        check_r12_too_fast(
            behaviour,
            nonce_age_ms=nonce_age_ms,
            min_ms=min_action_ms,
            weight=w.get("R12_TOO_FAST"),
        ),
        check_r13_rate_limit(rate_limit_exceeded, weight=w.get("R13_RATE_LIMIT")),
    ]

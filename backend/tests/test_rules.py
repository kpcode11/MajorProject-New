"""Unit tests for the environment rule layer (P4-02).

Tests each rule R01 through R13 for both passing and failing conditions,
weight overrides, missing-data safety, and full ruleset evaluation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import load_rule_config
from app.rules import (
    DEFAULT_RULE_WEIGHTS,
    RuleResult,
    RuleScore,
    check_r01_no_payload,
    check_r02_webdriver,
    check_r03_ua_platform_mismatch,
    check_r04_ua_hints_mismatch,
    check_r05_tz_lang_mismatch,
    check_r06_software_renderer,
    check_r07_zero_plugins_desktop,
    check_r08_viewport_anomaly,
    check_r09_touch_inconsistent,
    check_r10_native_function_tamper,
    check_r11_untrusted_events,
    check_r12_too_fast,
    check_r13_rate_limit,
    combine_rule_results,
    evaluate_all_rules,
    evaluate_rule_score,
)
from app.schemas import EnvSignals

# ---------------------------------------------------------------------------
# Fixtures: Benign desktop browser vs automation/bot
# ---------------------------------------------------------------------------


@pytest.fixture
def normal_chrome_env() -> EnvSignals:
    """Standard legitimate Chrome on Windows desktop from Appendix B.2."""
    return EnvSignals(
        webdriver=False,
        ua_family="chrome",
        ua_major=126,
        ua_os="windows",
        platform="Win32",
        hints_brands=["Chromium", "Google Chrome"],
        hints_platform="Windows",
        languages_count=2,
        lang_primary="en-IN",
        timezone_offset_min=-330,
        screen_w_bucket=1920,
        screen_h_bucket=1080,
        viewport_w=1280,
        viewport_h=720,
        outer_w=1296,
        outer_h=800,
        dpr_bucket=1.0,
        hw_concurrency_bucket=8,
        device_memory_bucket=8.0,
        webgl_renderer_class="hardware",
        plugins_count=5,
        max_touch_points=0,
        touch_event_supported=False,
        native_fn_integrity_ok=True,
        storage_available=True,
        visibility="visible",
    )


@pytest.fixture
def headless_bot_env() -> EnvSignals:
    """Standard headless automation default fixture."""
    return EnvSignals(
        webdriver=True,
        ua_family="chrome",
        ua_major=126,
        ua_os="windows",
        platform="Win32",
        hints_brands=["Chromium"],
        hints_platform="Windows",
        languages_count=1,
        lang_primary="en-US",
        timezone_offset_min=0,
        screen_w_bucket=1920,
        screen_h_bucket=1080,
        viewport_w=800,
        viewport_h=600,
        outer_w=0,
        outer_h=0,
        webgl_renderer_class="software",
        plugins_count=0,
        max_touch_points=0,
        touch_event_supported=False,
        native_fn_integrity_ok=False,
    )


# ---------------------------------------------------------------------------
# RuleResult structure and properties
# ---------------------------------------------------------------------------


class TestRuleResult:
    def test_construction_and_attributes(self) -> None:
        r = RuleResult(id="R02_WEBDRIVER", fired=True, weight=0.6, reason="webdriver true")
        assert r.id == "R02_WEBDRIVER"
        assert r.fired is True
        assert r.weight == 0.6
        assert r.reason == "webdriver true"

    def test_to_dict(self) -> None:
        r = RuleResult(id="R02_WEBDRIVER", fired=False, weight=0.6, reason="pass")
        d = r.to_dict()
        assert d == {"id": "R02_WEBDRIVER", "fired": False, "weight": 0.6, "reason": "pass"}

    def test_immutability(self) -> None:
        r = RuleResult(id="R02_WEBDRIVER", fired=False, weight=0.6, reason="pass")
        with pytest.raises(Exception):
            r.fired = True  # type: ignore[misc]


class TestRuleScore:
    def test_no_fired_rules_have_zero_score(self) -> None:
        result = combine_rule_results([RuleResult("R02_WEBDRIVER", False, 0.6, "passed")])
        assert isinstance(result, RuleScore)
        assert result.rule_score == 0.0
        assert result.reasons == []
        assert result.model_bypassed is False

    def test_fired_rules_use_noisy_or(self) -> None:
        result = combine_rule_results(
            [
                RuleResult("R02_WEBDRIVER", True, 0.6, "webdriver"),
                RuleResult("R06_SOFTWARE_RENDERER", True, 0.15, "software"),
            ]
        )
        assert result.rule_score == pytest.approx(0.66)
        assert result.fired_rules == ["R02_WEBDRIVER", "R06_SOFTWARE_RENDERER"]
        assert result.reasons == ["webdriver", "software"]
        assert result.model_bypassed is False

    def test_rate_limit_bypasses_model(self) -> None:
        result = combine_rule_results([RuleResult("R13_RATE_LIMIT", True, 1.0, "rate limit")])
        assert result.rule_score == 1.0
        assert result.model_bypassed is True
        assert result.hard_rule == "R13_RATE_LIMIT"
        assert "model bypass" in result.reasons[-1]

    def test_invalid_nonce_bypasses_model(self) -> None:
        result = combine_rule_results(
            [],
            invalid_nonce_or_signature=True,
        )
        assert result.rule_score == 1.0
        assert result.model_bypassed is True
        assert result.hard_rule == "INVALID_NONCE_OR_SIGNATURE"

    def test_rejects_invalid_fired_weight(self) -> None:
        with pytest.raises(ValueError, match=r"in \[0, 1\]"):
            combine_rule_results([RuleResult("R02_WEBDRIVER", True, 1.1, "bad")])

    def test_evaluate_rule_score_integrates_rule_evaluation(
        self, normal_chrome_env: EnvSignals
    ) -> None:
        result = evaluate_rule_score(normal_chrome_env, {})
        assert result.rule_score == pytest.approx(0.0)
        assert result.model_bypassed is False

    def test_disabled_rule_does_not_fire(self, headless_bot_env: EnvSignals) -> None:
        results = evaluate_all_rules(
            headless_bot_env,
            enabled={"R02_WEBDRIVER": False},
        )
        webdriver = next(result for result in results if result.id == "R02_WEBDRIVER")
        assert webdriver.fired is False
        assert webdriver.reason == "Rule disabled by configuration"

    def test_yaml_rule_config_loads(self) -> None:
        config = load_rule_config(Path(__file__).parents[1] / "config" / "rules.yaml")
        assert config.enabled["R02_WEBDRIVER"] is True
        assert config.weights["R13_RATE_LIMIT"] == 1.0

    def test_normal_chrome_fixture_has_near_zero_score(self, normal_chrome_env: EnvSignals) -> None:
        result = evaluate_rule_score(normal_chrome_env, {})
        assert result.rule_score == pytest.approx(0.0)
        assert result.fired_rules == []
        assert result.reasons == []

    def test_headless_fixture_fires_several_rules(self, headless_bot_env: EnvSignals) -> None:
        result = evaluate_rule_score(headless_bot_env, {})
        assert result.rule_score > 0.8
        assert len(result.fired_rules) >= 4
        assert {
            "R02_WEBDRIVER",
            "R06_SOFTWARE_RENDERER",
            "R07_ZERO_PLUGINS_DESKTOP",
            "R08_VIEWPORT_ANOMALY",
            "R10_NATIVE_FUNCTION_TAMPER",
        }.issubset(result.fired_rules)


# ---------------------------------------------------------------------------
# Individual rule tests: R01 to R13
# ---------------------------------------------------------------------------


class TestRule01NoPayload:
    def test_fires_when_both_none(self) -> None:
        res = check_r01_no_payload(None, None)
        assert res.fired is True
        assert res.id == "R01_NO_PAYLOAD"
        assert res.weight == DEFAULT_RULE_WEIGHTS["R01_NO_PAYLOAD"]

    def test_fires_when_both_empty(self) -> None:
        res = check_r01_no_payload(EnvSignals(), {})
        assert res.fired is True

    def test_passes_with_env_present(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r01_no_payload(normal_chrome_env, None)
        assert res.fired is False

    def test_passes_with_behaviour_present(self) -> None:
        res = check_r01_no_payload(None, {"mouse": {"points": [[1, 2, 3]]}})
        assert res.fired is False

    def test_custom_weight(self) -> None:
        res = check_r01_no_payload(None, None, weight=0.95)
        assert res.weight == 0.95


class TestRule02Webdriver:
    def test_fires_when_true(self) -> None:
        res = check_r02_webdriver(EnvSignals(webdriver=True))
        assert res.fired is True
        assert "webdriver" in res.reason

    def test_passes_when_false(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r02_webdriver(normal_chrome_env)
        assert res.fired is False

    def test_passes_when_none(self) -> None:
        res = check_r02_webdriver(EnvSignals())
        assert res.fired is False

    def test_dict_coercion(self) -> None:
        res = check_r02_webdriver({"webdriver": True})
        assert res.fired is True


class TestRule03UaPlatformMismatch:
    def test_fires_on_windows_ua_with_mac_platform(self) -> None:
        res = check_r03_ua_platform_mismatch(EnvSignals(ua_os="windows", platform="MacIntel"))
        assert res.fired is True

    def test_fires_on_macos_ua_with_win_platform(self) -> None:
        res = check_r03_ua_platform_mismatch(EnvSignals(ua_os="macos", platform="Win32"))
        assert res.fired is True

    def test_fires_on_linux_ua_with_win_platform(self) -> None:
        res = check_r03_ua_platform_mismatch(EnvSignals(ua_os="linux", platform="Win32"))
        assert res.fired is True

    def test_passes_on_consistent_windows(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r03_ua_platform_mismatch(normal_chrome_env)
        assert res.fired is False

    def test_passes_on_consistent_mac(self) -> None:
        res = check_r03_ua_platform_mismatch(EnvSignals(ua_os="macos", platform="MacIntel"))
        assert res.fired is False

    def test_passes_when_missing_values(self) -> None:
        assert check_r03_ua_platform_mismatch(EnvSignals(ua_os="windows")).fired is False
        assert check_r03_ua_platform_mismatch(EnvSignals(platform="Win32")).fired is False


class TestRule04UaHintsMismatch:
    def test_fires_on_platform_mismatch(self) -> None:
        res = check_r04_ua_hints_mismatch(EnvSignals(ua_os="windows", hints_platform="Linux"))
        assert res.fired is True

    def test_fires_on_firefox_with_chromium_hints(self) -> None:
        res = check_r04_ua_hints_mismatch(
            EnvSignals(ua_family="firefox", hints_brands=["Chromium", "Google Chrome"])
        )
        assert res.fired is True

    def test_fires_on_chrome_missing_from_brands(self) -> None:
        res = check_r04_ua_hints_mismatch(
            EnvSignals(ua_family="chrome", hints_brands=["MyCustomBrowser"])
        )
        assert res.fired is True

    def test_passes_on_consistent_hints(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r04_ua_hints_mismatch(normal_chrome_env)
        assert res.fired is False

    def test_passes_when_hints_absent(self) -> None:
        res = check_r04_ua_hints_mismatch(EnvSignals(ua_family="firefox", ua_os="windows"))
        assert res.fired is False


class TestRule05TzLangMismatch:
    def test_fires_on_invalid_terrestrial_offset(self) -> None:
        # Use model_construct to bypass schema validation so we can test the
        # rule logic directly with an out-of-range value.  In practice, the
        # schema rejects timezone_offset_min > 840, so this value would never
        # arrive from the API; the rule serves as a defence-in-depth guard.
        signals = EnvSignals.model_construct(timezone_offset_min=1000)
        res = check_r05_tz_lang_mismatch(signals)
        assert res.fired is True

    def test_fires_on_india_lang_with_us_tz(self) -> None:
        # India is -330; +480 is US West Coast (>13h difference)
        res = check_r05_tz_lang_mismatch(EnvSignals(lang_primary="en-IN", timezone_offset_min=480))
        assert res.fired is True

    def test_fires_on_japan_lang_with_us_tz(self) -> None:
        # Japan is -540; +300 is US East Coast
        res = check_r05_tz_lang_mismatch(EnvSignals(lang_primary="ja-JP", timezone_offset_min=300))
        assert res.fired is True

    def test_passes_on_matching_tz_and_lang(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r05_tz_lang_mismatch(normal_chrome_env)
        assert res.fired is False

    def test_passes_on_generic_lang(self) -> None:
        res = check_r05_tz_lang_mismatch(EnvSignals(lang_primary="en", timezone_offset_min=0))
        assert res.fired is False


class TestRule06SoftwareRenderer:
    def test_fires_on_software_renderer(self) -> None:
        res = check_r06_software_renderer(EnvSignals(webgl_renderer_class="software"))
        assert res.fired is True

    def test_fires_on_swiftshader(self) -> None:
        res = check_r06_software_renderer(EnvSignals(webgl_renderer_class="swiftshader"))
        assert res.fired is True

    def test_passes_on_hardware_renderer(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r06_software_renderer(normal_chrome_env)
        assert res.fired is False

    def test_passes_on_unknown_or_none(self) -> None:
        res = check_r06_software_renderer(EnvSignals(webgl_renderer_class="unknown"))
        assert res.fired is False


class TestRule07ZeroPluginsDesktop:
    def test_fires_on_desktop_with_zero_plugins(self) -> None:
        res = check_r07_zero_plugins_desktop(EnvSignals(ua_os="windows", plugins_count=0))
        assert res.fired is True

    def test_passes_on_desktop_with_plugins(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r07_zero_plugins_desktop(normal_chrome_env)
        assert res.fired is False

    def test_passes_on_mobile_with_zero_plugins(self) -> None:
        # Mobile browsers legitimately report 0 plugins
        res = check_r07_zero_plugins_desktop(EnvSignals(ua_os="android", plugins_count=0))
        assert res.fired is False


class TestRule08ViewportAnomaly:
    def test_fires_on_zero_outer_dimensions(self) -> None:
        res = check_r08_viewport_anomaly(
            EnvSignals(viewport_w=800, viewport_h=600, outer_w=0, outer_h=0)
        )
        assert res.fired is True

    def test_fires_on_viewport_larger_than_screen(self) -> None:
        res = check_r08_viewport_anomaly(
            EnvSignals(
                viewport_w=2560,
                viewport_h=1440,
                screen_w_bucket=1920,
                screen_h_bucket=1080,
            )
        )
        assert res.fired is True

    def test_fires_on_viewport_larger_than_outer(self) -> None:
        res = check_r08_viewport_anomaly(
            EnvSignals(viewport_w=1000, viewport_h=800, outer_w=900, outer_h=700)
        )
        assert res.fired is True

    def test_passes_on_normal_dimensions(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r08_viewport_anomaly(normal_chrome_env)
        assert res.fired is False


class TestRule09TouchInconsistent:
    def test_fires_on_mobile_with_zero_touch_points(self) -> None:
        res = check_r09_touch_inconsistent(
            EnvSignals(ua_os="android", max_touch_points=0, touch_event_supported=True)
        )
        assert res.fired is True

    def test_fires_on_mobile_with_touch_events_unsupported(self) -> None:
        res = check_r09_touch_inconsistent(
            EnvSignals(ua_os="ios", max_touch_points=5, touch_event_supported=False)
        )
        assert res.fired is True

    def test_fires_on_touch_supported_but_zero_points(self) -> None:
        res = check_r09_touch_inconsistent(
            EnvSignals(ua_os="windows", touch_event_supported=True, max_touch_points=0)
        )
        assert res.fired is True

    def test_passes_on_standard_desktop(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r09_touch_inconsistent(normal_chrome_env)
        assert res.fired is False

    def test_passes_on_standard_mobile(self) -> None:
        res = check_r09_touch_inconsistent(
            EnvSignals(ua_os="android", max_touch_points=5, touch_event_supported=True)
        )
        assert res.fired is False


class TestRule10NativeFunctionTamper:
    def test_fires_when_integrity_failed(self) -> None:
        res = check_r10_native_function_tamper(EnvSignals(native_fn_integrity_ok=False))
        assert res.fired is True

    def test_passes_when_integrity_ok(self, normal_chrome_env: EnvSignals) -> None:
        res = check_r10_native_function_tamper(normal_chrome_env)
        assert res.fired is False

    def test_passes_when_none(self) -> None:
        res = check_r10_native_function_tamper(EnvSignals())
        assert res.fired is False


class TestRule11UntrustedEvents:
    def test_fires_on_mouse_untrusted(self) -> None:
        res = check_r11_untrusted_events({"mouse": {"untrusted_count": 5}})
        assert res.fired is True
        assert "5" in res.reason

    def test_fires_on_keys_untrusted(self) -> None:
        res = check_r11_untrusted_events({"keys": {"untrusted_count": 2}})
        assert res.fired is True

    def test_fires_on_top_level_untrusted(self) -> None:
        res = check_r11_untrusted_events({"untrusted_count": 1})
        assert res.fired is True

    def test_passes_on_clean_events(self) -> None:
        res = check_r11_untrusted_events(
            {"mouse": {"untrusted_count": 0}, "keys": {"untrusted_count": 0}}
        )
        assert res.fired is False

    def test_passes_when_empty_or_none(self) -> None:
        assert check_r11_untrusted_events(None).fired is False
        assert check_r11_untrusted_events({}).fired is False


class TestRule12TooFast:
    def test_fires_on_very_short_nonce_time(self) -> None:
        res = check_r12_too_fast(
            behaviour={"timing": {"ms_since_nonce": 45}},
            min_ms=200.0,
        )
        assert res.fired is True

    def test_fires_on_server_nonce_age(self) -> None:
        res = check_r12_too_fast(nonce_age_ms=80.0, min_ms=200.0)
        assert res.fired is True

    def test_fires_on_sub_50ms_first_interaction(self) -> None:
        res = check_r12_too_fast(
            behaviour={"timing": {"ms_since_nonce": 500, "ms_to_first_interaction": 12}}
        )
        assert res.fired is True

    def test_passes_on_plausible_timing(self) -> None:
        res = check_r12_too_fast(
            behaviour={"timing": {"ms_since_nonce": 2400, "ms_to_first_interaction": 850}},
            min_ms=200.0,
        )
        assert res.fired is False


class TestRule13RateLimit:
    def test_fires_when_exceeded(self) -> None:
        res = check_r13_rate_limit(True)
        assert res.fired is True
        assert res.weight == 1.0

    def test_passes_when_normal(self) -> None:
        res = check_r13_rate_limit(False)
        assert res.fired is False


# ---------------------------------------------------------------------------
# Full ruleset evaluation tests
# ---------------------------------------------------------------------------


class TestEvaluateAllRules:
    def test_all_13_rules_evaluated(self, normal_chrome_env: EnvSignals) -> None:
        results = evaluate_all_rules(
            normal_chrome_env, behaviour={"timing": {"ms_since_nonce": 3000}}
        )
        assert len(results) == 13
        rule_ids = [r.id for r in results]
        assert rule_ids == [
            "R01_NO_PAYLOAD",
            "R02_WEBDRIVER",
            "R03_UA_PLATFORM_MISMATCH",
            "R04_UA_HINTS_MISMATCH",
            "R05_TZ_LANG_MISMATCH",
            "R06_SOFTWARE_RENDERER",
            "R07_ZERO_PLUGINS_DESKTOP",
            "R08_VIEWPORT_ANOMALY",
            "R09_TOUCH_INCONSISTENT",
            "R10_NATIVE_FUNCTION_TAMPER",
            "R11_UNTRUSTED_EVENTS",
            "R12_TOO_FAST",
            "R13_RATE_LIMIT",
        ]

    def test_normal_chrome_fixture_fires_zero_rules(self, normal_chrome_env: EnvSignals) -> None:
        results = evaluate_all_rules(
            normal_chrome_env,
            behaviour={
                "mouse": {"untrusted_count": 0},
                "timing": {"ms_since_nonce": 3500, "ms_to_first_interaction": 800},
            },
        )
        fired = [r.id for r in results if r.fired]
        assert fired == [], f"Expected 0 fired rules for normal chrome fixture, got: {fired}"

    def test_headless_bot_fixture_fires_multiple_rules(self, headless_bot_env: EnvSignals) -> None:
        results = evaluate_all_rules(
            headless_bot_env,
            behaviour={
                "mouse": {"untrusted_count": 10},
                "timing": {"ms_since_nonce": 20},
            },
        )
        fired = {r.id for r in results if r.fired}
        # Expected to fire: R02 (webdriver), R06 (software renderer), R07 (zero plugins),
        # R08 (viewport outer 0x0), R10 (native integrity False), R11 (untrusted), R12 (too fast)
        expected = {
            "R02_WEBDRIVER",
            "R06_SOFTWARE_RENDERER",
            "R07_ZERO_PLUGINS_DESKTOP",
            "R08_VIEWPORT_ANOMALY",
            "R10_NATIVE_FUNCTION_TAMPER",
            "R11_UNTRUSTED_EVENTS",
            "R12_TOO_FAST",
        }
        assert expected.issubset(fired), f"Missing expected rules: {expected - fired}"

    def test_custom_weight_overrides(self, normal_chrome_env: EnvSignals) -> None:
        overrides = {"R02_WEBDRIVER": 0.99, "R03_UA_PLATFORM_MISMATCH": 0.44}
        results = evaluate_all_rules(normal_chrome_env, weights=overrides)
        by_id = {r.id: r for r in results}
        assert by_id["R02_WEBDRIVER"].weight == 0.99
        assert by_id["R03_UA_PLATFORM_MISMATCH"].weight == 0.44
        assert by_id["R05_TZ_LANG_MISMATCH"].weight == 0.10

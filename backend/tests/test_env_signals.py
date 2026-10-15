"""Tests for the environment signal schema (P4-01)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import EnvSignals

# ---------------------------------------------------------------------------
# Construction and defaults
# ---------------------------------------------------------------------------


class TestEnvSignalsConstruction:
    """EnvSignals can be built from the example in Appendix B.2."""

    def test_full_payload_from_appendix_b2(self) -> None:
        """All Appendix B.2 fields are accepted and round-trip correctly."""
        signals = EnvSignals(
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
            dpr_bucket=1,
            hw_concurrency_bucket=8,
            device_memory_bucket=8,
            plugins_count=5,
            max_touch_points=0,
            touch_event_supported=False,
            webgl_renderer_class="hardware",
            native_fn_integrity_ok=True,
            storage_available=True,
            visibility="visible",
        )
        assert signals.webdriver is False
        assert signals.ua_family == "chrome"
        assert signals.ua_major == 126
        assert signals.ua_os == "windows"
        assert signals.platform == "Win32"
        assert signals.hints_brands == ["Chromium", "Google Chrome"]
        assert signals.hints_platform == "Windows"
        assert signals.languages_count == 2
        assert signals.lang_primary == "en-IN"
        assert signals.timezone_offset_min == -330
        assert signals.screen_w_bucket == 1920
        assert signals.screen_h_bucket == 1080
        assert signals.viewport_w == 1280
        assert signals.viewport_h == 720
        assert signals.outer_w == 1296
        assert signals.outer_h == 800
        assert signals.dpr_bucket == 1
        assert signals.hw_concurrency_bucket == 8
        assert signals.device_memory_bucket == 8
        assert signals.webgl_renderer_class == "hardware"
        assert signals.plugins_count == 5
        assert signals.max_touch_points == 0
        assert signals.touch_event_supported is False
        assert signals.native_fn_integrity_ok is True
        assert signals.storage_available is True
        assert signals.visibility == "visible"

    def test_all_defaults_none(self) -> None:
        """An empty constructor succeeds and all fields default to None."""
        signals = EnvSignals()
        dump = signals.model_dump()
        for key, value in dump.items():
            assert value is None, f"{key} should default to None"

    def test_partial_payload(self) -> None:
        """A payload with only a few fields is valid."""
        signals = EnvSignals(webdriver=True, ua_family="firefox")
        assert signals.webdriver is True
        assert signals.ua_family == "firefox"
        assert signals.ua_major is None

    def test_from_dict(self) -> None:
        """Construct from a dict, simulating JSON deserialization."""
        raw = {
            "webdriver": False,
            "ua_family": "chrome",
            "screen_w_bucket": 1920,
            "max_touch_points": 10,
        }
        signals = EnvSignals(**raw)
        assert signals.screen_w_bucket == 1920
        assert signals.max_touch_points == 10

    def test_extra_fields_ignored_by_default(self) -> None:
        """Unknown fields don't cause validation errors."""
        # Pydantic v2 ignores extra fields by default.
        signals = EnvSignals.model_validate({"webdriver": False, "unknown_field": 42})
        assert signals.webdriver is False
        assert not hasattr(signals, "unknown_field")


# ---------------------------------------------------------------------------
# is_empty helper
# ---------------------------------------------------------------------------


class TestIsEmpty:
    """The is_empty() method detects a fully-None payload."""

    def test_empty_payload(self) -> None:
        assert EnvSignals().is_empty() is True

    def test_non_empty_when_one_field_set(self) -> None:
        assert EnvSignals(webdriver=False).is_empty() is False

    def test_non_empty_with_zero_value(self) -> None:
        """Zero is a valid value, not None."""
        assert EnvSignals(max_touch_points=0).is_empty() is False

    def test_non_empty_with_empty_list(self) -> None:
        """An empty list is not None."""
        assert EnvSignals(hints_brands=[]).is_empty() is False


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    """model_dump / model_validate round-trips preserve values."""

    def test_round_trip(self) -> None:
        original = EnvSignals(
            webdriver=True,
            ua_family="safari",
            ua_major=17,
            hints_brands=["Safari"],
            dpr_bucket=2.0,
            timezone_offset_min=0,
        )
        rebuilt = EnvSignals.model_validate(original.model_dump())
        assert rebuilt == original

    def test_json_round_trip(self) -> None:
        original = EnvSignals(
            webdriver=False,
            plugins_count=5,
            touch_event_supported=True,
        )
        json_str = original.model_dump_json()
        rebuilt = EnvSignals.model_validate_json(json_str)
        assert rebuilt == original


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


class TestTypeValidation:
    """Pydantic enforces the declared types."""

    def test_webdriver_rejects_non_bool(self) -> None:
        with pytest.raises(ValidationError):
            EnvSignals(webdriver=[1, 2])  # type: ignore[arg-type]

    def test_ua_major_rejects_float_string(self) -> None:
        with pytest.raises(ValidationError):
            EnvSignals(ua_major="abc")  # type: ignore[arg-type]

    def test_hints_brands_rejects_non_list(self) -> None:
        with pytest.raises(ValidationError):
            EnvSignals(hints_brands="chrome")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Privacy guarantee: no fingerprint hash field
# ---------------------------------------------------------------------------


class TestPrivacyGuarantees:
    """The schema must never contain a unique fingerprint hash."""

    def test_no_fingerprint_field(self) -> None:
        fields = set(EnvSignals.model_fields.keys())
        forbidden = {"fingerprint", "fingerprint_hash", "fp_hash", "device_id", "visitor_id"}
        overlap = fields & forbidden
        assert not overlap, f"Forbidden fingerprint fields found: {overlap}"

    def test_field_count_matches_b2(self) -> None:
        """We expect exactly the 26 fields from Appendix B.2."""
        assert len(EnvSignals.model_fields) == 26

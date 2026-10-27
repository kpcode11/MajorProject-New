"""Tests for API request/response schemas (P5-02).

Verifies field-level validation limits, key-class enforcement, cross-field
invariants, and round-trip serialisation for every public schema.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    AssessRequest,
    AssessResponse,
    BehaviourPayload,
    ChallengeAssessRequest,
    ChallengeInfo,
    ClickEvent,
    EnvSignals,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    KeyBehaviour,
    KeyEvent,
    ModelVersions,
    MouseBehaviour,
    NonceResponse,
    TimingSignals,
    TokenVerifyRequest,
    TokenVerifyResponse,
    TouchBehaviour,
    TouchGesture,
)

# ---------------------------------------------------------------------------
# EnvSignals (existing model; verify new field limits still pass)
# ---------------------------------------------------------------------------


class TestEnvSignals:
    def test_full_payload_accepted(self) -> None:
        s = EnvSignals(
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
        assert not s.is_empty()

    def test_empty_payload_is_empty(self) -> None:
        assert EnvSignals().is_empty()

    def test_ua_major_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EnvSignals(ua_major=-1)

    def test_timezone_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            EnvSignals(timezone_offset_min=1000)

    def test_ua_family_too_long(self) -> None:
        with pytest.raises(ValidationError):
            EnvSignals(ua_family="x" * 200)

    def test_hints_brands_too_many(self) -> None:
        with pytest.raises(ValidationError):
            EnvSignals(hints_brands=["brand"] * 20)


# ---------------------------------------------------------------------------
# MouseBehaviour
# ---------------------------------------------------------------------------


class TestMouseBehaviour:
    def test_valid_points(self) -> None:
        mb = MouseBehaviour(
            points=[[100.0, 200.0, 0.0], [101.0, 201.0, 16.0]],
            clicks=[[100.0, 200.0, 100.0, 150.0]],
            untrusted_count=0,
            wheel_events=3,
        )
        assert len(mb.points) == 2

    def test_too_many_points_rejected(self) -> None:
        points = [[float(i), float(i), float(i)] for i in range(601)]
        with pytest.raises(ValidationError):
            MouseBehaviour(points=points)

    def test_malformed_point_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MouseBehaviour(points=[[1.0, 2.0]])  # missing t_ms

    def test_malformed_click_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MouseBehaviour(clicks=[[1.0, 2.0, 3.0]])  # only 3 elements

    def test_negative_untrusted_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MouseBehaviour(untrusted_count=-1)


# ---------------------------------------------------------------------------
# ClickEvent
# ---------------------------------------------------------------------------


class TestClickEvent:
    def test_valid_click(self) -> None:
        c = ClickEvent(x=100.0, y=200.0, down_ms=100.0, up_ms=150.0)
        assert c.up_ms >= c.down_ms

    def test_up_before_down_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ClickEvent(x=0.0, y=0.0, down_ms=200.0, up_ms=100.0)

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ClickEvent(x=0.0, y=0.0, down_ms=-1.0, up_ms=0.0)

    def test_from_list(self) -> None:
        c = ClickEvent.from_list([10.0, 20.0, 100.0, 150.0])
        assert c.x == 10.0

    def test_from_list_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="click event"):
            ClickEvent.from_list([1.0, 2.0, 3.0])


# ---------------------------------------------------------------------------
# KeyEvent and KeyBehaviour
# ---------------------------------------------------------------------------


class TestKeyEvent:
    def test_valid_key_event(self) -> None:
        ke = KeyEvent(key_class="letter", down_ms=1000.0, up_ms=1080.0)
        assert ke.key_class == "letter"

    def test_invalid_key_class(self) -> None:
        with pytest.raises(ValidationError):
            KeyEvent(key_class="shift", down_ms=0.0, up_ms=50.0)

    def test_up_before_down_rejected(self) -> None:
        with pytest.raises(ValidationError):
            KeyEvent(key_class="digit", down_ms=500.0, up_ms=400.0)

    def test_all_valid_classes(self) -> None:
        for kc in ["letter", "digit", "space", "punct", "modifier", "enter", "backspace", "other"]:
            ke = KeyEvent(key_class=kc, down_ms=0.0, up_ms=50.0)
            assert ke.key_class == kc

    def test_from_list(self) -> None:
        ke = KeyEvent.from_list(["letter", 100.0, 160.0])
        assert ke.key_class == "letter"

    def test_from_list_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="key event"):
            KeyEvent.from_list(["letter", 100.0])


class TestKeyBehaviour:
    def test_valid_events(self) -> None:
        kb = KeyBehaviour(
            events=[["letter", 100.0, 160.0], ["space", 200.0, 230.0]],
            paste_events=0,
            autofill_suspected=False,
        )
        assert len(kb.events) == 2

    def test_too_many_events_rejected(self) -> None:
        events = [["letter", float(i), float(i) + 50] for i in range(301)]
        with pytest.raises(ValidationError):
            KeyBehaviour(events=events)

    def test_invalid_key_class_in_event(self) -> None:
        with pytest.raises(ValidationError):
            KeyBehaviour(events=[["rawkey", 100.0, 160.0]])

    def test_malformed_event_rejected(self) -> None:
        with pytest.raises(ValidationError):
            KeyBehaviour(events=[["letter", 100.0]])  # only 2 elements


# ---------------------------------------------------------------------------
# TouchBehaviour
# ---------------------------------------------------------------------------


class TestTouchBehaviour:
    def test_valid_gesture(self) -> None:
        tb = TouchBehaviour(
            gestures=[
                TouchGesture(
                    type="swipe",
                    points=[[0.0, 0.0, 0.0], [10.0, 5.0, 50.0]],
                )
            ]
        )
        assert len(tb.gestures) == 1

    def test_too_many_gestures_rejected(self) -> None:
        gestures = [TouchGesture(type="tap", points=[]) for _ in range(21)]
        with pytest.raises(ValidationError):
            TouchBehaviour(gestures=gestures)

    def test_invalid_gesture_type(self) -> None:
        with pytest.raises(ValidationError):
            TouchGesture(type="pinch", points=[])  # type: ignore[arg-type]

    def test_too_many_gesture_points_rejected(self) -> None:
        points = [[float(i), float(i), float(i)] for i in range(101)]
        with pytest.raises(ValidationError):
            TouchGesture(type="drag", points=points)


# ---------------------------------------------------------------------------
# TimingSignals
# ---------------------------------------------------------------------------


class TestTimingSignals:
    def test_valid_timing(self) -> None:
        ts = TimingSignals(
            ms_since_load=8450.0,
            ms_to_first_interaction=1320.0,
            ms_since_nonce=7900.0,
            scroll_events=4,
            focus_changes=2,
        )
        assert ts.ms_since_load == 8450.0

    def test_negative_ms_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimingSignals(ms_since_load=-1.0)

    def test_excessive_ms_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TimingSignals(ms_since_load=3_700_000.0)  # > 1 hour


# ---------------------------------------------------------------------------
# BehaviourPayload
# ---------------------------------------------------------------------------


class TestBehaviourPayload:
    def test_empty_payload(self) -> None:
        bp = BehaviourPayload()
        assert bp.mouse is None
        assert bp.keys is None

    def test_full_payload(self) -> None:
        bp = BehaviourPayload(
            mouse=MouseBehaviour(points=[[0.0, 0.0, 0.0]]),
            keys=KeyBehaviour(events=[["letter", 0.0, 50.0]]),
            timing=TimingSignals(ms_since_load=5000.0),
            device_class="desktop",
        )
        assert bp.device_class == "desktop"

    def test_invalid_device_class(self) -> None:
        with pytest.raises(ValidationError):
            BehaviourPayload(device_class="smartwatch")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AssessRequest
# ---------------------------------------------------------------------------


class TestAssessRequest:
    def _make(self, **kwargs: object) -> AssessRequest:
        defaults: dict[str, object] = {
            "nonce": "abc123",
            "action": "otp_request",
        }
        defaults.update(kwargs)
        return AssessRequest(**defaults)  # type: ignore[arg-type]

    def test_minimal_valid_request(self) -> None:
        req = self._make()
        assert req.nonce == "abc123"
        assert req.schema_version == 1

    def test_empty_nonce_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._make(nonce="")

    def test_empty_action_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._make(action="")

    def test_nonce_too_long(self) -> None:
        with pytest.raises(ValidationError):
            self._make(nonce="x" * 300)

    def test_full_payload_accepted(self) -> None:
        req = self._make(
            env=EnvSignals(webdriver=False, ua_family="chrome"),
            behaviour=BehaviourPayload(
                mouse=MouseBehaviour(points=[[0.0, 0.0, 0.0]]),
                keys=KeyBehaviour(events=[["letter", 0.0, 50.0]]),
                device_class="desktop",
            ),
            client_ts=1_760_000_000_000.0,
        )
        assert req.behaviour is not None
        assert req.env is not None

    def test_negative_client_ts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._make(client_ts=-1.0)


# ---------------------------------------------------------------------------
# AssessResponse
# ---------------------------------------------------------------------------


class TestAssessResponse:
    def test_allow_response(self) -> None:
        r = AssessResponse(
            decision="allow",
            band="low",
            token="eyJ...",
            challenge=None,
            request_id="uuid-1",
        )
        assert r.token is not None

    def test_challenge_response(self) -> None:
        ch = ChallengeInfo(id="cid", type="press_hold", hold_ms=1100, expires_in=60)
        r = AssessResponse(
            decision="challenge",
            band="medium",
            token=None,
            challenge=ch,
            request_id="uuid-2",
        )
        assert r.challenge is not None

    def test_deny_response(self) -> None:
        r = AssessResponse(
            decision="deny",
            band="high",
            token=None,
            challenge=None,
            request_id="uuid-3",
        )
        assert r.decision == "deny"

    def test_allow_requires_token(self) -> None:
        with pytest.raises(ValidationError):
            AssessResponse(
                decision="allow",
                band="low",
                token=None,
                challenge=None,
                request_id="uuid-4",
            )

    def test_challenge_requires_challenge_object(self) -> None:
        with pytest.raises(ValidationError):
            AssessResponse(
                decision="challenge",
                band="medium",
                token=None,
                challenge=None,
                request_id="uuid-5",
            )

    def test_non_challenge_must_not_have_challenge_object(self) -> None:
        ch = ChallengeInfo(id="cid", type="press_hold", hold_ms=1100, expires_in=60)
        with pytest.raises(ValidationError):
            AssessResponse(
                decision="allow",
                band="low",
                token="eyJ...",
                challenge=ch,
                request_id="uuid-6",
            )

    def test_invalid_decision_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssessResponse(
                decision="maybe",  # type: ignore[arg-type]
                band="low",
                token="eyJ...",
                challenge=None,
                request_id="uuid-7",
            )


# ---------------------------------------------------------------------------
# ChallengeAssessRequest
# ---------------------------------------------------------------------------


class TestChallengeAssessRequest:
    def test_valid(self) -> None:
        r = ChallengeAssessRequest(
            nonce="n1",
            challenge_id="cid",
            action="otp_request",
            hold_start_ms=1000.0,
            hold_end_ms=2200.0,
        )
        assert r.challenge_id == "cid"

    def test_empty_challenge_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChallengeAssessRequest(nonce="n1", challenge_id="", action="otp_request")


# ---------------------------------------------------------------------------
# TokenVerifyRequest / Response
# ---------------------------------------------------------------------------


class TestTokenVerify:
    def test_valid_request(self) -> None:
        r = TokenVerifyRequest(token="eyJ...", expected_action="otp_request")
        assert r.expected_action == "otp_request"

    def test_empty_token_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TokenVerifyRequest(token="")

    def test_valid_response_valid(self) -> None:
        r = TokenVerifyResponse(valid=True, band="low", action="otp_request")
        assert r.valid

    def test_valid_response_invalid(self) -> None:
        r = TokenVerifyResponse(valid=False, reason="expired")
        assert not r.valid
        assert r.reason == "expired"


# ---------------------------------------------------------------------------
# NonceResponse
# ---------------------------------------------------------------------------


class TestNonceResponse:
    def test_valid(self) -> None:
        r = NonceResponse(nonce="abc123", expires_in=300)
        assert r.expires_in == 300

    def test_zero_expires_in_rejected(self) -> None:
        with pytest.raises(ValidationError):
            NonceResponse(nonce="abc", expires_in=0)


# ---------------------------------------------------------------------------
# HealthResponse
# ---------------------------------------------------------------------------


class TestHealthResponse:
    def test_ok(self) -> None:
        h = HealthResponse(
            status="ok",
            model_versions=ModelVersions(mouse="lgbm-1.0.0"),
            store_backend="memory",
            db_ok=True,
        )
        assert h.status == "ok"

    def test_degraded(self) -> None:
        h = HealthResponse(status="degraded", store_backend="redis", db_ok=False)
        assert h.status == "degraded"


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------


class TestErrorResponse:
    def test_valid(self) -> None:
        e = ErrorResponse(
            error=ErrorDetail(
                code="invalid_nonce",
                message="The nonce has already been used.",
                request_id="uuid-99",
            )
        )
        assert e.error.code == "invalid_nonce"

    def test_code_too_long(self) -> None:
        with pytest.raises(ValidationError):
            ErrorDetail(code="x" * 200, message="ok")


# ---------------------------------------------------------------------------
# Serialisation round-trips
# ---------------------------------------------------------------------------


class TestSerialisation:
    """All models must serialise and round-trip through JSON cleanly."""

    def test_assess_request_round_trip(self) -> None:
        req = AssessRequest(
            nonce="n",
            action="login",
            env=EnvSignals(webdriver=False),
            behaviour=BehaviourPayload(device_class="desktop"),
        )
        data = req.model_dump(mode="json")
        req2 = AssessRequest.model_validate(data)
        assert req2.nonce == req.nonce

    def test_assess_response_round_trip(self) -> None:
        resp = AssessResponse(
            decision="allow",
            band="low",
            token="eyJ...",
            request_id="r1",
        )
        data = resp.model_dump(mode="json")
        resp2 = AssessResponse.model_validate(data)
        assert resp2.decision == "allow"

    def test_env_signals_round_trip(self) -> None:
        env = EnvSignals(ua_family="firefox", webdriver=False, plugins_count=3)
        data = env.model_dump(mode="json")
        env2 = EnvSignals.model_validate(data)
        assert env2.ua_family == "firefox"

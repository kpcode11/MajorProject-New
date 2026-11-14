"""Comprehensive API, security, fail-safe, and logging tests (P5-09..P5-13)."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi import FastAPI

from app.config import Settings, load_rule_config, load_settings
from app.db import DatabaseManager
from app.main import app as default_app
from app.main import create_app, format_safe_log_record
from app.schemas import EnvSignals
from app.scoring import ModelScorer
from app.store import InMemoryStore, Store
from app.tokens import issue_token

BACKEND_ROOT = Path(__file__).resolve().parents[1]

HUMAN_MOUSE_POINTS: list[list[float]] = [
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


def _make_bot_mouse_points() -> list[list[float]]:
    pts: list[list[float]] = []
    t = 0.0
    for step in range(1, 46):
        u = step / 45.0
        pts.append([round(120.0 + u * 660.0, 2), round(150.0 + u * 370.0, 2), t])
        t += 16.0
    return pts


def _make_human_key_events() -> list[list[object]]:
    rng = np.random.default_rng(7)
    events: list[list[object]] = []
    t = 100.0
    for i in range(30):
        dwell = float(rng.lognormal(4.55, 0.32))
        key_cls = "backspace" if i % 9 == 4 else "letter"
        events.append([key_cls, round(t, 1), round(t + dwell, 1)])
        flight = -15.0 if i % 5 == 0 else float(rng.lognormal(4.6, 0.55))
        t = max(t + 5.0, t + dwell + flight)
    return events


def _make_bot_key_events() -> list[list[object]]:
    return [["letter", i * 210.0, i * 210.0 + 90.0] for i in range(30)]


def _clean_desktop_env() -> EnvSignals:
    return EnvSignals(
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
    )


class _BrokenStore(Store):
    """Fake store that simulates Redis/Store unavailability (P5-11 / P5-13)."""

    def get(self, key: str) -> str | None:
        raise ConnectionError("Simulated Redis outage")

    def set(self, key: str, value: str, *, ttl: int | None = None) -> None:
        raise ConnectionError("Simulated Redis outage")

    def delete(self, key: str) -> None:
        raise ConnectionError("Simulated Redis outage")

    def get_and_delete(self, key: str) -> str | None:
        raise ConnectionError("Simulated Redis outage")

    def increment(self, key: str, *, ttl: int | None = None) -> int:
        raise ConnectionError("Simulated Redis outage")

    def sliding_window_count(self, key: str, window_seconds: int) -> int:
        raise ConnectionError("Simulated Redis outage")


class _AsgiResponse:
    """In-process ASGI HTTP response wrapper."""

    def __init__(self, status_code: int, headers: dict[str, str], body: bytes) -> None:
        self.status_code = status_code
        self.headers = headers
        self.content = body

    def json(self) -> Any:
        return json.loads(self.content.decode("utf-8"))


class _AsgiTestClient:
    """Socket-free in-process ASGI test client for FastAPI."""

    def __init__(
        self,
        app: FastAPI,
        *,
        ip: str = "198.51.100.12",
        ua: str = "Mozilla/5.0 Chrome/130.0",
    ) -> None:
        self.app = app
        self.ip = ip
        self.ua = ua

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> _AsgiResponse:
        raw_body = b""
        req_headers: dict[str, str] = {"user-agent": self.ua, "host": "testserver"}
        if headers:
            for k, v in headers.items():
                req_headers[k.lower()] = v
        if json_body is not None:
            raw_body = json.dumps(json_body).encode("utf-8")
            req_headers.setdefault("content-type", "application/json")
        elif content is not None:
            raw_body = content
        if raw_body:
            req_headers.setdefault("content-length", str(len(raw_body)))

        clean_path, _, query_str = path.partition("?")
        asgi_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in req_headers.items()]
        scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": clean_path,
            "raw_path": clean_path.encode("ascii"),
            "query_string": query_str.encode("ascii"),
            "headers": asgi_headers,
            "client": (self.ip, 54321),
            "server": ("testserver", 80),
        }

        sent_messages: list[dict[str, Any]] = []
        body_consumed = False

        async def receive() -> dict[str, Any]:
            nonlocal body_consumed
            if not body_consumed:
                body_consumed = True
                return {"type": "http.request", "body": raw_body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            sent_messages.append(message)

        coro = self.app(scope, receive, send)
        try:
            coro.send(None)
        except StopIteration:
            pass

        status_code = 500
        resp_headers: dict[str, str] = {}
        body_chunks: list[bytes] = []
        for msg in sent_messages:
            if msg["type"] == "http.response.start":
                status_code = int(msg["status"])
                for hk, hv in msg.get("headers", []):
                    k_str = hk.decode("latin-1")
                    v_str = hv.decode("latin-1")
                    resp_headers[k_str] = v_str
                    # Also expose Title-Case key for convenience (e.g. Retry-After)
                    resp_headers["-".join(p.capitalize() for p in k_str.split("-"))] = v_str
            elif msg["type"] == "http.response.body":
                body_chunks.append(msg.get("body", b""))

        return _AsgiResponse(status_code, resp_headers, b"".join(body_chunks))

    def get(self, path: str, *, headers: dict[str, str] | None = None) -> _AsgiResponse:
        return self.request("GET", path, headers=headers)

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> _AsgiResponse:
        return self.request("POST", path, json_body=json, content=content, headers=headers)


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        database_url=f"sqlite:///{tmp_path / 'api_test.db'}",
        jwt_secret="api-test-secret-key-at-least-32-bytes-long-12345",
        rate_limit_nonce_per_min=20,
        rate_limit_assess_per_min=15,
        max_body_bytes=65536,
    )


@pytest.fixture
def test_app(test_settings: Settings) -> FastAPI:
    store = InMemoryStore()
    db = DatabaseManager(test_settings.database_url)
    app = create_app(
        settings=test_settings,
        store=store,
        scorer=default_app.state.scorer,
        db=db,
    )
    return app


def _client(
    app: FastAPI,
    *,
    ip: str = "198.51.100.12",
    ua: str = "Mozilla/5.0 Chrome/130.0",
) -> _AsgiTestClient:
    return _AsgiTestClient(app, ip=ip, ua=ua)


# ---------------------------------------------------------------------------
# 1. Health & Nonce single-use / context binding / replay rejection
# ---------------------------------------------------------------------------


def test_health_reports_loaded_model_versions(test_app: FastAPI) -> None:
    client = _client(test_app)
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db_ok"] is True
    assert data["store_backend"] == "memory"
    assert data["model_versions"]["mouse"] == "lightgbm-v1"
    assert data["model_versions"]["keyboard"] == "logistic_regression-v1"
    assert data["model_versions"]["fusion"] == "v1"


def test_nonce_single_use_and_replayed_assess_rejected(test_app: FastAPI) -> None:
    client = _client(test_app)
    nonce_resp = client.get("/v1/nonce")
    assert nonce_resp.status_code == 200
    nonce = nonce_resp.json()["nonce"]

    body = {
        "nonce": nonce,
        "action": "page_view",
        "env": _clean_desktop_env().model_dump(exclude_none=True),
        "behaviour": {
            "mouse": {"points": HUMAN_MOUSE_POINTS},
            "keys": {"events": _make_human_key_events()},
        },
    }
    first = client.post("/v1/assess", json=body)
    assert first.status_code == 200
    assert first.json()["decision"] == "allow"

    # Replaying the exact same assess payload with the consumed nonce is rejected (401)
    replay = client.post("/v1/assess", json=body)
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "invalid_or_expired_nonce"


def test_nonce_context_binding_rejects_different_user_agent_or_subnet(
    test_app: FastAPI,
) -> None:
    client1 = _client(test_app, ip="198.51.100.10", ua="Mozilla/5.0 Chrome/130")
    nonce = client1.get("/v1/nonce").json()["nonce"]

    # Different /24 subnet attempting to use the stolen nonce is rejected
    client2 = _client(test_app, ip="203.0.113.99", ua="Mozilla/5.0 Chrome/130")
    resp = client2.post(
        "/v1/assess",
        json={"nonce": nonce, "action": "login"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "nonce_context_mismatch"


# ---------------------------------------------------------------------------
# 2. Scoring fixture bands & raw score non-exposure
# ---------------------------------------------------------------------------


def test_clean_human_fixture_yields_low_band_and_never_exposes_raw_score(
    test_app: FastAPI,
) -> None:
    client = _client(test_app)
    nonce = client.get("/v1/nonce").json()["nonce"]
    payload = {
        "nonce": nonce,
        "action": "login",
        "env": _clean_desktop_env().model_dump(exclude_none=True),
        "behaviour": {
            "mouse": {"points": HUMAN_MOUSE_POINTS},
            "keys": {"events": _make_human_key_events()},
            "device_class": "desktop",
        },
    }
    resp = client.post("/v1/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["band"] == "low"
    assert data["decision"] == "allow"
    assert data["token"] is not None
    assert data["challenge"] is None
    assert data["degraded"] is False
    assert "score" not in data


def test_bot_fixture_yields_high_band_and_deny(test_app: FastAPI) -> None:
    client = _client(test_app)
    nonce = client.get("/v1/nonce").json()["nonce"]
    payload = {
        "nonce": nonce,
        "action": "otp_request",
        "env": {
            "ua_family": "Chrome",
            "ua_os": "Windows",
            "platform": "Linux x86_64",
            "webdriver": True,
            "plugins_count": 0,
        },
        "behaviour": {
            "mouse": {"points": _make_bot_mouse_points()},
            "keys": {"events": _make_bot_key_events()},
            "device_class": "desktop",
        },
    }
    resp = client.post("/v1/assess", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["band"] == "high"
    assert data["decision"] == "deny"
    assert data["token"] is None
    assert data["challenge"] is None
    assert "score" not in data


# ---------------------------------------------------------------------------
# 3. Step-up challenge flow & protected route token verification (P5-09, P5-10)
# ---------------------------------------------------------------------------


def test_challenge_step_up_flow_and_protected_route_access(
    test_app: FastAPI,
) -> None:
    client = _client(test_app)
    nonce1 = client.get("/v1/nonce").json()["nonce"]
    assess_resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce1,
            "action": "otp_request",
            "env": {"webdriver": True},
            "behaviour": {
                "keys": {"events": _make_human_key_events()},
            },
        },
    )
    assert assess_resp.status_code == 200
    assess_data = assess_resp.json()
    assert assess_data["decision"] == "challenge"
    assert assess_data["token"] is None
    chal = assess_data["challenge"]
    assert chal is not None
    assert chal["type"] == "press_hold"
    hold_ms = float(chal["hold_ms"])

    # Complete the challenge with valid hold duration
    nonce2 = client.get("/v1/nonce").json()["nonce"]
    chal_resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce2,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 1000.0,
            "hold_end_ms": 1000.0 + hold_ms + 50.0,
        },
    )
    assert chal_resp.status_code == 200
    chal_data = chal_resp.json()
    assert chal_data["decision"] == "allow"
    token = chal_data["token"]
    assert token is not None

    # Use the issued token on the protected route (/portal-api/otp/request)
    ok_portal = client.post(
        "/portal-api/otp/request",
        headers={"X-Human-Token": token},
    )
    assert ok_portal.status_code == 200
    assert ok_portal.json()["status"] == "otp_sent"

    # Reusing the single-use JTI token is rejected (401)
    replay_portal = client.post(
        "/portal-api/otp/request",
        headers={"X-Human-Token": token},
    )
    assert replay_portal.status_code == 401
    assert replay_portal.json()["error"]["code"] == "token_replayed_or_revoked"


def test_challenge_rescoring_rejects_untrusted_or_bot_challenge_behaviour(
    test_app: FastAPI,
) -> None:
    """Verify P7-07: POST /v1/assess/challenge re-scores original session + challenge features."""
    client = _client(test_app)
    nonce1 = client.get("/v1/nonce").json()["nonce"]
    assess_resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce1,
            "action": "otp_request",
            "env": {"webdriver": True},
            "behaviour": {
                "keys": {"events": _make_human_key_events()},
            },
        },
    )
    assert assess_resp.status_code == 200
    chal = assess_resp.json()["challenge"]
    assert chal is not None
    assert 800 <= chal["hold_ms"] <= 1500
    hold_ms = float(chal["hold_ms"])

    # Even with valid hold duration, untrusted synthetic challenge events (R11) cause deny
    nonce2 = client.get("/v1/nonce").json()["nonce"]
    chal_resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce2,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 500.0,
            "hold_end_ms": 500.0 + hold_ms + 40.0,
            "behaviour": {
                "mouse": {"points": _make_bot_mouse_points(), "untrusted_count": 3},
            },
        },
    )
    assert chal_resp.status_code == 200
    chal_data = chal_resp.json()
    assert chal_data["decision"] == "deny"
    assert chal_data["band"] == "high"
    assert chal_data["token"] is None


def test_challenge_single_use_and_endpoint_rate_limiting(
    test_settings: Settings,
) -> None:
    """Verify P7-08: single-use/short-lived challenge IDs and challenge rate limits."""
    cfg = dataclasses.replace(
        test_settings,
        rate_limit_challenge_per_min=5,
        rate_limit_challenge_session_per_min=2,
        challenge_ttl_seconds=45,
    )
    store = InMemoryStore()
    db = DatabaseManager(cfg.database_url)
    app = create_app(
        settings=cfg,
        store=store,
        scorer=default_app.state.scorer,
        db=db,
    )
    client = _client(app)

    nonce1 = client.get("/v1/nonce").json()["nonce"]
    assess_resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce1,
            "action": "otp_request",
            "env": {"webdriver": True},
            "behaviour": {"keys": {"events": _make_human_key_events()}},
        },
    )
    assert assess_resp.status_code == 200
    chal = assess_resp.json()["challenge"]
    assert chal is not None
    assert chal["expires_in"] == 45
    hold_ms = float(chal["hold_ms"])

    # 1. First challenge submission consumes challenge_id
    nonce2 = client.get("/v1/nonce").json()["nonce"]
    first_chal = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce2,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 100.0 + hold_ms + 30.0,
        },
    )
    assert first_chal.status_code == 200
    assert first_chal.json()["decision"] == "allow"

    # 2. Replaying the same challenge_id with a fresh nonce is rejected (401 single-use)
    nonce3 = client.get("/v1/nonce").json()["nonce"]
    replay_chal = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce3,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 100.0 + hold_ms + 30.0,
        },
    )
    assert replay_chal.status_code == 401
    assert replay_chal.json()["error"]["code"] == "invalid_or_expired_challenge"

    # 3. Third challenge attempt in the same session exceeds session limit=2 -> 429
    nonce4 = client.get("/v1/nonce").json()["nonce"]
    rl_chal = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce4,
            "challenge_id": "any_id",
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 1200.0,
        },
    )
    assert rl_chal.status_code == 429
    assert rl_chal.json()["error"]["code"] == "rate_limit_exceeded"
    assert rl_chal.headers.get("Retry-After") is not None


def test_token_verify_endpoint_and_wrong_action_rejection(
    test_app: FastAPI, test_settings: Settings
) -> None:
    store: Store = test_app.state.store
    tok = issue_token(store, test_settings, action="centre_search", band="low")
    client = _client(test_app)

    bad_act = client.post(
        "/v1/token/verify",
        json={"token": tok, "expected_action": "otp_request"},
    )
    assert bad_act.status_code == 200
    assert bad_act.json()["valid"] is False
    assert bad_act.json()["reason"] == "action_mismatch"

    ok = client.post(
        "/v1/token/verify",
        json={"token": tok, "expected_action": "centre_search"},
    )
    assert ok.status_code == 200
    assert ok.json()["valid"] is True
    assert ok.json()["band"] == "low"

    replay = client.post(
        "/v1/token/verify",
        json={"token": tok, "expected_action": "centre_search"},
    )
    assert replay.status_code == 200
    assert replay.json()["valid"] is False
    assert replay.json()["reason"] == "token_replayed_or_revoked"


# ---------------------------------------------------------------------------
# 4. Oversize / malformed payload & rate limits (P5-13)
# ---------------------------------------------------------------------------


def test_oversize_and_malformed_payloads_rejected_with_4xx(
    test_app: FastAPI,
) -> None:
    client = _client(test_app)
    huge_body = b'{"nonce":"x","action":"login","padding":"' + (b"A" * 70_000) + b'"}'
    oversize = client.post(
        "/v1/assess",
        content=huge_body,
        headers={"Content-Type": "application/json"},
    )
    assert oversize.status_code == 413
    assert oversize.json()["error"]["code"] == "payload_too_large"

    too_many_pts = [[float(i), float(i), float(i * 10)] for i in range(605)]
    malformed = client.post(
        "/v1/assess",
        json={
            "nonce": "valid-len-nonce",
            "action": "login",
            "behaviour": {"mouse": {"points": too_many_pts}},
        },
    )
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "validation_error"


def test_rate_limiting_triggers_429(test_settings: Settings) -> None:
    strict_settings = dataclasses.replace(
        test_settings,
        rate_limit_nonce_per_min=3,
    )
    app = create_app(
        settings=strict_settings,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
    )
    client = _client(app, ip="192.0.2.55")
    for _ in range(3):
        r = client.get("/v1/nonce")
        assert r.status_code == 200
    blocked = client.get("/v1/nonce")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in blocked.headers


# ---------------------------------------------------------------------------
# 5. Fail-safe behaviour when Redis/Store or Model is unavailable (P5-11, P5-13)
# ---------------------------------------------------------------------------


def test_fail_safe_when_store_is_unavailable(test_settings: Settings) -> None:
    app = create_app(
        settings=test_settings,
        store=_BrokenStore(),
        scorer=default_app.state.scorer,
    )
    client = _client(app)
    high_resp = client.post(
        "/v1/assess",
        json={"nonce": "any-nonce", "action": "otp_request"},
    )
    assert high_resp.status_code == 200
    high_data = high_resp.json()
    assert high_data["decision"] == "deny"
    assert high_data["band"] == "high"
    assert high_data["degraded"] is True

    low_resp = client.post(
        "/v1/assess",
        json={"nonce": "any-nonce", "action": "page_view"},
    )
    assert low_resp.status_code == 200
    low_data = low_resp.json()
    assert low_data["decision"] == "allow"
    assert low_data["band"] == "low"
    assert low_data["degraded"] is True
    assert low_data["token"] is not None


def test_fail_safe_when_models_are_unavailable(test_settings: Settings) -> None:
    store = InMemoryStore()
    rule_cfg = load_rule_config(test_settings.rules_config_file)
    rules_only_scorer = ModelScorer(
        mouse_model=None,
        keyboard_model=None,
        rule_config=rule_cfg,
    )
    app = create_app(settings=test_settings, store=store, scorer=rules_only_scorer)
    client = _client(app)
    nonce = client.get("/v1/nonce").json()["nonce"]
    resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce,
            "action": "login",
            "env": _clean_desktop_env().model_dump(exclude_none=True),
            "behaviour": {"mouse": {"points": HUMAN_MOUSE_POINTS}},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["degraded"] is True
    assert data["decision"] == "allow"
    assert data["band"] == "low"


# ---------------------------------------------------------------------------
# 6. Privacy-safe structured logging (P5-12)
# ---------------------------------------------------------------------------


def test_structured_logging_coarsens_ip_and_strips_payloads() -> None:
    rec = format_safe_log_record(
        "assessment_completed",
        request_id="req-999",
        client_ip="203.0.113.195",
        action="otp_request",
        decision="allow",
        band="low",
        points=[[100.0, 200.0, 10.0]],
        events=[["letter", 0.0, 50.0]],
        nonce="secret-nonce",
        token="secret-jwt",
        user_agent="Mozilla/5.0",
    )
    assert rec["request_id"] == "req-999"
    assert rec["ip_bucket"] == "203.0.113.0/24"
    assert "203.0.113.195" not in str(rec)
    for forbidden in ("points", "events", "nonce", "token", "user_agent", "client_ip"):
        assert forbidden not in rec

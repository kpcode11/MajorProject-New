"""Dedicated step-up challenge test suite (P7-10):
success, timeout, replay, too-fast completion, and wrong ID / context mismatch.
"""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from test_api import _AsgiTestClient, _make_human_key_events

from app.config import Settings, load_settings
from app.db import DatabaseManager
from app.main import app as default_app
from app.main import create_app
from app.store import InMemoryStore


@pytest.fixture
def challenge_settings(tmp_path: Path) -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        database_url=f"sqlite:///{tmp_path / 'challenge_test.db'}",
        jwt_secret="challenge-test-secret-key-at-least-32-bytes-long",
        rate_limit_nonce_per_min=50,
        rate_limit_assess_per_min=50,
        rate_limit_challenge_per_min=30,
        rate_limit_challenge_session_per_min=20,
        challenge_ttl_seconds=60,
    )


@pytest.fixture
def challenge_app(challenge_settings: Settings) -> FastAPI:
    store = InMemoryStore()
    db = DatabaseManager(challenge_settings.database_url)
    return create_app(
        settings=challenge_settings,
        store=store,
        scorer=default_app.state.scorer,
        db=db,
    )


def _issue_challenge(client: _AsgiTestClient, action: str = "otp_request") -> dict[str, object]:
    nonce = client.get("/v1/nonce").json()["nonce"]
    resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce,
            "action": action,
            "env": {"webdriver": True},
            "behaviour": {"keys": {"events": _make_human_key_events()}},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "challenge"
    assert data["challenge"] is not None
    return dict(data["challenge"])


def test_challenge_success(challenge_app: FastAPI) -> None:
    """1. Challenge success: valid hold duration issues single-use human token."""
    client = _AsgiTestClient(challenge_app)
    chal = _issue_challenge(client)
    hold_ms = float(str(chal["hold_ms"]))

    nonce = client.get("/v1/nonce").json()["nonce"]
    resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 200.0,
            "hold_end_ms": 200.0 + hold_ms + 50.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "allow"
    assert body["band"] == "low"
    assert body["token"] is not None


def test_challenge_timeout_expired(challenge_settings: Settings) -> None:
    """2. Challenge timeout: expired challenge_id is rejected with 401."""
    short_ttl_settings = dataclasses.replace(challenge_settings, challenge_ttl_seconds=1)
    store = InMemoryStore()
    db = DatabaseManager(short_ttl_settings.database_url)
    app = create_app(
        settings=short_ttl_settings,
        store=store,
        scorer=default_app.state.scorer,
        db=db,
    )
    client = _AsgiTestClient(app)
    chal = _issue_challenge(client)
    assert chal["expires_in"] == 1
    hold_ms = float(str(chal["hold_ms"]))

    # Wait for the 1-second challenge TTL to expire
    time.sleep(1.1)

    nonce = client.get("/v1/nonce").json()["nonce"]
    resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 100.0 + hold_ms + 50.0,
        },
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_or_expired_challenge"


def test_challenge_replay_rejected(challenge_app: FastAPI) -> None:
    """3. Challenge replay: reusing a consumed challenge_id (after pass or fail) is rejected."""
    client = _AsgiTestClient(challenge_app)
    chal = _issue_challenge(client)
    hold_ms = float(str(chal["hold_ms"]))

    # First submission succeeds
    nonce1 = client.get("/v1/nonce").json()["nonce"]
    first = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce1,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 100.0 + hold_ms + 40.0,
        },
    )
    assert first.status_code == 200
    assert first.json()["decision"] == "allow"

    # Second submission with the same challenge_id is rejected with 401
    nonce2 = client.get("/v1/nonce").json()["nonce"]
    replay = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce2,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 100.0 + hold_ms + 40.0,
        },
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "invalid_or_expired_challenge"


def test_challenge_too_fast_completion_denied(challenge_app: FastAPI) -> None:
    """4. Too-fast completion: hold shorter than required_hold_ms * 0.85 returns deny."""
    client = _AsgiTestClient(challenge_app)
    chal = _issue_challenge(client)

    # Hold for only 120 ms (well below 800-1500 ms target)
    nonce = client.get("/v1/nonce").json()["nonce"]
    resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 500.0,
            "hold_end_ms": 620.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "deny"
    assert body["band"] == "high"
    assert body["token"] is None

    # And the failed challenge_id cannot be replayed
    nonce2 = client.get("/v1/nonce").json()["nonce"]
    replay = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce2,
            "challenge_id": chal["id"],
            "action": "otp_request",
            "hold_start_ms": 500.0,
            "hold_end_ms": 2500.0,
        },
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "invalid_or_expired_challenge"


def test_challenge_wrong_id_and_mismatches_rejected(challenge_app: FastAPI) -> None:
    """5. Wrong ID, wrong caller context, and wrong action are rejected."""
    client = _AsgiTestClient(challenge_app)

    # Wrong/unknown challenge_id -> 401 invalid_or_expired_challenge
    nonce1 = client.get("/v1/nonce").json()["nonce"]
    wrong_id_resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce1,
            "challenge_id": "non_existent_challenge_id_xyz",
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 1500.0,
        },
    )
    assert wrong_id_resp.status_code == 401
    assert wrong_id_resp.json()["error"]["code"] == "invalid_or_expired_challenge"

    # Action mismatch -> 400 challenge_action_mismatch
    chal = _issue_challenge(client, action="otp_request")
    nonce2 = client.get("/v1/nonce").json()["nonce"]
    wrong_act_resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce2,
            "challenge_id": chal["id"],
            "action": "centre_search",
            "hold_start_ms": 100.0,
            "hold_end_ms": 1500.0,
        },
    )
    assert wrong_act_resp.status_code == 400
    assert wrong_act_resp.json()["error"]["code"] == "challenge_action_mismatch"

    # Context mismatch (different /24 IP subnet) -> 401 challenge_context_mismatch
    chal2 = _issue_challenge(client, action="otp_request")
    other_client = _AsgiTestClient(challenge_app, ip="203.0.113.77")
    other_nonce = other_client.get("/v1/nonce").json()["nonce"]
    wrong_ctx_resp = other_client.post(
        "/v1/assess/challenge",
        json={
            "nonce": other_nonce,
            "challenge_id": chal2["id"],
            "action": "otp_request",
            "hold_start_ms": 100.0,
            "hold_end_ms": 1500.0,
        },
    )
    assert wrong_ctx_resp.status_code == 401
    assert wrong_ctx_resp.json()["error"]["code"] == "challenge_context_mismatch"

"""Unit tests for the protected mock portal API routes under ``/portal-api/`` (P7-03)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from fastapi import FastAPI
from test_api import _AsgiTestClient

from app.config import Settings, load_settings
from app.db import DatabaseManager
from app.main import app as default_app
from app.main import create_app
from app.store import InMemoryStore, Store
from app.tokens import issue_token


@pytest.fixture
def portal_settings(tmp_path: Path) -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        database_url=f"sqlite:///{tmp_path / 'portal_api_test.db'}",
        jwt_secret="portal-api-test-secret-key-at-least-32-bytes-long",
    )


@pytest.fixture
def portal_app(portal_settings: Settings) -> FastAPI:
    store = InMemoryStore()
    db = DatabaseManager(portal_settings.database_url)
    return create_app(
        settings=portal_settings,
        store=store,
        scorer=default_app.state.scorer,
        db=db,
    )


def _client(app: FastAPI) -> _AsgiTestClient:
    return _AsgiTestClient(app)


def test_portal_otp_request_requires_valid_single_use_token(
    portal_app: FastAPI, portal_settings: Settings
) -> None:
    client = _client(portal_app)
    store: Store = portal_app.state.store

    # 1. Missing token -> 401 missing_token
    no_tok = client.post("/portal-api/otp/request", json={"identifier_length": 12})
    assert no_tok.status_code == 401
    assert no_tok.json()["error"]["code"] == "missing_token"

    # 2. Wrong action token -> 401 action_mismatch
    wrong_tok = issue_token(store, portal_settings, action="centre_search", band="low")
    bad_act = client.post(
        "/portal-api/otp/request",
        json={"identifier_length": 12},
        headers={"X-Human-Token": wrong_tok},
    )
    assert bad_act.status_code == 401
    assert bad_act.json()["error"]["code"] == "action_mismatch"

    # 3. Valid otp_request token -> 200 otp_sent
    valid_tok = issue_token(store, portal_settings, action="otp_request", band="low")
    ok = client.post(
        "/portal-api/otp/request",
        json={"action": "otp_request", "identifier_length": 12},
        headers={"X-Human-Token": valid_tok},
    )
    assert ok.status_code == 200
    data = ok.json()
    assert data["status"] == "otp_sent"
    assert data["action"] == "otp_request"
    assert data["band"] == "low"
    assert data["identifier_length"] == 12

    # 4. Replaying the consumed token -> 401 token_replayed_or_revoked
    replay = client.post(
        "/portal-api/otp/request",
        json={"identifier_length": 12},
        headers={"X-Human-Token": valid_tok},
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "token_replayed_or_revoked"


def test_portal_details_update_requires_valid_token_and_forbids_extra_fields(
    portal_app: FastAPI, portal_settings: Settings
) -> None:
    client = _client(portal_app)
    store: Store = portal_app.state.store

    # Missing token -> 401
    assert client.post("/portal-api/details/update").status_code == 401

    # Valid details_update token via Authorization: Bearer
    tok = issue_token(store, portal_settings, action="details_update", band="low")
    ok = client.post(
        "/portal-api/details/update",
        json={
            "action": "details_update",
            "fields_updated": ["name", "address"],
            "city_code": "DELHI",
            "language_code": "HI",
            "confirmed": True,
        },
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert ok.status_code == 200
    data = ok.json()
    assert data["status"] == "details_updated"
    assert data["action"] == "details_update"
    assert data["fields_updated"] == ["name", "address"]
    assert data["city_code"] == "DELHI"

    # Extra PII key in request body is rejected with 422 validation_error
    tok2 = issue_token(store, portal_settings, action="details_update", band="low")
    extra_resp = client.post(
        "/portal-api/details/update",
        json={"action": "details_update", "raw_full_name": "ShouldBeRejected"},
        headers={"X-Human-Token": tok2},
    )
    assert extra_resp.status_code == 422
    assert extra_resp.json()["error"]["code"] == "validation_error"


def test_portal_centres_search_requires_valid_token_and_filters_by_service(
    portal_app: FastAPI, portal_settings: Settings
) -> None:
    client = _client(portal_app)
    store: Store = portal_app.state.store

    # Missing token -> 401
    assert client.post("/portal-api/centres/search").status_code == 401

    # All services
    tok_all = issue_token(store, portal_settings, action="centre_search", band="low")
    resp_all = client.post(
        "/portal-api/centres/search",
        json={"action": "centre_search", "service_type": "ALL", "query_length": 6},
        headers={"X-Human-Token": tok_all},
    )
    assert resp_all.status_code == 200
    centres_all = resp_all.json()["centres"]
    assert len(centres_all) == 3

    # Filter by BIOMETRIC_UPDATE
    tok_bio = issue_token(store, portal_settings, action="centre_search", band="low")
    resp_bio = client.post(
        "/portal-api/centres/search",
        json={
            "action": "centre_search",
            "service_type": "BIOMETRIC_UPDATE",
            "query_length": 9,
        },
        headers={"X-Human-Token": tok_bio},
    )
    assert resp_bio.status_code == 200
    centres_bio = resp_bio.json()["centres"]
    assert len(centres_bio) == 1
    assert centres_bio[0]["code"] == "DEMO-BLR-01"


def test_portal_stats_counts_accepted_and_rejected_calls(
    portal_app: FastAPI, portal_settings: Settings
) -> None:
    client = _client(portal_app)
    store: Store = portal_app.state.store

    # Initial stats are zero
    init_resp = client.get("/portal-api/stats")
    assert init_resp.status_code == 200
    assert init_resp.json() == {
        "accepted": 0,
        "rejected": 0,
        "total": 0,
        "by_action": {
            "otp_request": {"accepted": 0, "rejected": 0},
            "details_update": {"accepted": 0, "rejected": 0},
            "centre_search": {"accepted": 0, "rejected": 0},
        },
        "by_reason": {},
        "protection_mode": "passive",
    }

    # 1. Missing token on otp_request -> rejected (missing_token)
    assert client.post("/portal-api/otp/request").status_code == 401

    # 2. Valid token on otp_request -> accepted
    tok_otp = issue_token(store, portal_settings, action="otp_request", band="low")
    assert (
        client.post(
            "/portal-api/otp/request",
            headers={"X-Human-Token": tok_otp},
        ).status_code
        == 200
    )

    # 3. Replay consumed token on otp_request -> rejected (token_replayed_or_revoked)
    assert (
        client.post(
            "/portal-api/otp/request",
            headers={"X-Human-Token": tok_otp},
        ).status_code
        == 401
    )

    # 4. Wrong action token on details_update -> rejected (action_mismatch)
    tok_wrong = issue_token(store, portal_settings, action="centre_search", band="low")
    assert (
        client.post(
            "/portal-api/details/update",
            headers={"X-Human-Token": tok_wrong},
        ).status_code
        == 401
    )

    # 5. Valid token on centre_search -> accepted
    tok_search = issue_token(store, portal_settings, action="centre_search", band="low")
    assert (
        client.post(
            "/portal-api/centres/search",
            headers={"X-Human-Token": tok_search},
        ).status_code
        == 200
    )

    # 6. Extra field on details_update with valid token -> rejected (validation_error)
    tok_details = issue_token(store, portal_settings, action="details_update", band="low")
    assert (
        client.post(
            "/portal-api/details/update",
            json={"unexpected_field": "bad"},
            headers={"X-Human-Token": tok_details},
        ).status_code
        == 422
    )

    stats = client.get("/portal-api/stats").json()
    assert stats["accepted"] == 2
    assert stats["rejected"] == 4
    assert stats["total"] == 6
    assert stats["by_action"] == {
        "otp_request": {"accepted": 1, "rejected": 2},
        "details_update": {"accepted": 0, "rejected": 2},
        "centre_search": {"accepted": 1, "rejected": 0},
    }
    assert stats["by_reason"] == {
        "missing_token": 1,
        "token_replayed_or_revoked": 1,
        "action_mismatch": 1,
        "validation_error": 1,
    }
    assert stats["protection_mode"] == "passive"


def test_protection_mode_off_allows_unauthenticated_portal_calls(
    portal_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROTECTION_MODE", "off")
    env_settings = load_settings()
    assert env_settings.protection_mode == "off"

    off_settings = dataclasses.replace(portal_settings, protection_mode="off")
    store = InMemoryStore()
    db = DatabaseManager(off_settings.database_url)
    app = create_app(
        settings=off_settings,
        store=store,
        scorer=default_app.state.scorer,
        db=db,
    )
    client = _client(app)

    # All 3 portal endpoints succeed without X-Human-Token when protection_mode="off"
    otp_resp = client.post("/portal-api/otp/request", json={"identifier_length": 12})
    assert otp_resp.status_code == 200
    assert otp_resp.json()["status"] == "otp_sent"

    details_resp = client.post("/portal-api/details/update", json={"fields_updated": ["name"]})
    assert details_resp.status_code == 200
    assert details_resp.json()["status"] == "details_updated"

    search_resp = client.post("/portal-api/centres/search", json={"query_length": 6})
    assert search_resp.status_code == 200
    assert search_resp.json()["status"] == "ok"

    stats = client.get("/portal-api/stats").json()
    assert stats["protection_mode"] == "off"
    assert stats["accepted"] == 3
    assert stats["rejected"] == 0
    assert stats["total"] == 3

    # Invalid PROTECTION_MODE value raises ValueError
    monkeypatch.setenv("PROTECTION_MODE", "invalid_mode")
    with pytest.raises(ValueError, match="PROTECTION_MODE"):
        load_settings()

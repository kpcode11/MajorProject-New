"""End-to-end portal protection and simulator verification tests (P7-18).

Covers the Phase 7 E2E requirements and acceptance criteria:
1. Normal interaction path -> token issued -> OTP request accepted (200 OK).
2. Headless Playwright direct click/fill -> denied or challenged -> OTP rejected (401).
3. No token -> 401 Unauthorized across all protected ``/portal-api/*`` routes.
4. Keyboard-only scripted session (Tab navigation + typing + Enter, no mouse events) is
   never denied automatically and passes via the accessible keyboard challenge path.
5. With ``protection_mode="off"``, Tiers 1-4 succeed in submitting OTP requests; with
   ``protection_mode="passive"``, outcomes are recorded and reported honestly.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI
from test_api import _AsgiTestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.reference_human import (  # noqa: E402
    REFERENCE_HUMAN_MOUSE_POINTS,
    build_reference_human_env_signals,
    build_reference_human_key_events,
    run_reference_human_session,
)
from simulator.tier1_http import HttpGetFn, HttpPostFn, run_tier1_session  # noqa: E402
from simulator.tier2_playwright import run_tier2_session  # noqa: E402
from simulator.tier3_stealth import run_tier3_session  # noqa: E402
from simulator.tier4_humanlike import run_tier4_session  # noqa: E402

from app.config import Settings, load_settings  # noqa: E402
from app.db import DatabaseManager  # noqa: E402
from app.main import app as default_app  # noqa: E402
from app.main import create_app  # noqa: E402
from app.store import InMemoryStore  # noqa: E402


def _make_asgi_transports(
    app: FastAPI,
) -> tuple[_AsgiTestClient, HttpPostFn, HttpGetFn]:
    client = _AsgiTestClient(app)

    def post_fn(
        url: str,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> tuple[int, dict[str, Any]]:
        path = urlsplit(url).path or "/"
        resp = client.post(path, json=body, headers=headers)
        return resp.status_code, resp.json()

    def get_fn(url: str, headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        path = urlsplit(url).path or "/"
        resp = client.get(path, headers=headers)
        return resp.status_code, resp.json()

    return client, post_fn, get_fn


@pytest.fixture
def base_e2e_settings(tmp_path: Path) -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        database_url=f"sqlite:///{tmp_path / 'e2e_portal.db'}",
        jwt_secret="e2e-portal-test-secret-key-at-least-32-bytes-long",
        rate_limit_nonce_per_min=1000,
        rate_limit_assess_per_min=1000,
        rate_limit_challenge_per_min=1000,
        rate_limit_challenge_session_per_min=1000,
    )


def test_e2e_normal_interaction_path_issues_token_and_accepts_otp(
    base_e2e_settings: Settings,
) -> None:
    """Normal interaction path -> /v1/assess issues token -> /portal-api/otp/request returns 200."""
    cfg = dataclasses.replace(base_e2e_settings, protection_mode="passive")
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(cfg.database_url),
    )
    client = _AsgiTestClient(app)

    nonce_resp = client.get("/v1/nonce")
    assert nonce_resp.status_code == 200
    nonce = nonce_resp.json()["nonce"]

    assess_resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce,
            "action": "otp_request",
            "sdk_version": "1.0.0",
            "env": build_reference_human_env_signals(),
            "behaviour": {
                "mouse": {
                    "points": REFERENCE_HUMAN_MOUSE_POINTS,
                    "clicks": [],
                    "untrusted_count": 0,
                    "wheel_events": 1,
                },
                "keys": {
                    "events": build_reference_human_key_events(seed=7),
                    "paste_events": 0,
                    "autofill_suspected": False,
                    "untrusted_count": 0,
                },
                "timing": {
                    "ms_since_load": 3800.0,
                    "ms_to_first_interaction": 191.0,
                    "ms_since_nonce": 3500.0,
                    "scroll_events": 1,
                    "focus_changes": 2,
                },
                "device_class": "desktop",
            },
        },
    )
    assert assess_resp.status_code == 200
    assess_data = assess_resp.json()
    assert assess_data["decision"] == "allow"
    assert assess_data["band"] == "low"
    token = assess_data["token"]
    assert isinstance(token, str) and len(token) > 20

    otp_resp = client.post(
        "/portal-api/otp/request",
        json={"action": "otp_request", "identifier_length": 12},
        headers={"X-Human-Token": token},
    )
    assert otp_resp.status_code == 200
    assert otp_resp.json()["status"] == "otp_sent"

    stats = client.get("/portal-api/stats").json()
    assert stats["accepted"] == 1
    assert stats["rejected"] == 0


def test_e2e_headless_direct_click_is_denied_or_challenged(
    base_e2e_settings: Settings,
) -> None:
    """Headless direct click/fill (Tier 2) is denied or challenged and rejected at portal API."""
    cfg = dataclasses.replace(base_e2e_settings, protection_mode="passive")
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(cfg.database_url),
    )
    client, post_fn, get_fn = _make_asgi_transports(app)

    res = run_tier2_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        action="otp_request",
        post_fn=post_fn,
        get_fn=get_fn,
    )
    assert res.assess_decision in ("deny", "challenge")
    assert res.outcome in ("denied", "challenged")
    assert res.portal_status == 401

    stats = client.get("/portal-api/stats").json()
    assert stats["accepted"] == 0
    assert stats["rejected"] == 1


def test_e2e_no_token_returns_401(
    base_e2e_settings: Settings,
) -> None:
    """Requests to protected /portal-api/* endpoints without X-Human-Token return 401."""
    cfg = dataclasses.replace(base_e2e_settings, protection_mode="passive")
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(cfg.database_url),
    )
    client = _AsgiTestClient(app)

    r_otp = client.post(
        "/portal-api/otp/request",
        json={"action": "otp_request", "identifier_length": 12},
    )
    assert r_otp.status_code == 401

    r_details = client.post(
        "/portal-api/details/update",
        json={
            "action": "details_update",
            "fields_updated": ["name"],
            "city_code": "BENGALURU",
            "language_code": "EN",
            "confirmed": True,
        },
    )
    assert r_details.status_code == 401

    r_centres = client.post(
        "/portal-api/centres/search",
        json={"action": "centre_search", "service_type": "ALL", "query_length": 6},
    )
    assert r_centres.status_code == 401

    stats = client.get("/portal-api/stats").json()
    assert stats["accepted"] == 0
    assert stats["rejected"] == 3
    assert stats["by_reason"]["missing_token"] == 3


def test_e2e_keyboard_only_session_is_not_denied_and_passes_via_challenge_path(
    base_e2e_settings: Settings,
) -> None:
    """Keyboard-only session (Tab + Enter) is never auto-denied and passes step-up."""
    cfg = dataclasses.replace(base_e2e_settings, protection_mode="passive")
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(cfg.database_url),
    )
    client, post_fn, get_fn = _make_asgi_transports(app)

    res = run_reference_human_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        action="otp_request",
        mode="keyboard_only",
        post_fn=post_fn,
        get_fn=get_fn,
    )
    assert res.params["initial_decision"] in ("allow", "challenge")
    assert res.outcome == "allowed"
    assert res.portal_status == 200
    assert client.get("/portal-api/stats").json()["accepted"] == 1


def test_e2e_protection_mode_off_vs_passive_across_all_tiers(
    base_e2e_settings: Settings,
) -> None:
    """With protection off, Tiers 1-4 succeed; with passive, Tiers 1-3 are blocked."""
    off_cfg = dataclasses.replace(base_e2e_settings, protection_mode="off")
    off_app = create_app(
        settings=off_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(off_cfg.database_url),
    )
    off_client, off_post, off_get = _make_asgi_transports(off_app)

    for runner in (run_tier1_session, run_tier2_session, run_tier3_session, run_tier4_session):
        r = runner(
            "http://127.0.0.1:8000",
            protection_mode="off",
            action="otp_request",
            post_fn=off_post,
            get_fn=off_get,
        )
        assert r.outcome == "allowed"
        assert r.portal_status == 200

    assert off_client.get("/portal-api/stats").json()["accepted"] == 4

    pas_cfg = dataclasses.replace(base_e2e_settings, protection_mode="passive")
    pas_app = create_app(
        settings=pas_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(pas_cfg.database_url),
    )
    pas_client, pas_post, pas_get = _make_asgi_transports(pas_app)

    r1 = run_tier1_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        action="otp_request",
        post_fn=pas_post,
        get_fn=pas_get,
    )
    r2 = run_tier2_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        action="otp_request",
        post_fn=pas_post,
        get_fn=pas_get,
    )
    r3 = run_tier3_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        action="otp_request",
        post_fn=pas_post,
        get_fn=pas_get,
    )
    assert r1.outcome == "blocked-at-api"
    assert r2.outcome in ("denied", "challenged")
    assert r3.outcome in ("denied", "challenged")
    assert pas_client.get("/portal-api/stats").json()["rejected"] == 3

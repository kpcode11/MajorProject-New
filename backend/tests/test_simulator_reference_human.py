"""Unit tests for the scripted human-like reference run (P7-17)."""

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
    DEMO_SCRIPT_DISCLAIMER,
    run_reference_human_session,
)
from simulator.safety import SimulatorTargetError  # noqa: E402
from simulator.tier1_http import HttpGetFn, HttpPostFn  # noqa: E402

from app.config import load_settings  # noqa: E402
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
def passive_app(tmp_path: Path) -> FastAPI:
    base = load_settings()
    cfg = dataclasses.replace(
        base,
        protection_mode="passive",
        database_url=f"sqlite:///{tmp_path / 'sim_ref_human.db'}",
        jwt_secret="sim-ref-human-secret-key-at-least-32-bytes-long",
    )
    return create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(cfg.database_url),
    )


def test_reference_human_refuses_non_local_host() -> None:
    """run_reference_human_session must refuse non-allowlisted hosts."""
    with pytest.raises(SimulatorTargetError):
        run_reference_human_session("https://resident.uidai.gov.in")


def test_multimodal_reference_human_session_passes_passive_protection(
    passive_app: FastAPI,
) -> None:
    """Multimodal human reference session passes passive protection across all portal actions."""
    client, post_fn, get_fn = _make_asgi_transports(passive_app)

    for action in ("otp_request", "details_update", "centre_search"):
        res = run_reference_human_session(
            "http://127.0.0.1:8000",
            protection_mode="passive",
            action=action,
            mode="multimodal_desktop",
            post_fn=post_fn,
            get_fn=get_fn,
        )
        assert res.tier == "reference_human"
        assert res.outcome == "allowed"
        assert res.portal_status == 200
        assert res.assess_decision == "allow"
        assert res.assess_band == "low"
        assert res.params["demo_script_only"] is True
        assert res.params["not_a_validation_dataset"] is True
        assert res.params["disclaimer"] == DEMO_SCRIPT_DISCLAIMER

    stats = client.get("/portal-api/stats").json()
    assert stats["accepted"] == 3
    assert stats["rejected"] == 0


def test_keyboard_only_reference_session_is_not_denied_and_passes_portal(
    passive_app: FastAPI,
) -> None:
    """A keyboard-only scripted session (Tab + Enter) is never auto-denied and passes."""
    client, post_fn, get_fn = _make_asgi_transports(passive_app)

    res = run_reference_human_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        action="otp_request",
        mode="keyboard_only",
        post_fn=post_fn,
        get_fn=get_fn,
    )
    assert res.tier == "reference_human"
    assert res.params["initial_decision"] in ("allow", "challenge")
    assert res.outcome == "allowed"
    assert res.portal_status == 200
    assert res.assess_decision == "allow"

    stats = client.get("/portal-api/stats").json()
    assert stats["accepted"] == 1
    assert stats["rejected"] == 0

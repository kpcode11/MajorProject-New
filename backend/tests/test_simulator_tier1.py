"""Unit tests for Tier 1 plain-HTTP bot simulator (P7-12)."""

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

from simulator.safety import SimulatorTargetError  # noqa: E402
from simulator.tier1_http import HttpGetFn, HttpPostFn, run_tier1_session  # noqa: E402

from app.config import Settings, load_settings  # noqa: E402
from app.db import DatabaseManager  # noqa: E402
from app.main import app as default_app  # noqa: E402
from app.main import create_app  # noqa: E402
from app.store import InMemoryStore  # noqa: E402


def _make_asgi_transports(app: FastAPI) -> tuple[HttpPostFn, HttpGetFn]:
    client = _AsgiTestClient(app)

    def post_fn(
        url: str, body: dict[str, Any], headers: dict[str, str]
    ) -> tuple[int, dict[str, Any]]:
        path = urlsplit(url).path or "/"
        resp = client.post(path, json=body, headers=headers)
        return resp.status_code, resp.json()

    def get_fn(url: str, headers: dict[str, str]) -> tuple[int, dict[str, Any]]:
        path = urlsplit(url).path or "/"
        resp = client.get(path, headers=headers)
        return resp.status_code, resp.json()

    return post_fn, get_fn


@pytest.fixture
def base_sim_settings(tmp_path: Path) -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        database_url=f"sqlite:///{tmp_path / 'sim_tier1.db'}",
        jwt_secret="sim-tier1-test-secret-key-at-least-32-bytes-long",
    )


def test_tier1_refuses_non_local_host() -> None:
    with pytest.raises(SimulatorTargetError):
        run_tier1_session("https://example.com")


def test_tier1_succeeds_when_protection_is_off_and_is_blocked_when_passive(
    base_sim_settings: Settings,
) -> None:
    # 1. protection_mode = "off" -> Tier 1 plain HTTP POST succeeds ("allowed")
    off_cfg = dataclasses.replace(base_sim_settings, protection_mode="off")
    off_app = create_app(
        settings=off_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(off_cfg.database_url),
    )
    off_post, off_get = _make_asgi_transports(off_app)

    res_off = run_tier1_session(
        "http://127.0.0.1:8000",
        protection_mode="off",
        post_fn=off_post,
        get_fn=off_get,
    )
    assert res_off.tier == "tier1"
    assert res_off.outcome == "allowed"
    assert res_off.portal_status == 200
    assert res_off.to_dict()["outcome"] == "allowed"

    # 2. protection_mode = "passive" (direct POST) -> blocked at API (401)
    pas_cfg = dataclasses.replace(base_sim_settings, protection_mode="passive")
    pas_app = create_app(
        settings=pas_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(pas_cfg.database_url),
    )
    pas_post, pas_get = _make_asgi_transports(pas_app)

    res_direct = run_tier1_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        include_assess_attempt=False,
        post_fn=pas_post,
        get_fn=pas_get,
    )
    assert res_direct.outcome == "blocked-at-api"
    assert res_direct.portal_status == 401
    assert res_direct.assess_decision is None

    # 3. protection_mode = "passive" (with empty-telemetry /v1/assess attempt) -> challenged/denied
    res_assess = run_tier1_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        include_assess_attempt=True,
        post_fn=pas_post,
        get_fn=pas_get,
    )
    assert res_assess.portal_status == 401
    assert res_assess.assess_decision in ("challenge", "deny")
    assert res_assess.outcome in ("challenged", "denied")

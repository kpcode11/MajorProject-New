"""Unit tests for Tier 2 Playwright-default bot simulator (P7-13)."""

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
from simulator.tier1_http import HttpGetFn, HttpPostFn  # noqa: E402
from simulator.tier2_playwright import (  # noqa: E402
    drive_tier2_playwright_page,
    run_tier2_session,
)

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


class _FakePlaywrightPage:
    """Spy implementing ``PlaywrightPageLike`` to verify direct ``fill`` and ``click`` calls."""

    def __init__(
        self,
        *,
        dom_outcome: str | None = "rejected",
        stepup_visible: bool = False,
    ) -> None:
        self.visited_urls: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []
        self._dom_outcome = dom_outcome
        self._stepup_visible = stepup_visible

    def goto(self, url: str, **kwargs: Any) -> Any:
        self.visited_urls.append(url)
        return None

    def fill(self, selector: str, value: str, **kwargs: Any) -> None:
        self.fills.append((selector, value))

    def click(self, selector: str, **kwargs: Any) -> None:
        self.clicks.append(selector)

    def get_attribute(self, selector: str, name: str, **kwargs: Any) -> str | None:
        if name == "data-outcome":
            return self._dom_outcome
        return None

    def is_visible(self, selector: str, **kwargs: Any) -> bool:
        if selector == '[data-testid="stepup-dialog"]':
            return self._stepup_visible
        return False


@pytest.fixture
def base_sim_settings(tmp_path: Path) -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        database_url=f"sqlite:///{tmp_path / 'sim_tier2.db'}",
        jwt_secret="sim-tier2-test-secret-key-at-least-32-bytes-long",
    )


def test_tier2_refuses_non_local_host() -> None:
    """Tier 2 must refuse non-allowlisted hosts before any browser navigation or HTTP request."""
    with pytest.raises(SimulatorTargetError):
        run_tier2_session("https://resident.uidai.gov.in")

    fake_page = _FakePlaywrightPage()
    with pytest.raises(SimulatorTargetError):
        drive_tier2_playwright_page(fake_page, "https://example.com")
    assert fake_page.visited_urls == []


def test_tier2_succeeds_when_protection_is_off_and_is_denied_when_passive(
    base_sim_settings: Settings,
) -> None:
    """Tier 2 succeeds when protection_mode=off and is denied/challenged when passive."""
    off_cfg = dataclasses.replace(base_sim_settings, protection_mode="off")
    off_app = create_app(
        settings=off_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(off_cfg.database_url),
    )
    off_client, off_post, off_get = _make_asgi_transports(off_app)

    off_res = run_tier2_session(
        "http://127.0.0.1:8000",
        protection_mode="off",
        action="otp_request",
        post_fn=off_post,
        get_fn=off_get,
    )
    assert off_res.tier == "tier2"
    assert off_res.outcome == "allowed"
    assert off_res.portal_status == 200
    stats_off = off_client.get("/portal-api/stats").json()
    assert stats_off["accepted"] == 1
    assert stats_off["rejected"] == 0

    pas_cfg = dataclasses.replace(base_sim_settings, protection_mode="passive")
    pas_app = create_app(
        settings=pas_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(pas_cfg.database_url),
    )
    pas_client, pas_post, pas_get = _make_asgi_transports(pas_app)

    for action in ("otp_request", "details_update", "centre_search"):
        res = run_tier2_session(
            "http://127.0.0.1:8000",
            protection_mode="passive",
            action=action,
            post_fn=pas_post,
            get_fn=pas_get,
        )
        assert res.tier == "tier2"
        assert res.outcome in ("denied", "challenged")
        assert res.assess_decision in ("deny", "challenge")
        assert res.portal_status == 401

    stats_passive = pas_client.get("/portal-api/stats").json()
    assert stats_passive["accepted"] == 0
    assert stats_passive["rejected"] == 3


def test_drive_tier2_playwright_page_performs_direct_fill_and_click() -> None:
    """drive_tier2_playwright_page performs direct fills and clicks across portal actions."""
    login_page = _FakePlaywrightPage(dom_outcome="rejected", stepup_visible=False)
    res_login = run_tier2_session(
        "http://127.0.0.1:5173",
        protection_mode="passive",
        action="otp_request",
        page=login_page,
    )
    assert login_page.visited_urls == ["http://127.0.0.1:5173/?page=login"]
    assert login_page.fills == [('[data-testid="identifier-input"]', "999999999999")]
    assert login_page.clicks == ['[data-testid="send-otp-btn"]']
    assert res_login.tier == "tier2"
    assert res_login.outcome == "denied"

    stepup_page = _FakePlaywrightPage(dom_outcome=None, stepup_visible=True)
    res_challenged = drive_tier2_playwright_page(
        stepup_page,
        "http://127.0.0.1:5173",
        protection_mode="passive",
        action="centre_search",
        attempt_stepup=False,
    )
    assert stepup_page.visited_urls == ["http://127.0.0.1:5173/?page=centre-search"]
    assert stepup_page.fills == [('[data-testid="centre-query-input"]', "560001")]
    assert stepup_page.clicks == ['[data-testid="search-centres-btn"]']
    assert res_challenged.outcome == "challenged"

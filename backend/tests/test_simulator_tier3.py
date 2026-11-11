"""Unit tests for Tier 3 stealth-adjusted Playwright bot simulator (P7-14)."""

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
from simulator.tier3_stealth import (  # noqa: E402
    TIER3_INIT_SCRIPT,
    TIER3_PROFILES,
    build_tier3_behaviour_payload,
    build_tier3_env_signals,
    drive_tier3_playwright_page,
    run_tier3_session,
)

from app.config import Settings, load_settings  # noqa: E402
from app.db import DatabaseManager  # noqa: E402
from app.main import app as default_app  # noqa: E402
from app.main import create_app  # noqa: E402
from app.rules import evaluate_rule_score  # noqa: E402
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


class _FakeStealthPage:
    """Spy implementing ``PlaywrightPageLike`` plus ``add_init_script``."""

    def __init__(
        self,
        *,
        dom_outcome: str | None = "rejected",
        stepup_visible: bool = False,
    ) -> None:
        self.init_scripts: list[str] = []
        self.visited_urls: list[str] = []
        self.fills: list[tuple[str, str]] = []
        self.clicks: list[str] = []
        self._dom_outcome = dom_outcome
        self._stepup_visible = stepup_visible

    def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)

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
        database_url=f"sqlite:///{tmp_path / 'sim_tier3.db'}",
        jwt_secret="sim-tier3-test-secret-key-at-least-32-bytes-long",
    )


def test_tier3_refuses_non_local_host() -> None:
    """Tier 3 must refuse non-allowlisted hosts before any browser navigation or HTTP request."""
    with pytest.raises(SimulatorTargetError):
        run_tier3_session("https://resident.uidai.gov.in")

    fake_page = _FakeStealthPage()
    with pytest.raises(SimulatorTargetError):
        drive_tier3_playwright_page(fake_page, "https://example.com")
    assert fake_page.visited_urls == []
    assert fake_page.init_scripts == []


def test_tier3_profiles_exercise_rule_layer() -> None:
    """Verify that Tier 3 stealth profiles bypass R02_WEBDRIVER while exercising R03-R10."""
    behaviour = build_tier3_behaviour_payload()

    env_inconsistent = build_tier3_env_signals("inconsistent_ua_platform")
    score_inconsistent = evaluate_rule_score(env_inconsistent, behaviour)
    assert "R02_WEBDRIVER" not in score_inconsistent.fired_rules
    assert "R03_UA_PLATFORM_MISMATCH" in score_inconsistent.fired_rules
    assert "R04_UA_HINTS_MISMATCH" in score_inconsistent.fired_rules
    assert "R06_SOFTWARE_RENDERER" in score_inconsistent.fired_rules
    assert "R10_NATIVE_FUNCTION_TAMPER" in score_inconsistent.fired_rules
    assert score_inconsistent.rule_score > 0.60

    env_viewport = build_tier3_env_signals("viewport_touch_mismatch")
    score_viewport = evaluate_rule_score(env_viewport, behaviour)
    assert "R02_WEBDRIVER" not in score_viewport.fired_rules
    assert "R08_VIEWPORT_ANOMALY" in score_viewport.fired_rules
    assert "R09_TOUCH_INCONSISTENT" in score_viewport.fired_rules
    assert "R10_NATIVE_FUNCTION_TAMPER" in score_viewport.fired_rules

    env_clean = build_tier3_env_signals("clean_env_linear_input")
    score_clean = evaluate_rule_score(env_clean, behaviour)
    assert score_clean.fired_rules == []
    assert score_clean.rule_score == 0.0


def test_tier3_succeeds_when_protection_is_off_and_is_caught_when_passive(
    base_sim_settings: Settings,
) -> None:
    """Tier 3 succeeds when protection_mode=off and is denied/challenged when passive."""
    off_cfg = dataclasses.replace(base_sim_settings, protection_mode="off")
    off_app = create_app(
        settings=off_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(off_cfg.database_url),
    )
    off_client, off_post, off_get = _make_asgi_transports(off_app)

    off_res = run_tier3_session(
        "http://127.0.0.1:8000",
        protection_mode="off",
        action="otp_request",
        post_fn=off_post,
        get_fn=off_get,
    )
    assert off_res.tier == "tier3"
    assert off_res.outcome == "allowed"
    assert off_res.portal_status == 200
    stats_off = off_client.get("/portal-api/stats").json()
    assert stats_off["accepted"] == 1

    pas_cfg = dataclasses.replace(base_sim_settings, protection_mode="passive")
    pas_app = create_app(
        settings=pas_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(pas_cfg.database_url),
    )
    pas_client, pas_post, pas_get = _make_asgi_transports(pas_app)

    for profile in TIER3_PROFILES:
        res = run_tier3_session(
            "http://127.0.0.1:8000",
            protection_mode="passive",
            action="otp_request",
            profile=profile,
            post_fn=pas_post,
            get_fn=pas_get,
        )
        assert res.tier == "tier3"
        assert res.outcome in ("denied", "challenged")
        assert res.assess_decision in ("deny", "challenge")
        assert res.portal_status == 401

    stats_passive = pas_client.get("/portal-api/stats").json()
    assert stats_passive["accepted"] == 0
    assert stats_passive["rejected"] == len(TIER3_PROFILES)


def test_drive_tier3_playwright_page_applies_init_script() -> None:
    """drive_tier3_playwright_page injects TIER3_INIT_SCRIPT before navigating."""
    page = _FakeStealthPage(dom_outcome="rejected", stepup_visible=False)
    res = run_tier3_session(
        "http://127.0.0.1:5173",
        protection_mode="passive",
        action="otp_request",
        page=page,
    )
    assert page.init_scripts == [TIER3_INIT_SCRIPT]
    assert page.visited_urls == ["http://127.0.0.1:5173/?page=login"]
    assert res.tier == "tier3"
    assert res.params["init_script_applied"] is True
    assert res.outcome == "denied"

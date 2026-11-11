"""Unit tests for Appendix D.3 Bezier humanlike generators and Tier 4 bot simulator (P7-15)."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import numpy as np
import pytest
from fastapi import FastAPI
from test_api import _AsgiTestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.humanlike import (  # noqa: E402
    VALID_KEY_CLASSES,
    bezier_path,
    generate_humanlike_key_events,
    generate_humanlike_mouse_trajectory,
)
from simulator.safety import SimulatorTargetError  # noqa: E402
from simulator.tier1_http import HttpGetFn, HttpPostFn  # noqa: E402
from simulator.tier4_humanlike import (  # noqa: E402
    build_tier4_behaviour_payload,
    drive_tier4_playwright_page,
    run_tier4_session,
)

from app.config import Settings, load_settings  # noqa: E402
from app.db import DatabaseManager  # noqa: E402
from app.main import app as default_app  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas import BehaviourPayload  # noqa: E402
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


class _FakeMouse:
    def __init__(self) -> None:
        self.moves: list[tuple[float, float]] = []

    def move(self, x: float, y: float) -> None:
        self.moves.append((x, y))


class _FakeTier4Page:
    """Spy implementing ``PlaywrightPageLike`` with ``mouse.move`` and ``add_init_script``."""

    def __init__(
        self,
        *,
        dom_outcome: str | None = "accepted",
        stepup_visible: bool = False,
    ) -> None:
        self.mouse = _FakeMouse()
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
        database_url=f"sqlite:///{tmp_path / 'sim_tier4.db'}",
        jwt_secret="sim-tier4-test-secret-key-at-least-32-bytes-long",
    )


def test_bezier_path_and_humanlike_generators() -> None:
    """Verify Appendix D.3 bezier_path and human-like mouse/keyboard generators."""
    rng1 = np.random.default_rng(123)
    rng2 = np.random.default_rng(123)
    pts1 = bezier_path((50.0, 60.0), (320.0, 290.0), n=60, jitter=1.5, rng=rng1)
    pts2 = bezier_path((50.0, 60.0), (320.0, 290.0), n=60, jitter=1.5, rng=rng2)
    assert pts1.shape == (60, 2)
    assert np.allclose(pts1, pts2)

    # Smoothstep ease-in/out without jitter: middle step displacement > first step displacement
    pts_smooth = bezier_path(
        (0.0, 0.0),
        (300.0, 0.0),
        n=41,
        jitter=0.0,
        rng=np.random.default_rng(7),
    )
    first_step = float(np.linalg.norm(pts_smooth[1] - pts_smooth[0]))
    mid_step = float(np.linalg.norm(pts_smooth[20] - pts_smooth[19]))
    assert mid_step > first_step

    traj = generate_humanlike_mouse_trajectory(
        (60.0, 80.0),
        (250.0, 310.0),
        n=50,
        jitter=1.5,
        rng=np.random.default_rng(99),
    )
    assert len(traj) == 50
    times = [pt[2] for pt in traj]
    assert all(times[i] <= times[i + 1] for i in range(len(times) - 1))

    keys = generate_humanlike_key_events(
        num_keys=16,
        typo_prob=0.25,
        rng=np.random.default_rng(42),
    )
    assert len(keys) >= 16
    dwells: list[float] = []
    for ev in keys:
        cls_name, down_ms, up_ms = str(ev[0]), float(ev[1]), float(ev[2])  # type: ignore[arg-type]
        assert cls_name in VALID_KEY_CLASSES
        assert up_ms >= down_ms
        dwells.append(up_ms - down_ms)
    assert float(np.std(dwells)) > 1.0

    # Validate full BehaviourPayload schema compliance
    payload_dict = build_tier4_behaviour_payload(rng=np.random.default_rng(11))
    parsed = BehaviourPayload.model_validate(payload_dict)
    assert parsed.mouse is not None and len(parsed.mouse.points) >= 40
    assert parsed.keys is not None and len(parsed.keys.events) >= 12


def test_tier4_refuses_non_local_host() -> None:
    """Tier 4 must refuse non-allowlisted hosts before any browser navigation or HTTP request."""
    with pytest.raises(SimulatorTargetError):
        run_tier4_session("https://resident.uidai.gov.in")

    fake_page = _FakeTier4Page()
    with pytest.raises(SimulatorTargetError):
        drive_tier4_playwright_page(fake_page, "https://example.com")
    assert fake_page.visited_urls == []
    assert fake_page.mouse.moves == []


def test_tier4_succeeds_when_protection_is_off_and_records_honest_outcome_when_passive(
    base_sim_settings: Settings,
) -> None:
    """Tier 4 succeeds when protection_mode=off and records its passive outcome honestly."""
    off_cfg = dataclasses.replace(base_sim_settings, protection_mode="off")
    off_app = create_app(
        settings=off_cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(off_cfg.database_url),
    )
    off_client, off_post, off_get = _make_asgi_transports(off_app)

    off_res = run_tier4_session(
        "http://127.0.0.1:8000",
        protection_mode="off",
        action="otp_request",
        seed=42,
        post_fn=off_post,
        get_fn=off_get,
    )
    assert off_res.tier == "tier4"
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

    res_pas = run_tier4_session(
        "http://127.0.0.1:8000",
        protection_mode="passive",
        action="otp_request",
        seed=42,
        post_fn=pas_post,
        get_fn=pas_get,
    )
    assert res_pas.tier == "tier4"
    assert res_pas.outcome in ("allowed", "challenged", "denied")
    assert res_pas.assess_decision in ("allow", "challenge", "deny")
    assert res_pas.portal_status in (200, 401)
    stats_pas = pas_client.get("/portal-api/stats").json()
    assert stats_pas["total"] == 1


def test_drive_tier4_playwright_page_moves_along_bezier_curve() -> None:
    """drive_tier4_playwright_page moves the mouse along a Bezier curve before clicking."""
    page = _FakeTier4Page(dom_outcome="accepted", stepup_visible=False)
    res = run_tier4_session(
        "http://127.0.0.1:5173",
        protection_mode="passive",
        action="otp_request",
        n_curve_points=35,
        seed=7,
        page=page,
    )
    assert page.visited_urls == ["http://127.0.0.1:5173/?page=login"]
    assert len(page.mouse.moves) == 35
    assert res.tier == "tier4"
    assert res.outcome == "allowed"

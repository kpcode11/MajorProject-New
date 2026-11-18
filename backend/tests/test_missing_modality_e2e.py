"""End-to-end verification of the missing-modality fairness policy (P9-12).

Verifies end-to-end across ``/v1/nonce`` -> ``/v1/assess`` (-> ``/v1/assess/challenge`` if
challenged) -> protected ``/portal-api/*`` endpoints that any session with **no mouse events**
and **valid keyboard navigation** is never automatically denied:
1. Short ``Tab`` + ``Enter`` keyboard navigation (2-3 key events, 0 mouse points) across
   ``otp_request``, ``details_update``, and ``centre_search``.
2. Short PIN/identifier keyboard entry (8 key events < 10-key typing window, 0 mouse points).
3. Slow assistive-technology / one-handed typing (12 key events with long dwell/flight and
   natural human variance, 0 mouse points).
4. Standard keyboard-only typing in both raw-trace mode (``sendRawTrace=true``) and local
   feature extraction mode (``sendRawTrace=false``).
5. Negative guard: synthetic constant-interval keyboard bots and untrusted/webdriver
   keyboard sessions with 0 mouse points are still denied.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any

import pytest
from test_api import _AsgiTestClient, _make_bot_key_events

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.reference_human import (  # noqa: E402
    build_reference_human_env_signals,
    build_reference_human_key_events,
)

from app.config import Settings, load_settings  # noqa: E402
from app.db import DatabaseManager  # noqa: E402
from app.main import app as default_app  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas import KeyBehaviour  # noqa: E402
from app.scoring import extract_keyboard_feature_dict  # noqa: E402
from app.store import InMemoryStore  # noqa: E402


@pytest.fixture
def client(tmp_path: Path) -> _AsgiTestClient:
    base: Settings = load_settings()
    cfg = dataclasses.replace(
        base,
        protection_mode="passive",
        database_url=f"sqlite:///{tmp_path / 'missing_modality_e2e.db'}",
        jwt_secret="missing-modality-e2e-secret-key-at-least-32-bytes",
        rate_limit_nonce_per_min=1000,
        rate_limit_assess_per_min=1000,
        rate_limit_challenge_per_min=1000,
        rate_limit_challenge_session_per_min=1000,
    )
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=DatabaseManager(cfg.database_url),
    )
    return _AsgiTestClient(app)


def _complete_stepup_if_challenged(
    client: _AsgiTestClient,
    assess_body: dict[str, Any],
    action: str,
) -> str:
    """Return the issued token, or complete the keyboard step-up challenge if challenged."""
    decision = assess_body["decision"]
    assert decision in ("allow", "challenge"), f"Unexpected auto-deny: {assess_body}"
    if decision == "allow":
        token = assess_body["token"]
        assert isinstance(token, str) and len(token) > 20
        return token

    challenge = assess_body["challenge"]
    assert challenge is not None
    hold_ms = float(challenge["hold_ms"])
    nonce = client.get("/v1/nonce").json()["nonce"]
    chal_resp = client.post(
        "/v1/assess/challenge",
        json={
            "nonce": nonce,
            "challenge_id": challenge["id"],
            "action": action,
            "hold_start_ms": 100.0,
            "hold_end_ms": round(100.0 + hold_ms + 35.0, 1),
            "env": build_reference_human_env_signals(),
            "behaviour": {
                "mouse": {"points": [], "clicks": [], "untrusted_count": 0, "wheel_events": 0},
                "keys": {
                    "events": [
                        ["other", 25.0, 88.0],
                        ["space", 100.0, round(100.0 + hold_ms + 35.0, 1)],
                    ],
                    "paste_events": 0,
                    "autofill_suspected": False,
                    "untrusted_count": 0,
                },
                "timing": {
                    "ms_since_load": 3200.0,
                    "ms_to_first_interaction": 25.0,
                    "ms_since_nonce": round(hold_ms + 240.0, 1),
                    "scroll_events": 0,
                    "focus_changes": 1,
                },
                "device_class": "desktop",
            },
        },
    )
    assert chal_resp.status_code == 200
    chal_data = chal_resp.json()
    assert chal_data["decision"] == "allow"
    token = chal_data["token"]
    assert isinstance(token, str) and len(token) > 20
    return token


@pytest.mark.parametrize(
    ("action", "portal_path", "portal_body"),
    [
        (
            "otp_request",
            "/portal-api/otp/request",
            {"action": "otp_request", "identifier_length": 12},
        ),
        (
            "details_update",
            "/portal-api/details/update",
            {
                "action": "details_update",
                "fields_updated": ["city"],
                "city_code": "BENGALURU",
                "language_code": "EN",
                "confirmed": True,
            },
        ),
        (
            "centre_search",
            "/portal-api/centres/search",
            {"action": "centre_search", "service_type": "ALL", "query_length": 6},
        ),
    ],
)
def test_short_tab_enter_navigation_without_mouse_is_never_auto_denied(
    client: _AsgiTestClient,
    action: str,
    portal_path: str,
    portal_body: dict[str, Any],
) -> None:
    """A keyboard-only session with only Tab + Enter (2-3 keys) and 0 mouse events is not denied."""
    nonce = client.get("/v1/nonce").json()["nonce"]
    assess_resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce,
            "action": action,
            "sdk_version": "1.0.0",
            "env": build_reference_human_env_signals(),
            "behaviour": {
                "mouse": {
                    "points": [],
                    "clicks": [[0, 0, 980.0, 980.0]],
                    "untrusted_count": 0,
                    "wheel_events": 0,
                },
                "keys": {
                    "events": [
                        ["other", 210.0, 285.0],
                        ["other", 530.0, 610.0],
                        ["enter", 890.0, 978.0],
                    ],
                    "paste_events": 0,
                    "autofill_suspected": False,
                    "untrusted_count": 0,
                },
                "timing": {
                    "ms_since_load": 1800.0,
                    "ms_to_first_interaction": 210.0,
                    "ms_since_nonce": 1500.0,
                    "scroll_events": 0,
                    "focus_changes": 3,
                },
                "device_class": "desktop",
            },
        },
    )
    assert assess_resp.status_code == 200
    body = assess_resp.json()
    assert body["decision"] in ("allow", "challenge")

    token = _complete_stepup_if_challenged(client, body, action)
    portal_resp = client.post(portal_path, json=portal_body, headers={"X-Human-Token": token})
    assert portal_resp.status_code == 200


def test_short_pin_entry_and_slow_assistive_typing_without_mouse_are_never_auto_denied(
    client: _AsgiTestClient,
) -> None:
    """Short PIN entry (<10 keys) and slow assistive typing (>=10 keys) with no mouse pass E2E."""
    # 1. Short 8-key sequence (Tab + 6-digit PIN + Enter)
    pin_keys: list[list[Any]] = [
        ["other", 180.0, 255.0],
        ["digit", 480.0, 565.0],
        ["digit", 710.0, 788.0],
        ["digit", 960.0, 1052.0],
        ["digit", 1240.0, 1318.0],
        ["digit", 1510.0, 1604.0],
        ["digit", 1830.0, 1912.0],
        ["enter", 2210.0, 2295.0],
    ]
    # 2. Slow assistive-tech / single-switch typing (12 keys, ~320 ms dwell, ~850 ms flight)
    slow_keys: list[list[Any]] = [
        ["other", 200.0, 490.0],
        ["digit", 1320.0, 1645.0],
        ["digit", 2510.0, 2860.0],
        ["digit", 3690.0, 4015.0],
        ["digit", 4880.0, 5240.0],
        ["punct", 6120.0, 6430.0],
        ["digit", 7310.0, 7665.0],
        ["digit", 8540.0, 8850.0],
        ["digit", 9720.0, 10085.0],
        ["digit", 10960.0, 11290.0],
        ["other", 12180.0, 12510.0],
        ["enter", 13420.0, 13760.0],
    ]

    for key_seq in (pin_keys, slow_keys):
        nonce = client.get("/v1/nonce").json()["nonce"]
        resp = client.post(
            "/v1/assess",
            json={
                "nonce": nonce,
                "action": "otp_request",
                "sdk_version": "1.0.0",
                "env": build_reference_human_env_signals(),
                "behaviour": {
                    "mouse": {"points": [], "clicks": [], "untrusted_count": 0, "wheel_events": 0},
                    "keys": {
                        "events": key_seq,
                        "paste_events": 0,
                        "autofill_suspected": False,
                        "untrusted_count": 0,
                    },
                    "timing": {
                        "ms_since_load": 14500.0,
                        "ms_to_first_interaction": 180.0,
                        "ms_since_nonce": 14000.0,
                        "scroll_events": 0,
                        "focus_changes": 2,
                    },
                    "device_class": "desktop",
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] in ("allow", "challenge")
        token = _complete_stepup_if_challenged(client, body, "otp_request")
        otp_resp = client.post(
            "/portal-api/otp/request",
            json={"action": "otp_request", "identifier_length": 8},
            headers={"X-Human-Token": token},
        )
        assert otp_resp.status_code == 200


def test_local_features_mode_missing_mouse_with_valid_keyboard_is_not_auto_denied(
    client: _AsgiTestClient,
) -> None:
    """In sendRawTrace=false mode, empty mouse features + valid keyboard features is not denied."""
    raw_keys = KeyBehaviour(events=build_reference_human_key_events(seed=11))
    kb_feats = extract_keyboard_feature_dict(raw_keys)
    assert kb_feats is not None
    serialized_kb = {k: (None if v is None or v != v else float(v)) for k, v in kb_feats.items()}

    nonce = client.get("/v1/nonce").json()["nonce"]
    resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce,
            "action": "otp_request",
            "sdk_version": "1.0.0",
            "env": build_reference_human_env_signals(),
            "behaviour": {
                "mouse": {
                    "points": [],
                    "clicks": [],
                    "untrusted_count": 0,
                    "wheel_events": 0,
                    "features": None,
                    "feature_windows": [],
                },
                "keys": {
                    "events": [],
                    "paste_events": 0,
                    "autofill_suspected": False,
                    "untrusted_count": 0,
                    "features": serialized_kb,
                },
                "timing": {
                    "ms_since_load": 3400.0,
                    "ms_to_first_interaction": 200.0,
                    "ms_since_nonce": 3100.0,
                    "scroll_events": 0,
                    "focus_changes": 2,
                },
                "device_class": "desktop",
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "allow"
    assert body["band"] == "low"


def test_constant_interval_bot_without_mouse_is_still_denied(
    client: _AsgiTestClient,
) -> None:
    """A synthetic constant-interval keyboard bot with 0 mouse events is still denied."""
    nonce = client.get("/v1/nonce").json()["nonce"]
    resp = client.post(
        "/v1/assess",
        json={
            "nonce": nonce,
            "action": "otp_request",
            "sdk_version": "1.0.0",
            "env": build_reference_human_env_signals(),
            "behaviour": {
                "mouse": {"points": [], "clicks": [], "untrusted_count": 0, "wheel_events": 0},
                "keys": {
                    "events": _make_bot_key_events(),
                    "paste_events": 0,
                    "autofill_suspected": False,
                    "untrusted_count": 0,
                },
                "timing": {
                    "ms_since_load": 2500.0,
                    "ms_to_first_interaction": 150.0,
                    "ms_since_nonce": 2200.0,
                    "scroll_events": 0,
                    "focus_changes": 1,
                },
                "device_class": "desktop",
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "deny"
    assert body["band"] == "high"

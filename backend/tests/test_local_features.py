"""Backend tests for P9-08 local feature extraction mode (`sendRawTrace=false`).

Verifies that `ModelScorer` and `POST /v1/assess` produce identical model probabilities,
fused risk scores, and access decisions when given locally extracted feature maps
(`mouse.features` / `mouse.feature_windows` and `keys.features` with empty `points`/`events`)
compared to server-side raw trace extraction (`sendRawTrace=true`).
"""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path
from typing import Any

from test_api import (
    HUMAN_MOUSE_POINTS,
    _AsgiTestClient,
    _clean_desktop_env,
    _make_bot_key_events,
    _make_bot_mouse_points,
    _make_human_key_events,
)

from app.config import load_settings
from app.db import DatabaseManager
from app.main import app as default_app
from app.main import create_app
from app.schemas import BehaviourPayload, KeyBehaviour, MouseBehaviour
from app.scoring import extract_keyboard_feature_dict, extract_mouse_feature_windows
from app.store import InMemoryStore


def _serialize_feature_map(feats: dict[str, float]) -> dict[str, float | None]:
    return {
        k: (float(v) if v is not None and math.isfinite(float(v)) else None)
        for k, v in feats.items()
    }


def test_model_scorer_local_features_parity() -> None:
    """ModelScorer returns identical probabilities for local features vs raw traces."""
    scorer = default_app.state.scorer
    env = _clean_desktop_env()

    cases: list[tuple[str, MouseBehaviour, KeyBehaviour]] = [
        (
            "clean_human_session",
            MouseBehaviour(
                points=HUMAN_MOUSE_POINTS,
                clicks=[[767.0, 267.0, 830.0, 910.0]],
                untrusted_count=0,
                wheel_events=2,
            ),
            KeyBehaviour(
                events=_make_human_key_events(),
                paste_events=0,
                autofill_suspected=False,
                untrusted_count=0,
            ),
        ),
        (
            "linear_bot_session",
            MouseBehaviour(
                points=_make_bot_mouse_points(),
                clicks=[],
                untrusted_count=0,
                wheel_events=0,
            ),
            KeyBehaviour(
                events=_make_bot_key_events(),
                paste_events=0,
                autofill_suspected=False,
                untrusted_count=0,
            ),
        ),
    ]

    for label, raw_mouse, raw_keys in cases:
        raw_res = scorer.score(
            env,
            BehaviourPayload(device_class="desktop", mouse=raw_mouse, keys=raw_keys),
        )

        win_list = [
            _serialize_feature_map(w)
            for w in extract_mouse_feature_windows(raw_mouse, env, include_shortcut_features=True)
        ]
        kb_map = _serialize_feature_map(extract_keyboard_feature_dict(raw_keys) or {})

        local_mouse = MouseBehaviour(
            points=[],
            clicks=[],
            untrusted_count=raw_mouse.untrusted_count,
            wheel_events=raw_mouse.wheel_events,
            features=win_list[0] if win_list else None,
            feature_windows=win_list,
        )
        local_keys = KeyBehaviour(
            events=[],
            paste_events=raw_keys.paste_events,
            autofill_suspected=raw_keys.autofill_suspected,
            untrusted_count=raw_keys.untrusted_count,
            features=kb_map,
        )
        local_res = scorer.score(
            env,
            BehaviourPayload(device_class="desktop", mouse=local_mouse, keys=local_keys),
        )

        assert raw_res.mouse_score is not None and local_res.mouse_score is not None
        assert raw_res.keyboard_score is not None and local_res.keyboard_score is not None
        assert raw_res.model_score is not None and local_res.model_score is not None
        assert abs(raw_res.mouse_score - local_res.mouse_score) <= 1e-7, label
        assert abs(raw_res.keyboard_score - local_res.keyboard_score) <= 1e-7, label
        assert abs(raw_res.model_score - local_res.model_score) <= 1e-7, label
        assert abs(raw_res.score - local_res.score) <= 1e-7, label
        assert raw_res.band == local_res.band, label
        assert raw_res.top_features == local_res.top_features, label


def test_assess_endpoint_accepts_local_features_without_raw_traces(tmp_path: Path) -> None:
    """POST /v1/assess scores local features when points/events are empty (sendRawTrace=false)."""
    base_cfg = load_settings()
    cfg = dataclasses.replace(
        base_cfg,
        database_url=f"sqlite:///{(tmp_path / 'local_feat_test.db').as_posix()}",
        jwt_secret="local-feature-test-secret-key-at-least-32-bytes!",
        store_features_in_db=True,
        retention_purge_interval_seconds=0,
    )
    db = DatabaseManager(cfg.database_url, store_features_in_db=True)
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=db,
    )
    client = _AsgiTestClient(app)

    env = _clean_desktop_env()
    raw_mouse = MouseBehaviour(points=HUMAN_MOUSE_POINTS)
    raw_keys = KeyBehaviour(events=_make_human_key_events())
    win_list = [
        _serialize_feature_map(w)
        for w in extract_mouse_feature_windows(raw_mouse, env, include_shortcut_features=True)
    ]
    kb_map = _serialize_feature_map(extract_keyboard_feature_dict(raw_keys) or {})

    nonce = client.get("/v1/nonce").json()["nonce"]
    payload: dict[str, Any] = {
        "nonce": nonce,
        "action": "login",
        "sdk_version": "1.0.0",
        "schema_version": 1,
        "env": env.model_dump(exclude_none=True),
        "behaviour": {
            "device_class": "desktop",
            "mouse": {
                "points": [],
                "clicks": [],
                "untrusted_count": 0,
                "wheel_events": 0,
                "features": win_list[0],
                "feature_windows": win_list,
            },
            "keys": {
                "events": [],
                "paste_events": 0,
                "autofill_suspected": False,
                "untrusted_count": 0,
                "features": kb_map,
            },
        },
    }
    resp = client.post("/v1/assess", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "allow"
    assert body["band"] == "low"
    assert body["degraded"] is False

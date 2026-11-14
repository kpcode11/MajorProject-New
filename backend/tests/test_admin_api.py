"""Unit tests for the Phase 9 Admin API endpoints (P9-01)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from test_api import _AsgiTestClient

from app.config import load_settings
from app.db import DatabaseManager
from app.main import app as default_app
from app.main import create_app
from app.store import InMemoryStore


def _build_admin_test_client(
    tmp_path: Path,
    *,
    admin_key: str = "test-admin-secret-key",
    store_features_in_db: bool = True,
) -> tuple[_AsgiTestClient, DatabaseManager, FastAPI]:
    base_cfg = load_settings()
    cfg = dataclasses.replace(
        base_cfg,
        database_url=f"sqlite:///{tmp_path / 'admin_test.db'}",
        jwt_secret="admin-test-jwt-secret-key-at-least-32-bytes-long",
        admin_api_key=admin_key,
        store_features_in_db=store_features_in_db,
        feature_ttl_seconds=3600,
        assessment_ttl_seconds=86400,
    )
    db = DatabaseManager(
        cfg.database_url,
        store_features_in_db=cfg.store_features_in_db,
        feature_ttl_seconds=cfg.feature_ttl_seconds,
        assessment_ttl_seconds=cfg.assessment_ttl_seconds,
    )
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=db,
    )
    return _AsgiTestClient(app), db, app


def test_admin_endpoints_require_valid_api_key(tmp_path: Path) -> None:
    """All /admin/* endpoints must reject missing or invalid API keys with 401."""
    client, _, _ = _build_admin_test_client(tmp_path, admin_key="secret-key-123")

    for path in (
        "/admin/overview",
        "/admin/scores",
        "/admin/assessments",
        "/admin/assessments/nonexistent",
        "/admin/feedback",
        "/admin/sim-results",
        "/admin/privacy",
    ):
        resp_missing = client.get(path)
        assert resp_missing.status_code == 401
        assert resp_missing.json()["error"]["code"] == "unauthorized_admin"

        resp_wrong = client.get(path, headers={"X-Admin-Key": "wrong-key"})
        assert resp_wrong.status_code == 401

    # Valid key via X-Admin-Key or Authorization: Bearer succeeds
    ok_hdr = client.get("/admin/overview", headers={"X-Admin-Key": "secret-key-123"})
    assert ok_hdr.status_code == 200
    ok_bearer = client.get(
        "/admin/overview",
        headers={"Authorization": "Bearer secret-key-123"},
    )
    assert ok_bearer.status_code == 200


def test_admin_overview_scores_assessments_and_detail(tmp_path: Path) -> None:
    """Verify /admin/overview, /admin/scores, /admin/assessments, and /admin/assessments/{id}."""
    client, db, _ = _build_admin_test_client(tmp_path, store_features_in_db=True)
    headers = {"X-Admin-Key": "test-admin-secret-key"}
    now = datetime.now(UTC)

    id_allow = db.record_assessment(
        assessment_id="assess-allow-1",
        session_hash="sess_allow",
        action="otp_request",
        device_class="desktop",
        score=0.08,
        band="low",
        decision="allow",
        rules_fired=[],
        top_factors=["mouse:straightness_mean", "keyboard:dwell_std"],
        model_versions={"mouse": "lightgbm-v1", "keyboard": "logistic_regression-v1"},
        latency_ms=3.5,
        degraded=False,
        derived_features={
            "mouse:straightness_mean": 0.912,
            "keyboard:dwell_std": 18.4,
        },
        now=now,
    )
    id_chal = db.record_assessment(
        assessment_id="assess-chal-2",
        session_hash="sess_chal",
        action="centre_search",
        device_class="desktop",
        score=0.45,
        band="medium",
        decision="challenge",
        rules_fired=["R06_SOFTWARE_RENDERER"],
        top_factors=["R06_SOFTWARE_RENDERER", "mouse:dt_cv_mean"],
        model_versions={"mouse": "lightgbm-v1", "keyboard": "logistic_regression-v1"},
        latency_ms=5.1,
        degraded=False,
        derived_features={"mouse:dt_cv_mean": 0.04},
        now=now,
    )
    db.record_challenge_issued(
        challenge_id="chal-for-2",
        assessment_id=id_chal,
        challenge_type="press_hold",
        now=now,
    )
    db.record_challenge_completed(
        challenge_id="chal-for-2",
        outcome="passed",
        now=now,
    )
    db.record_assessment(
        assessment_id="assess-deny-3",
        session_hash="sess_deny",
        action="otp_request",
        device_class="desktop",
        score=0.92,
        band="high",
        decision="deny",
        rules_fired=["R02_WEBDRIVER", "R11_UNTRUSTED_EVENTS"],
        top_factors=["R02_WEBDRIVER", "R11_UNTRUSTED_EVENTS"],
        model_versions={"mouse": "lightgbm-v1", "keyboard": "logistic_regression-v1"},
        latency_ms=1.8,
        degraded=False,
        now=now,
    )

    # 1. /admin/overview
    ov = client.get("/admin/overview", headers=headers).json()
    assert ov["total_assessments"] == 3
    assert ov["decisions"] == {"allow": 1, "challenge": 1, "deny": 1}
    assert ov["latency_ms"]["mean"] > 0
    assert ov["latency_ms"]["p50"] > 0
    assert ov["latency_ms"]["p95"] >= ov["latency_ms"]["p50"]
    assert "SSO" in ov["auth_note"] and "RBAC" in ov["auth_note"]

    # 2. /admin/scores
    scores = client.get("/admin/scores?bins=10", headers=headers).json()
    assert scores["total_scored"] == 3
    assert len(scores["bins"]) == 10
    assert sum(b["count"] for b in scores["bins"]) == 3
    assert "high" in scores["thresholds"]
    assert "allow_below" in scores["thresholds"]["high"]
    assert "low" in scores["band_cutoffs"]

    # 3. /admin/assessments list & filters
    listed = client.get("/admin/assessments?decision=deny", headers=headers).json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == "assess-deny-3"

    # 4. /admin/assessments/{id} detail (derived values only, no raw traces)
    detail_allow = client.get(f"/admin/assessments/{id_allow}", headers=headers).json()
    assert detail_allow["id"] == id_allow
    assert detail_allow["decision"] == "allow"
    assert detail_allow["features"]["mouse:straightness_mean"] == 0.912
    assert detail_allow["top_contributing_features"][0] == {
        "feature": "mouse:straightness_mean",
        "value": 0.912,
    }

    detail_chal = client.get(f"/admin/assessments/{id_chal}", headers=headers).json()
    assert len(detail_chal["challenges"]) == 1
    assert detail_chal["challenges"][0]["id"] == "chal-for-2"
    assert detail_chal["challenges"][0]["outcome"] == "passed"

    not_found = client.get("/admin/assessments/does-not-exist", headers=headers)
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "assessment_not_found"


def test_admin_feedback_queue_and_update(tmp_path: Path) -> None:
    """Verify marking fp/fn via POST /admin/feedback and listing via GET /admin/feedback."""
    client, db, _ = _build_admin_test_client(tmp_path)
    headers = {"X-Admin-Key": "test-admin-secret-key"}

    a1 = db.record_assessment(
        assessment_id="fb-1",
        session_hash="s1",
        action="otp_request",
        score=0.81,
        band="high",
        decision="deny",
    )
    a2 = db.record_assessment(
        assessment_id="fb-2",
        session_hash="s2",
        action="otp_request",
        score=0.05,
        band="low",
        decision="allow",
    )

    resp_fp = client.post(
        "/admin/feedback",
        json={"assessment_id": a1, "feedback": "fp"},
        headers=headers,
    )
    assert resp_fp.status_code == 200
    assert resp_fp.json()["feedback"] == "fp"
    assert resp_fp.json()["training_policy"] == "stored_only_never_auto_trained"

    resp_fn = client.post(
        "/admin/feedback",
        json={"assessment_id": a2, "feedback": "fn"},
        headers=headers,
    )
    assert resp_fn.status_code == 200
    assert resp_fn.json()["feedback"] == "fn"

    queue = client.get("/admin/feedback", headers=headers).json()
    assert queue["total"] == 2
    assert queue["fp_count"] == 1
    assert queue["fn_count"] == 1
    assert len(queue["items"]) == 2

    only_fp = client.get("/admin/feedback?feedback=fp", headers=headers).json()
    assert len(only_fp["items"]) == 1
    assert only_fp["items"][0]["id"] == a1

    # Clear feedback on a1
    resp_clear = client.post(
        "/admin/feedback",
        json={"assessment_id": a1, "feedback": None},
        headers=headers,
    )
    assert resp_clear.status_code == 200
    assert resp_clear.json()["feedback"] is None
    queue_after = client.get("/admin/feedback", headers=headers).json()
    assert queue_after["total"] == 1


def test_admin_sim_results_and_privacy_panel(tmp_path: Path) -> None:
    """Verify /admin/sim-results ingestion/summary and /admin/privacy counts/purge."""
    client, db, app = _build_admin_test_client(tmp_path, store_features_in_db=True)
    headers = {"X-Admin-Key": "test-admin-secret-key"}

    # Point sim_runs_path to an isolated file so we can test ingestion deterministically
    sim_file = tmp_path / "sim_runs.jsonl"
    app.state.sim_runs_path = sim_file

    ingest = client.post(
        "/admin/sim-results",
        json={
            "replace": True,
            "runs": [
                {
                    "tier": "tier1",
                    "protection_mode": "passive",
                    "action": "otp_request",
                    "outcome": "blocked-at-api",
                    "portal_status": 401,
                    "latency_ms": 1.2,
                },
                {
                    "tier": "tier4",
                    "protection_mode": "passive",
                    "action": "otp_request",
                    "outcome": "denied",
                    "portal_status": 401,
                    "assess_decision": "deny",
                    "assess_band": "high",
                    "latency_ms": 4.8,
                },
            ],
        },
        headers=headers,
    )
    assert ingest.status_code == 200
    sim_data = ingest.json()
    assert sim_data["total_runs"] == 2
    assert sim_data["by_mode"]["passive"]["tier1"]["blocked_at_api"] == 1
    assert sim_data["by_mode"]["passive"]["tier4"]["denied"] == 1
    assert "No model, feature, or threshold was tuned" in sim_data["disclaimer"]

    # Insert an expired feature record and an expired assessment record
    old_ts = datetime.now(UTC) - timedelta(days=2)
    db.record_assessment(
        assessment_id="old-expired-assess",
        session_hash="s_old",
        action="login",
        score=0.22,
        band="low",
        decision="allow",
        derived_features={"mouse:speed_mean_mean": 310.0},
        now=old_ts,
    )
    recent_feat_expired_ts = datetime.now(UTC) - timedelta(hours=2)
    db.record_assessment(
        assessment_id="recent-feat-expired",
        session_hash="s_recent",
        action="login",
        score=0.18,
        band="low",
        decision="allow",
        derived_features={"mouse:speed_mean_mean": 410.0},
        now=recent_feat_expired_ts,
    )

    priv_before = client.get("/admin/privacy", headers=headers).json()
    assert priv_before["retention_settings"]["store_features_in_db"] is True
    assert priv_before["record_counts"]["total_assessments"] == 2
    assert priv_before["record_counts"]["assessments_with_features"] == 2
    assert priv_before["record_counts"]["expired_feature_records"] == 2
    assert priv_before["record_counts"]["expired_assessment_records"] == 1

    purge_resp = client.post("/admin/privacy/purge", headers=headers)
    assert purge_resp.status_code == 200
    purge_data = purge_resp.json()
    assert purge_data["features_purged"] == 2
    assert purge_data["assessments_purged"] == 1

    priv_after = client.get("/admin/privacy", headers=headers).json()
    assert priv_after["record_counts"]["total_assessments"] == 1
    assert priv_after["record_counts"]["assessments_with_features"] == 0
    assert priv_after["last_purge"]["last_purge_at"] is not None
    assert priv_after["last_purge"]["features_purged"] == 2
    assert priv_after["last_purge"]["assessments_purged"] == 1

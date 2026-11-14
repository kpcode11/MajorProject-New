"""E2E smoke: admin dashboard data loads from the running backend (P9-03).

Seeds assessments, simulator runs, and a purgeable feature blob, then hits the same
``/admin/*`` endpoints the React dashboard uses on first paint.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from test_admin_api import _build_admin_test_client


def test_dashboard_smoke_loads_all_admin_views_from_backend(tmp_path: Path) -> None:
    """The six dashboard views can be populated from live admin API responses."""
    client, db, app = _build_admin_test_client(tmp_path, store_features_in_db=True)
    headers = {"X-Admin-Key": "test-admin-secret-key"}
    now = datetime.now(UTC)

    db.record_assessment(
        assessment_id="dash-allow-1",
        session_hash="sess_allow",
        action="otp_request",
        device_class="desktop",
        score=0.08,
        band="low",
        decision="allow",
        rules_fired=[],
        top_factors=["mouse:straightness_mean"],
        model_versions={
            "mouse": "lightgbm-v1",
            "keyboard": "logistic_regression-v1",
            "fusion": "v1",
        },
        latency_ms=3.5,
        degraded=False,
        derived_features={"mouse:straightness_mean": 0.912, "keyboard:dwell_std": 18.4},
        now=now,
    )
    db.record_assessment(
        assessment_id="dash-deny-2",
        session_hash="sess_deny",
        action="otp_request",
        device_class="desktop",
        score=0.92,
        band="high",
        decision="deny",
        rules_fired=["R02_WEBDRIVER"],
        top_factors=["R02_WEBDRIVER"],
        model_versions={"mouse": "lightgbm-v1"},
        latency_ms=1.8,
        degraded=False,
        now=now,
    )
    expired = now - timedelta(days=2)
    db.record_assessment(
        assessment_id="dash-expired-3",
        session_hash="sess_old",
        action="login",
        score=0.22,
        band="low",
        decision="allow",
        derived_features={"mouse:speed_mean_mean": 310.0},
        now=expired,
    )

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

    overview = client.get("/admin/overview", headers=headers)
    scores = client.get("/admin/scores?bins=10", headers=headers)
    assessments = client.get("/admin/assessments?limit=25", headers=headers)
    detail = client.get("/admin/assessments/dash-allow-1", headers=headers)
    feedback = client.get("/admin/feedback", headers=headers)
    sim = client.get("/admin/sim-results", headers=headers)
    privacy = client.get("/admin/privacy", headers=headers)

    for resp in (overview, scores, assessments, detail, feedback, sim, privacy):
        assert resp.status_code == 200, resp.text

    ov = overview.json()
    assert ov["total_assessments"] == 3
    assert ov["decisions"]["allow"] == 2
    assert ov["decisions"]["deny"] == 1
    assert ov["model_versions"]["mouse"]
    assert "RBAC" in ov["auth_note"]

    sc = scores.json()
    assert len(sc["bins"]) == 10
    assert "high" in sc["thresholds"]
    assert "allow_below" in sc["thresholds"]["high"]
    assert "deny_at_or_above" in sc["thresholds"]["high"]

    listed = assessments.json()
    assert listed["total"] >= 2
    ids = {item["id"] for item in listed["items"]}
    assert "dash-allow-1" in ids

    det = detail.json()
    assert det["decision"] == "allow"
    assert det["features"]["mouse:straightness_mean"] == 0.912
    assert det["top_contributing_features"][0]["feature"] == "mouse:straightness_mean"
    assert "privacy_note" in det
    feature_names = {item["feature"] for item in det["top_contributing_features"]}
    assert all(":" in name or name.startswith("R") for name in feature_names)
    assert not any("keydown" in name or name.endswith("points") for name in feature_names)

    sim_data = sim.json()
    assert sim_data["total_runs"] == 2
    assert any(row["tier"] == "tier1" for row in sim_data["tiers"])
    assert any(row["tier"] == "tier4" for row in sim_data["tiers"])

    mark_fp = client.post(
        "/admin/feedback",
        json={"assessment_id": "dash-deny-2", "feedback": "fp"},
        headers=headers,
    )
    assert mark_fp.status_code == 200
    assert mark_fp.json()["training_policy"] == "stored_only_never_auto_trained"
    queue = client.get("/admin/feedback", headers=headers).json()
    assert queue["fp_count"] == 1

    priv = privacy.json()
    assert priv["retention_settings"]["store_features_in_db"] is True
    assert priv["record_counts"]["total_assessments"] == 3
    purge = client.post("/admin/privacy/purge", headers=headers)
    assert purge.status_code == 200
    assert purge.json()["features_purged"] >= 1
    after = client.get("/admin/privacy", headers=headers).json()
    assert after["last_purge"]["last_purge_at"] is not None

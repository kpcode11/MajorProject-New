"""Tests for SQLAlchemy persistence models, migrations, and fail-safe buffering (P5-08)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.db import DatabaseManager, sanitize_derived_features


class TestDatabasePersistenceAndPrivacy:
    def test_assessment_persisted_without_features_by_default(self, tmp_path: Path) -> None:
        db = DatabaseManager(
            f"sqlite:///{tmp_path / 'test.db'}",
            store_features_in_db=False,
        )
        assert db.ping() is True

        rec_id = db.record_assessment(
            session_hash="sess_1234",
            action="otp_request",
            device_class="desktop",
            score=0.12,
            band="low",
            decision="allow",
            rules_fired=[],
            top_factors=["mouse:window_dt_cv", "keyboard:flight_p5"],
            model_versions={"mouse": "lightgbm-v1", "keyboard": "logistic_regression-v1"},
            latency_ms=4.2,
            degraded=False,
            derived_features={"speed_mean_mean": 510.2, "typing_speed_cps": 4.8},
        )
        row = db.get_assessment(rec_id)
        assert row is not None
        assert row.action == "otp_request"
        assert row.score == pytest.approx(0.12)
        assert row.band == "low"
        assert row.decision == "allow"
        assert row.features is None
        assert row.features_expires_at is None

    def test_optional_feature_storage_and_ttl_purge(self, tmp_path: Path) -> None:
        db = DatabaseManager(
            f"sqlite:///{tmp_path / 'features.db'}",
            store_features_in_db=True,
            feature_ttl_seconds=3600,
        )
        t0 = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)
        rec_id = db.record_assessment(
            session_hash="sess_5678",
            action="login",
            score=0.45,
            band="medium",
            decision="challenge",
            derived_features={"speed_mean_mean": 480.0, "dwell_mean": 95.0},
            now=t0,
        )
        row = db.get_assessment(rec_id)
        assert row is not None
        assert row.features == {"speed_mean_mean": 480.0, "dwell_mean": 95.0}
        assert row.features_expires_at is not None

        # Before expiry: 0 rows purged
        assert db.purge_expired_features(now=t0 + timedelta(minutes=30)) == 0
        # After expiry: features nulled out while assessment row remains
        assert db.purge_expired_features(now=t0 + timedelta(hours=2)) == 1
        after = db.get_assessment(rec_id)
        assert after is not None
        assert after.features is None
        assert after.features_expires_at is None
        assert after.decision == "challenge"

    def test_prohibited_raw_trace_keys_rejected(self) -> None:
        for bad_key in ("points", "events", "gestures", "clicks", "raw_trace", "text"):
            with pytest.raises(ValueError, match="prohibited raw trace key"):
                sanitize_derived_features({bad_key: [1, 2, 3]})

    def test_challenge_lifecycle_and_db_down_buffering(self, tmp_path: Path) -> None:
        db = DatabaseManager(f"sqlite:///{tmp_path / 'buffer.db'}")

        # Simulate DB outage: writes buffer in memory without raising
        db.set_simulated_outage(True)
        assert db.ping() is False

        rec_id = db.record_assessment(
            session_hash="sess_buf",
            action="otp_request",
            score=0.52,
            band="medium",
            decision="challenge",
        )
        db.record_challenge_issued(
            challenge_id="chal_1",
            assessment_id=rec_id,
            challenge_type="press_hold",
        )
        db.record_challenge_completed(
            challenge_id="chal_1",
            outcome="passed",
        )
        assert db.buffered_count == 3

        # Recover DB and flush buffer
        db.set_simulated_outage(False)
        assert db.ping() is True
        flushed = db.flush_buffer()
        assert flushed == 3
        assert db.buffered_count == 0

        chal = db.get_challenge("chal_1")
        assert chal is not None
        assert chal.assessment_id == rec_id
        assert chal.outcome == "passed"
        assert chal.completed_at is not None


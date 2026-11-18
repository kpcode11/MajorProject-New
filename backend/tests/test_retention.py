"""Unit tests for the P9-04 retention purge (fake clock, scheduler, CLI)."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import pytest

from app.db import DatabaseManager
from app.retention import (
    FakeClock,
    RetentionScheduler,
    main,
    run_retention_purge,
)


def _db(
    tmp_path: Path,
    *,
    store_features_in_db: bool = True,
    feature_ttl_seconds: int = 3600,
    assessment_ttl_seconds: int = 86400,
) -> DatabaseManager:
    return DatabaseManager(
        f"sqlite:///{tmp_path / 'retention.db'}",
        store_features_in_db=store_features_in_db,
        feature_ttl_seconds=feature_ttl_seconds,
        assessment_ttl_seconds=assessment_ttl_seconds,
    )


def test_fake_clock_purges_expired_features_but_keeps_fresh_ones(tmp_path: Path) -> None:
    db = _db(tmp_path)
    t0 = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    clock = FakeClock(t0)

    expired_id = db.record_assessment(
        assessment_id="feat-old",
        session_hash="sess_old",
        action="login",
        score=0.2,
        band="low",
        decision="allow",
        derived_features={"mouse:speed_mean_mean": 310.0},
        now=t0,
    )
    clock.advance(timedelta(minutes=30))
    fresh_id = db.record_assessment(
        assessment_id="feat-new",
        session_hash="sess_new",
        action="login",
        score=0.18,
        band="low",
        decision="allow",
        derived_features={"mouse:speed_mean_mean": 410.0},
        now=clock.now(),
    )

    clock.set(t0 + timedelta(minutes=30))
    early = run_retention_purge(db, clock=clock)
    assert early.features_purged == 0
    assert early.assessments_purged == 0
    still_present = db.get_assessment(expired_id)
    assert still_present is not None
    assert still_present.features is not None

    clock.set(t0 + timedelta(hours=1, minutes=5))
    later = run_retention_purge(db, clock=clock)
    assert later.features_purged == 1
    assert later.assessments_purged == 0
    old_row = db.get_assessment(expired_id)
    new_row = db.get_assessment(fresh_id)
    assert old_row is not None and old_row.features is None
    assert new_row is not None and new_row.features is not None


def test_fake_clock_deletes_assessments_past_long_term_ttl(tmp_path: Path) -> None:
    db = _db(tmp_path, assessment_ttl_seconds=24 * 3600)
    t0 = datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC)
    clock = FakeClock(t0)

    old_id = db.record_assessment(
        assessment_id="assess-old",
        session_hash="sess_old",
        action="otp_request",
        score=0.9,
        band="high",
        decision="deny",
        derived_features={"mouse:straightness_mean": 0.1},
        now=t0,
    )
    clock.advance(timedelta(hours=20))
    new_id = db.record_assessment(
        assessment_id="assess-new",
        session_hash="sess_new",
        action="otp_request",
        score=0.05,
        band="low",
        decision="allow",
        now=clock.now(),
    )

    clock.set(t0 + timedelta(hours=25))
    result = run_retention_purge(db, clock=clock)
    assert result.assessments_purged == 1
    assert db.get_assessment(old_id) is None
    kept = db.get_assessment(new_id)
    assert kept is not None
    assert kept.session_hash == "sess_new"


def test_scheduler_run_once_uses_injected_clock(tmp_path: Path) -> None:
    db = _db(tmp_path, feature_ttl_seconds=60)
    t0 = datetime(2026, 11, 14, 8, 0, 0, tzinfo=UTC)
    db.record_assessment(
        assessment_id="sched-1",
        session_hash="s1",
        action="login",
        score=0.3,
        band="low",
        decision="allow",
        derived_features={"keyboard:dwell_mean": 90.0},
        now=t0,
    )
    clock = FakeClock(t0 + timedelta(seconds=61))
    scheduler = RetentionScheduler(db, clock=clock, interval_seconds=0)
    result = scheduler.run_once()
    assert result.features_purged == 1
    assert scheduler.last_result == result
    scheduler.start()
    assert scheduler.running is False


def test_scheduler_loop_honours_interval_via_wait_fn(tmp_path: Path) -> None:
    db = _db(tmp_path)
    clock = FakeClock(datetime(2026, 11, 14, 9, 0, 0, tzinfo=UTC))
    seen_timeout: list[float] = []
    started = threading.Event()

    def wait_fn(event: threading.Event, timeout: float) -> bool:
        seen_timeout.append(timeout)
        started.set()
        event.set()
        return True

    scheduler = RetentionScheduler(
        db,
        clock=clock,
        interval_seconds=77,
        wait_fn=wait_fn,
    )
    scheduler.start()
    assert started.wait(timeout=2.0)
    scheduler.stop()
    assert seen_timeout == [77.0]
    assert scheduler.running is False
    assert scheduler.last_result is not None


def test_retention_cli_once_prints_json(tmp_path: Path) -> None:
    db = _db(tmp_path, feature_ttl_seconds=1)
    t0 = datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)
    db.record_assessment(
        assessment_id="cli-1",
        session_hash="s_cli",
        action="login",
        score=0.4,
        band="medium",
        decision="challenge",
        derived_features={"mouse:dt_cv_mean": 0.2},
        now=t0,
    )
    buf = StringIO()
    clock = FakeClock(t0 + timedelta(seconds=2))
    code = main(["--once"], stdout=buf, db=db, clock=clock)
    assert code == 0
    payload = json.loads(buf.getvalue())
    assert payload["features_purged"] == 1
    assert payload["assessments_purged"] == 0
    assert payload["purged_at"].endswith("Z")


def test_negative_interval_rejected(tmp_path: Path) -> None:
    db = _db(tmp_path)
    with pytest.raises(ValueError, match="interval_seconds"):
        RetentionScheduler(db, interval_seconds=-1)

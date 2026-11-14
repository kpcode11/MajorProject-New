"""SQLAlchemy persistence models, schema migrations, and fail-safe write buffering (P5-08).

Implements the ``assessments`` and ``challenges`` tables from Appendix B.5 using
SQLAlchemy 2.0 declarative models compatible with both SQLite (default) and
PostgreSQL.

Privacy & Retention Guarantees:
- Raw mouse coordinate traces, keystroke arrays, and touch point arrays are
  **never** persisted.
- Derived numerical features are stored **only** when
  ``settings.store_features_in_db`` is ``True``, and are tagged with
  ``features_expires_at`` (default 7-day TTL).
- When the database is unreachable (``db_down`` fail-safe mode), assessment and
  challenge writes are buffered in memory (bounded ring buffer) so live request
  scoring never fails due to a database outage.
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    create_engine,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

MAX_BUFFER_SIZE = 1000


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for BotGuard persistence models."""


class AssessmentRecord(Base):
    """Row in the ``assessments`` table (Appendix B.5)."""

    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('allow', 'challenge', 'deny')",
            name="ck_assessments_decision",
        ),
        CheckConstraint(
            "feedback IS NULL OR feedback IN ('fp', 'fn')",
            name="ck_assessments_feedback",
        ),
        Index("assessments_ts_idx", "ts"),
        Index("assessments_decision_ts_idx", "decision", "ts"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    session_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    device_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    band: Mapped[str] = mapped_column(String(16), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    rules_fired: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    top_factors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    model_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback: Mapped[str | None] = mapped_column(String(8), nullable=True)
    features: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    features_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ChallengeRecord(Base):
    """Row in the ``challenges`` table (Appendix B.5)."""

    __tablename__ = "challenges"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    assessment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("assessments.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)


# Prohibited raw trace keys that must never be stored in the features JSON column
_PROHIBITED_RAW_FEATURE_KEYS: frozenset[str] = frozenset(
    {"points", "events", "gestures", "clicks", "raw_trace", "keystrokes", "text", "key"}
)


def sanitize_derived_features(
    features: dict[str, Any] | None,
) -> dict[str, float] | None:
    """Ensure only scalar numeric derived features are persisted (never raw traces)."""
    if not features:
        return None
    cleaned: dict[str, float] = {}
    for k, v in features.items():
        key_str = str(k)
        if key_str.lower() in _PROHIBITED_RAW_FEATURE_KEYS:
            raise ValueError(f"Refusing to persist prohibited raw trace key: {key_str!r}")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            cleaned[key_str] = float(v)
    return cleaned or None


def create_db_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for SQLite or PostgreSQL."""
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args, future=True)


def run_migrations(engine: Engine) -> None:
    """Create or upgrade schema tables and indexes idempotently."""
    Base.metadata.create_all(bind=engine)


class DatabaseManager:
    """Session factory and fail-safe buffered writer for ``assessments`` and ``challenges``."""

    def __init__(
        self,
        database_url: str = "sqlite:///./botguard.db",
        *,
        store_features_in_db: bool = False,
        feature_ttl_seconds: int = 7 * 24 * 3600,
        assessment_ttl_seconds: int = 30 * 24 * 3600,
        auto_migrate: bool = True,
    ) -> None:
        self.database_url = database_url
        self.store_features_in_db = store_features_in_db
        self.feature_ttl_seconds = feature_ttl_seconds
        self.assessment_ttl_seconds = assessment_ttl_seconds
        self.engine = create_db_engine(database_url)
        self._session_factory = sessionmaker(
            bind=self.engine, expire_on_commit=False, class_=Session
        )
        self._lock = threading.Lock()
        self._buffer: deque[tuple[str, dict[str, Any]]] = deque(maxlen=MAX_BUFFER_SIZE)
        self._simulate_down: bool = False
        self.last_purge_at: datetime | None = None
        self.last_features_purged: int = 0
        self.last_assessments_purged: int = 0
        if auto_migrate:
            run_migrations(self.engine)

    def session(self) -> Session:
        """Open a new SQLAlchemy ``Session``."""
        return self._session_factory()

    @property
    def buffered_count(self) -> int:
        """Number of writes waiting in the fail-safe memory buffer."""
        with self._lock:
            return len(self._buffer)

    def set_simulated_outage(self, down: bool) -> None:
        """Toggle a simulated DB outage (used by fail-safe tests)."""
        self._simulate_down = down

    def ping(self) -> bool:
        """Return ``True`` if the database is reachable, ``False`` otherwise."""
        if self._simulate_down:
            return False
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except (SQLAlchemyError, OSError):
            return False

    def flush_buffer(self) -> int:
        """Attempt to flush any buffered writes to the database."""
        if self._simulate_down:
            return 0
        with self._lock:
            items = list(self._buffer)
            self._buffer.clear()
        if not items:
            return 0

        flushed = 0
        for idx, (kind, payload) in enumerate(items):
            try:
                with self.session() as sess:
                    if kind == "assessment":
                        sess.add(AssessmentRecord(**payload))
                    elif kind == "challenge_create":
                        sess.add(ChallengeRecord(**payload))
                    elif kind == "challenge_complete":
                        stmt = (
                            update(ChallengeRecord)
                            .where(ChallengeRecord.id == payload["id"])
                            .values(
                                completed_at=payload["completed_at"],
                                outcome=payload["outcome"],
                            )
                        )
                        sess.execute(stmt)
                    sess.commit()
                flushed += 1
            except (SQLAlchemyError, OSError):
                # Put remaining items back in buffer
                with self._lock:
                    for rem in items[idx:]:
                        self._buffer.append(rem)
                break
        return flushed

    def record_assessment(
        self,
        *,
        assessment_id: str | None = None,
        session_hash: str,
        action: str,
        device_class: str | None = None,
        score: float,
        band: str,
        decision: str,
        rules_fired: list[str] | None = None,
        top_factors: list[str] | None = None,
        model_versions: dict[str, Any] | None = None,
        latency_ms: float | None = None,
        degraded: bool = False,
        derived_features: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> str:
        """Persist an assessment row, buffering in memory if the DB is unavailable."""
        rec_id = assessment_id or str(uuid.uuid4())
        ts = now or _utc_now()

        stored_features: dict[str, float] | None = None
        expires_at: datetime | None = None
        if self.store_features_in_db and derived_features is not None:
            stored_features = sanitize_derived_features(derived_features)
            if stored_features is not None:
                expires_at = ts + timedelta(seconds=self.feature_ttl_seconds)
        elif derived_features is not None:
            # Always validate even when feature storage is disabled
            _ = sanitize_derived_features(derived_features)

        payload: dict[str, Any] = {
            "id": rec_id,
            "ts": ts,
            "session_hash": session_hash,
            "action": action,
            "device_class": device_class,
            "score": float(score),
            "band": band,
            "decision": decision,
            "rules_fired": list(rules_fired or []),
            "top_factors": list(top_factors or []),
            "model_versions": dict(model_versions or {}),
            "latency_ms": float(latency_ms) if latency_ms is not None else None,
            "degraded": bool(degraded),
            "feedback": None,
            "features": stored_features,
            "features_expires_at": expires_at,
        }

        if self._simulate_down:
            with self._lock:
                self._buffer.append(("assessment", payload))
            return rec_id

        try:
            self.flush_buffer()
            with self.session() as sess:
                sess.add(AssessmentRecord(**payload))
                sess.commit()
        except (SQLAlchemyError, OSError):
            with self._lock:
                self._buffer.append(("assessment", payload))
        return rec_id

    def record_challenge_issued(
        self,
        *,
        challenge_id: str,
        assessment_id: str | None,
        challenge_type: str = "press_hold",
        now: datetime | None = None,
    ) -> str:
        """Persist a newly issued challenge row, buffering on DB outage."""
        payload: dict[str, Any] = {
            "id": challenge_id,
            "assessment_id": assessment_id,
            "type": challenge_type,
            "issued_at": now or _utc_now(),
            "completed_at": None,
            "outcome": None,
        }
        if self._simulate_down:
            with self._lock:
                self._buffer.append(("challenge_create", payload))
            return challenge_id

        try:
            self.flush_buffer()
            with self.session() as sess:
                sess.add(ChallengeRecord(**payload))
                sess.commit()
        except (SQLAlchemyError, OSError):
            with self._lock:
                self._buffer.append(("challenge_create", payload))
        return challenge_id

    def record_challenge_completed(
        self,
        *,
        challenge_id: str,
        outcome: str,
        now: datetime | None = None,
    ) -> None:
        """Update a challenge row with its completion timestamp and outcome."""
        payload: dict[str, Any] = {
            "id": challenge_id,
            "completed_at": now or _utc_now(),
            "outcome": outcome,
        }
        if self._simulate_down:
            with self._lock:
                self._buffer.append(("challenge_complete", payload))
            return

        try:
            self.flush_buffer()
            with self.session() as sess:
                stmt = (
                    update(ChallengeRecord)
                    .where(ChallengeRecord.id == challenge_id)
                    .values(
                        completed_at=payload["completed_at"],
                        outcome=outcome,
                    )
                )
                sess.execute(stmt)
                sess.commit()
        except (SQLAlchemyError, OSError):
            with self._lock:
                self._buffer.append(("challenge_complete", payload))

    def get_assessment(self, assessment_id: str) -> AssessmentRecord | None:
        """Fetch an :class:`AssessmentRecord` by ID."""
        with self.session() as sess:
            return sess.get(AssessmentRecord, assessment_id)

    def get_challenge(self, challenge_id: str) -> ChallengeRecord | None:
        """Fetch a :class:`ChallengeRecord` by ID."""
        with self.session() as sess:
            return sess.get(ChallengeRecord, challenge_id)

    def get_challenges_for_assessment(self, assessment_id: str) -> list[ChallengeRecord]:
        """Fetch all :class:`ChallengeRecord` rows associated with ``assessment_id``."""
        with self.session() as sess:
            stmt = (
                select(ChallengeRecord)
                .where(ChallengeRecord.assessment_id == assessment_id)
                .order_by(ChallengeRecord.issued_at.asc())
            )
            return list(sess.scalars(stmt))

    def set_feedback(
        self,
        assessment_id: str,
        feedback: str | None,
    ) -> AssessmentRecord | None:
        """Mark an assessment as false positive (``'fp'``), false negative (``'fn'``), or clear."""
        if feedback is not None and feedback not in ("fp", "fn"):
            raise ValueError(f"feedback must be 'fp', 'fn', or None; got {feedback!r}")
        with self.session() as sess:
            row = sess.get(AssessmentRecord, assessment_id)
            if row is None:
                return None
            row.feedback = feedback
            sess.commit()
            sess.refresh(row)
            return row

    def purge_expired_features(self, *, now: datetime | None = None) -> int:
        """Null out expired ``features`` blobs while retaining assessment rows."""
        cutoff = now or _utc_now()
        with self.session() as sess:
            rows = list(
                sess.scalars(
                    select(AssessmentRecord).where(
                        AssessmentRecord.features.is_not(None),
                        AssessmentRecord.features_expires_at.is_not(None),
                        AssessmentRecord.features_expires_at <= cutoff,
                    )
                )
            )
            for row in rows:
                row.features = None
                row.features_expires_at = None
            sess.commit()
            self.last_purge_at = cutoff
            self.last_features_purged = len(rows)
            return len(rows)

    def purge_expired_assessments(self, *, now: datetime | None = None) -> int:
        """Delete assessment rows (and linked challenges) older than ``assessment_ttl_seconds``."""
        cutoff = now or _utc_now()
        threshold = cutoff - timedelta(seconds=self.assessment_ttl_seconds)
        with self.session() as sess:
            rows = list(
                sess.scalars(select(AssessmentRecord).where(AssessmentRecord.ts <= threshold))
            )
            if rows:
                ids = [r.id for r in rows]
                chals = list(
                    sess.scalars(
                        select(ChallengeRecord).where(ChallengeRecord.assessment_id.in_(ids))
                    )
                )
                for c in chals:
                    sess.delete(c)
                for row in rows:
                    sess.delete(row)
                sess.commit()
            self.last_purge_at = cutoff
            self.last_assessments_purged = len(rows)
            return len(rows)

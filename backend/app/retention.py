"""Scheduled data-retention purge (P9-04).

Deletes stored feature JSON older than ``FEATURE_TTL_SECONDS`` (default 7 days)
and deletes (anonymises by removal) assessment rows older than
``ASSESSMENT_TTL_SECONDS`` (default 30 days).

A purge can be triggered:
- immediately via :func:`run_retention_purge` (admin ``POST /admin/privacy/purge``)
- on a cron-like interval by :class:`RetentionScheduler` (FastAPI lifespan)
- from the CLI: ``python -m app.retention --once``
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, TextIO

from app.config import Settings, load_settings
from app.db import DatabaseManager


class Clock(Protocol):
    """Injectable clock so retention tests can freeze and advance time."""

    def now(self) -> datetime:
        """Return the current UTC instant used for TTL comparisons."""
        ...


class SystemClock:
    """Wall-clock UTC time."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    """Deterministic clock for unit tests."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        self._instant = instant

    def now(self) -> datetime:
        return self._instant

    def set(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        self._instant = instant

    def advance(self, delta: timedelta) -> None:
        self._instant = self._instant + delta


@dataclass(frozen=True)
class PurgeResult:
    """Counts from a single retention pass."""

    purged_at: datetime
    features_purged: int
    assessments_purged: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "purged_at": self.purged_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "features_purged": self.features_purged,
            "assessments_purged": self.assessments_purged,
        }


def run_retention_purge(
    db: DatabaseManager,
    *,
    clock: Clock | None = None,
    now: datetime | None = None,
    flush: bool = True,
) -> PurgeResult:
    """Flush the write buffer, then purge expired features and assessments.

    Feature blobs whose ``features_expires_at`` is at or before ``now`` are
    nulled. Assessment rows whose ``ts`` is older than
    ``db.assessment_ttl_seconds`` are deleted together with linked challenges
    (the long-term TTL path; identifiers are removed rather than retained in
    anonymised form).
    """
    instant = now if now is not None else (clock or SystemClock()).now()
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    if flush:
        db.flush_buffer()
    features_purged = db.purge_expired_features(now=instant)
    assessments_purged = db.purge_expired_assessments(now=instant)
    return PurgeResult(
        purged_at=instant,
        features_purged=features_purged,
        assessments_purged=assessments_purged,
    )


class RetentionScheduler:
    """Cron-like background loop that periodically runs :func:`run_retention_purge`."""

    def __init__(
        self,
        db: DatabaseManager,
        *,
        clock: Clock | None = None,
        interval_seconds: int = 3600,
        wait_fn: Callable[[threading.Event, float], bool] | None = None,
    ) -> None:
        if interval_seconds < 0:
            raise ValueError("interval_seconds must be >= 0")
        self.db = db
        self.clock: Clock = clock or SystemClock()
        self.interval_seconds = interval_seconds
        self._wait = wait_fn or (lambda event, timeout: event.wait(timeout))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_result: PurgeResult | None = None

    def run_once(self) -> PurgeResult:
        """Execute one purge at ``clock.now()``."""
        result = run_retention_purge(self.db, clock=self.clock)
        self.last_result = result
        return result

    def start(self) -> None:
        """Start the daemon loop. No-op when ``interval_seconds`` is 0 or already running."""
        if self.interval_seconds <= 0 or (self._thread is not None and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="botguard-retention",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout: float = 2.0) -> None:
        """Signal the loop to exit and join the worker thread."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.run_once()
            if self._wait(self._stop, float(self.interval_seconds)):
                break


def build_database(settings: Settings) -> DatabaseManager:
    """Construct a :class:`DatabaseManager` from application settings."""
    return DatabaseManager(
        settings.database_url,
        store_features_in_db=settings.store_features_in_db,
        feature_ttl_seconds=settings.feature_ttl_seconds,
        assessment_ttl_seconds=settings.assessment_ttl_seconds,
    )


def main(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    db: DatabaseManager | None = None,
    clock: Clock | None = None,
) -> int:
    """CLI entry: ``python -m app.retention --once``."""
    parser = argparse.ArgumentParser(
        prog="python -m app.retention",
        description="Run the BotGuard feature/assessment retention purge.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=True,
        help="Run a single purge and exit (the only CLI mode; scheduling is the API lifespan).",
    )
    parser.parse_args(argv)
    out = stdout if stdout is not None else sys.stdout
    settings = load_settings()
    manager = db if db is not None else build_database(settings)
    result = run_retention_purge(manager, clock=clock)
    out.write(json.dumps(result.as_dict()) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Unit and integration tests for rotating session identifiers and IP coarsening (P9-05).

Verifies:
1. Session identifiers are random per page load and rotate on demand.
2. Session hashes (`make_session_hash`) have zero cross-day linkage across UTC day boundaries.
3. IP addresses are stored only as coarse `/24` (IPv4) or `/48` (IPv6) buckets in logs and
   are never persisted raw in `assessments` or structured log lines.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_api import (
    HUMAN_MOUSE_POINTS,
    _AsgiTestClient,
    _clean_desktop_env,
    _make_human_key_events,
)

from app.config import load_settings
from app.main import app as default_app
from app.main import create_app, format_safe_log_record
from app.nonce import (
    _coarsen_ip,
    daily_session_salt,
    generate_session_id,
    make_session_hash,
)
from app.store import InMemoryStore


def _human_payload(nonce: str, action: str = "login") -> dict[str, object]:
    return {
        "nonce": nonce,
        "action": action,
        "sdk_version": "1.0.0",
        "schema_version": 1,
        "env": _clean_desktop_env().model_dump(),
        "behaviour": {
            "device_class": "desktop",
            "mouse": {"points": HUMAN_MOUSE_POINTS, "clicks": [[767.0, 267.0, 830.0, 910.0]]},
            "keys": {"events": _make_human_key_events()},
            "timing": {
                "ms_since_load": 1500.0,
                "ms_to_first_interaction": 190.0,
                "ms_since_nonce": 800.0,
            },
        },
    }


def _build_client(tmp_path: Path) -> tuple[_AsgiTestClient, object]:
    db_file = tmp_path / "session_privacy_test.db"
    settings = dataclasses.replace(
        load_settings(),
        jwt_secret="session-privacy-test-secret-key-32bytes!",
        database_url=f"sqlite:///{db_file.as_posix()}",
        store_features_in_db=True,
        retention_purge_interval_seconds=0,
    )
    app = create_app(
        settings=settings,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
    )
    return _AsgiTestClient(app), app


def test_random_session_id_and_per_page_load_rotation() -> None:
    """Every page load / rotation produces a distinct 128-bit random session token and hash."""
    tokens = {generate_session_id() for _ in range(50)}
    assert len(tokens) == 50
    for tok in tokens:
        assert len(tok) == 32
        assert all(c in "0123456789abcdef" for c in tok)

    fixed_now = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
    # Without a client_session_id, every call generates a fresh ephemeral session hash
    anon_hashes = {
        make_session_hash("203.0.113.42", "Mozilla/5.0", now=fixed_now, secret="s")
        for _ in range(20)
    }
    assert len(anon_hashes) == 20

    # With explicit per-page-load client_session_id values, each page load gets a distinct hash
    h_page_1 = make_session_hash(
        "203.0.113.42",
        "Mozilla/5.0",
        client_session_id="page-load-1",
        now=fixed_now,
        secret="s",
    )
    h_page_2 = make_session_hash(
        "203.0.113.42",
        "Mozilla/5.0",
        client_session_id="page-load-2",
        now=fixed_now,
        secret="s",
    )
    assert h_page_1 != h_page_2
    assert len(h_page_1) == 16


def test_no_cross_day_session_linkage() -> None:
    """Identical IP, UA, and client_session_id across UTC day boundaries cannot be linked."""
    day_1_late = datetime(2026, 11, 14, 23, 59, 59, tzinfo=UTC)
    day_1_earlier = datetime(2026, 11, 14, 8, 15, 0, tzinfo=UTC)
    day_2_early = datetime(2026, 11, 15, 0, 0, 1, tzinfo=UTC)

    assert daily_session_salt(day_1_earlier, secret="k") == daily_session_salt(
        day_1_late, secret="k"
    )
    assert daily_session_salt(day_1_late, secret="k") != daily_session_salt(day_2_early, secret="k")

    h_day1_a = make_session_hash(
        "198.51.100.77",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        client_session_id="persistent-attempt-token",
        now=day_1_earlier,
        secret="k",
    )
    h_day1_b = make_session_hash(
        "198.51.100.77",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        client_session_id="persistent-attempt-token",
        now=day_1_late,
        secret="k",
    )
    h_day2 = make_session_hash(
        "198.51.100.77",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        client_session_id="persistent-attempt-token",
        now=day_2_early,
        secret="k",
    )

    # Same UTC day + same page-load session ID -> consistent within the day
    assert h_day1_a == h_day1_b
    # Next UTC day -> completely different hash (zero cross-day linkage)
    assert h_day1_b != h_day2


def test_assess_endpoint_rotates_session_hash_per_page_and_across_days(
    tmp_path: Path,
) -> None:
    """POST /v1/assess stores rotating session_hash with no cross-day linkage or raw IP."""
    client, app = _build_client(tmp_path)
    raw_ip = "203.0.113.199"
    headers_base = {
        "X-Forwarded-For": raw_ip,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
    }

    # Day 1, page load A
    app.state.session_clock = lambda: datetime(2026, 11, 14, 14, 0, 0, tzinfo=UTC)  # type: ignore[attr-defined]
    n1 = client.get("/v1/nonce", headers=headers_base).json()["nonce"]
    r1 = client.post(
        "/v1/assess",
        json=_human_payload(n1),
        headers={**headers_base, "X-Session-Id": "sess-page-a"},
    )
    assert r1.status_code == 200
    id1 = r1.json()["request_id"]

    # Day 1, page load B (rotated X-Session-Id)
    n2 = client.get("/v1/nonce", headers=headers_base).json()["nonce"]
    r2 = client.post(
        "/v1/assess",
        json=_human_payload(n2),
        headers={**headers_base, "X-Session-Id": "sess-page-b"},
    )
    assert r2.status_code == 200
    id2 = r2.json()["request_id"]

    # Day 2, even if caller reuses "sess-page-a"
    app.state.session_clock = lambda: datetime(2026, 11, 15, 9, 0, 0, tzinfo=UTC)  # type: ignore[attr-defined]
    n3 = client.get("/v1/nonce", headers=headers_base).json()["nonce"]
    r3 = client.post(
        "/v1/assess",
        json=_human_payload(n3),
        headers={**headers_base, "X-Session-Id": "sess-page-a"},
    )
    assert r3.status_code == 200
    id3 = r3.json()["request_id"]

    db = app.state.db  # type: ignore[attr-defined]
    rec1 = db.get_assessment(id1)
    rec2 = db.get_assessment(id2)
    rec3 = db.get_assessment(id3)
    assert rec1 is not None and rec2 is not None and rec3 is not None

    # All three assessments must have distinct session hashes
    assert rec1.session_hash != rec2.session_hash
    assert rec1.session_hash != rec3.session_hash
    assert rec2.session_hash != rec3.session_hash

    # Neither raw IP nor raw X-Session-Id appears anywhere in the stored records
    serialized = json.dumps(
        [{k: v for k, v in vars(r).items() if not k.startswith("_")} for r in (rec1, rec2, rec3)],
        default=str,
    )
    assert raw_ip not in serialized
    assert "sess-page-a" not in serialized
    assert "sess-page-b" not in serialized


def test_ip_stored_only_as_coarse_bucket_in_logs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Structured logs contain only /24 or /48 coarse IP buckets and never raw IPs."""
    assert _coarsen_ip("203.0.113.199") == "203.0.113.0/24"
    assert _coarsen_ip("2001:db8:abcd:1234:5678::1") == "2001:db8:abcd::/48"
    assert _coarsen_ip("not-an-ip-address") == "unknown"

    rec = format_safe_log_record(
        "assessment_completed",
        request_id="req-99",
        client_ip="198.51.100.234",
        session_id="secret-session-token",
        x_session_id="secret-header-token",
        ip="198.51.100.234",
        decision="allow",
    )
    assert rec["ip_bucket"] == "198.51.100.0/24"
    assert "198.51.100.234" not in json.dumps(rec)
    assert "secret-session-token" not in json.dumps(rec)
    assert "secret-header-token" not in json.dumps(rec)

    client, _ = _build_client(tmp_path)
    with caplog.at_level(logging.INFO, logger="botguard.api"):
        headers = {
            "X-Forwarded-For": "198.51.100.234",
            "User-Agent": "Mozilla/5.0",
            "X-Session-Id": "ephemeral-page-session-xyz",
        }
        nonce = client.get("/v1/nonce", headers=headers).json()["nonce"]
        resp = client.post("/v1/assess", json=_human_payload(nonce), headers=headers)
        assert resp.status_code == 200

    assert len(caplog.records) >= 2
    for log_rec in caplog.records:
        msg = log_rec.getMessage()
        assert "198.51.100.234" not in msg
        assert "ephemeral-page-session-xyz" not in msg
        parsed = json.loads(msg)
        assert parsed.get("ip_bucket") == "198.51.100.0/24"

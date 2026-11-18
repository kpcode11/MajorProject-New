"""Automated privacy regression scan across E2E flows, DB tables, and logs (P9-06).

Verifies that after executing a full suite of end-to-end portal and scoring flows
(OTP request, demographic details update with step-up challenge, centre search,
bot rejection, form-value injection attempts, and admin inspection):
1. No database table column or cell contains typed characters, form values,
   full IP addresses, raw User-Agents, raw behavioural traces, or persistent
   device identifiers.
2. No structured log line contains typed characters, form values, full IPs,
   nonces, JWTs, raw session IDs, or persistent device identifiers.
3. Schema validation and persistence guards actively reject raw key identities,
   raw form values on portal endpoints, and raw trace keys.
"""

from __future__ import annotations

import dataclasses
import ipaddress
import json
import logging
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, text
from test_api import (
    HUMAN_MOUSE_POINTS,
    _AsgiTestClient,
    _clean_desktop_env,
    _make_bot_key_events,
    _make_bot_mouse_points,
    _make_human_key_events,
)

from app.config import load_settings
from app.db import DatabaseManager, sanitize_derived_features
from app.main import app as default_app
from app.main import create_app
from app.portal import PortalStatsTracker, create_portal_router
from app.schemas import KeyBehaviour, KeyEvent
from app.store import InMemoryStore

# Synthetic canary secrets that simulate user-typed text, form values, full IPs,
# and persistent device identifiers. None of these strings may ever appear in
# any database column or log line.
CANARY_TYPED_SECRETS: tuple[str, ...] = (
    "CANARY_SECRET_UID_999988887777",
    "CANARY_PASS_Hunter42!",
    "CANARY_NAME_Ramesh_Kumar",
    "CANARY_ADDR_42_MG_Road_Bengaluru",
    "ramesh.kumar@example.in",
    "9876543210",
    "CANARY_DEVICE_FINGERPRINT_SHA256_DEADBEEF",
    "CANARY_CANVAS_HASH_8f9e7d6c5b4a",
    "CANARY_WEBGL_UNMASKED_NVIDIA_RTX_4090_SERIAL",
)

CANARY_FULL_IPS: tuple[str, ...] = (
    "203.0.113.77",
    "198.51.100.44",
    "192.0.2.188",
    "2001:db8:abcd:1234:5678::99",
)

CANARY_SESSION_IDS: tuple[str, ...] = (
    "ephemeral-sess-otp-001",
    "ephemeral-sess-details-002",
    "ephemeral-sess-search-003",
    "ephemeral-sess-bot-004",
)

CANARY_USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.6422.112",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
)

FORBIDDEN_DB_COLUMNS: frozenset[str] = frozenset(
    {
        "ip",
        "client_ip",
        "raw_ip",
        "remote_addr",
        "user_agent",
        "ua_raw",
        "points",
        "events",
        "gestures",
        "clicks",
        "keystrokes",
        "raw_trace",
        "text",
        "key",
        "char",
        "typed_text",
        "password",
        "identifier",
        "phone",
        "email",
        "full_name",
        "address",
        "device_id",
        "fingerprint",
        "canvas_hash",
        "webgl_hash",
        "audio_hash",
    }
)

FORBIDDEN_LOG_KEYS: frozenset[str] = frozenset(
    {
        "ip",
        "client_ip",
        "raw_ip",
        "nonce",
        "token",
        "jwt",
        "env",
        "behaviour",
        "points",
        "events",
        "gestures",
        "clicks",
        "payload",
        "body",
        "user_agent",
        "session_id",
        "x_session_id",
        "device_id",
        "fingerprint",
        "canvas_hash",
        "webgl_hash",
    }
)

_IPV4_CANDIDATE_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")


def _build_e2e_scan_client(
    tmp_path: Path,
    *,
    admin_key: str = "privacy-scan-admin-key",
) -> tuple[_AsgiTestClient, DatabaseManager]:
    base_cfg = load_settings()
    cfg = dataclasses.replace(
        base_cfg,
        database_url=f"sqlite:///{(tmp_path / 'privacy_scan.db').as_posix()}",
        jwt_secret="privacy-scan-jwt-secret-key-at-least-32-bytes!",
        admin_api_key=admin_key,
        store_features_in_db=True,
        feature_ttl_seconds=604800,
        assessment_ttl_seconds=2592000,
        retention_purge_interval_seconds=0,
    )
    db = DatabaseManager(
        cfg.database_url,
        store_features_in_db=True,
        feature_ttl_seconds=cfg.feature_ttl_seconds,
        assessment_ttl_seconds=cfg.assessment_ttl_seconds,
    )
    app = create_app(
        settings=cfg,
        store=InMemoryStore(),
        scorer=default_app.state.scorer,
        db=db,
    )
    app.state.portal_stats = PortalStatsTracker()
    app.include_router(create_portal_router())
    return _AsgiTestClient(app), db


def _assert_no_unmasked_ip_in_text(text_blob: str) -> None:
    """Verify that any IPv4 literal in `text_blob` is a coarse `/24` network prefix."""
    for match in _IPV4_CANDIDATE_RE.findall(text_blob):
        if "/" in match:
            net = ipaddress.ip_network(match, strict=False)
            assert net.prefixlen <= 24, f"IPv4 prefix finer than /24 found: {match}"
            assert str(net) == match, f"Host bits set in IPv4 network prefix: {match}"
        else:
            # Skip version strings like "1.0.0.0" only if not a valid public/test IP,
            # but none of our model versions use 4-octet dotted quads.
            raise AssertionError(f"Unmasked raw IPv4 address found: {match}")


def _collect_json_keys(obj: Any, out: set[str] | None = None) -> set[str]:
    if out is None:
        out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k).lower())
            _collect_json_keys(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_json_keys(item, out)
    return out


def test_privacy_regression_scan_over_e2e_flows(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Run E2E portal + challenge + bot flows and scan all DB tables and log lines."""
    admin_key = "privacy-scan-admin-key"
    client, db = _build_e2e_scan_client(tmp_path, admin_key=admin_key)

    issued_nonces: list[str] = []
    issued_tokens: list[str] = []

    with caplog.at_level(logging.INFO, logger="botguard.api"):
        # ------------------------------------------------------------------
        # 1. Human Login + OTP Request + Challenge Flow (IPv4)
        # ------------------------------------------------------------------
        hdr_otp = {
            "X-Forwarded-For": CANARY_FULL_IPS[0],
            "User-Agent": CANARY_USER_AGENTS[0],
            "X-Session-Id": CANARY_SESSION_IDS[0],
        }
        nonce_login = client.get("/v1/nonce", headers=hdr_otp).json()["nonce"]
        issued_nonces.append(nonce_login)
        assess_login = client.post(
            "/v1/assess",
            headers=hdr_otp,
            json={
                "nonce": nonce_login,
                "action": "login",
                "env": _clean_desktop_env().model_dump(exclude_none=True),
                "behaviour": {
                    "device_class": "desktop",
                    "mouse": {"points": HUMAN_MOUSE_POINTS},
                    "keys": {"events": _make_human_key_events()},
                },
            },
        )
        assert assess_login.status_code == 200
        assert assess_login.json()["decision"] == "allow"
        issued_tokens.append(assess_login.json()["token"])

        nonce_1 = client.get("/v1/nonce", headers=hdr_otp).json()["nonce"]
        issued_nonces.append(nonce_1)
        assess_1 = client.post(
            "/v1/assess",
            headers=hdr_otp,
            json={
                "nonce": nonce_1,
                "action": "otp_request",
                "env": _clean_desktop_env().model_dump(exclude_none=True),
                "behaviour": {
                    "device_class": "desktop",
                    "mouse": {"points": HUMAN_MOUSE_POINTS},
                    "keys": {"events": _make_human_key_events()},
                },
            },
        )
        assert assess_1.status_code == 200
        body_1 = assess_1.json()
        otp_token: str | None = body_1.get("token")
        if body_1["decision"] == "challenge" and body_1["challenge"] is not None:
            chal_1 = body_1["challenge"]
            nonce_1c = client.get("/v1/nonce", headers=hdr_otp).json()["nonce"]
            issued_nonces.append(nonce_1c)
            chal_1_res = client.post(
                "/v1/assess/challenge",
                headers=hdr_otp,
                json={
                    "nonce": nonce_1c,
                    "challenge_id": chal_1["id"],
                    "action": "otp_request",
                    "sdk_version": "1.0.0",
                    "hold_start_ms": 100.0,
                    "hold_end_ms": 100.0 + float(chal_1["hold_ms"]),
                    "env": _clean_desktop_env().model_dump(exclude_none=True),
                    "behaviour": {
                        "device_class": "desktop",
                        "mouse": {"points": HUMAN_MOUSE_POINTS},
                        "keys": {"events": _make_human_key_events()},
                    },
                },
            )
            assert chal_1_res.status_code == 200
            otp_token = chal_1_res.json()["token"]
        assert otp_token is not None
        issued_tokens.append(otp_token)

        otp_ok = client.post(
            "/portal-api/otp/request",
            headers={**hdr_otp, "X-Human-Token": otp_token},
            json={"action": "otp_request", "identifier_length": 12},
        )
        assert otp_ok.status_code == 200

        # Attempt to send raw typed form values to /portal-api/otp/request -> must 422
        from app.tokens import issue_token

        tok_1b = issue_token(
            client.app.state.store,
            client.app.state.settings,
            action="otp_request",
            band="low",
        )
        issued_tokens.append(tok_1b)

        otp_bad = client.post(
            "/portal-api/otp/request",
            headers={**hdr_otp, "X-Human-Token": tok_1b},
            json={
                "action": "otp_request",
                "identifier_length": 12,
                "identifier": CANARY_TYPED_SECRETS[0],
                "password": CANARY_TYPED_SECRETS[1],
                "email": CANARY_TYPED_SECRETS[4],
                "phone": CANARY_TYPED_SECRETS[5],
            },
        )
        assert otp_bad.status_code == 422

        # ------------------------------------------------------------------
        # 2. Step-Up Challenge + Details Update Flow (IPv6)
        # ------------------------------------------------------------------
        hdr_chal = {
            "X-Forwarded-For": CANARY_FULL_IPS[3],
            "User-Agent": CANARY_USER_AGENTS[1],
            "X-Session-Id": CANARY_SESSION_IDS[1],
        }
        nonce_2 = client.get("/v1/nonce", headers=hdr_chal).json()["nonce"]
        issued_nonces.append(nonce_2)

        assess_2 = client.post(
            "/v1/assess",
            headers=hdr_chal,
            json={
                "nonce": nonce_2,
                "action": "details_update",
                "sdk_version": "1.0.0",
                "schema_version": 1,
                "env": _clean_desktop_env().model_dump(exclude_none=True),
                "behaviour": {
                    "device_class": "desktop",
                    "mouse": {"points": HUMAN_MOUSE_POINTS[:6], "untrusted_count": 2},
                    "keys": {"events": _make_human_key_events()[:5]},
                    "timing": {"ms_since_load": 400.0, "ms_to_first_interaction": 50.0},
                },
            },
        )
        assert assess_2.status_code == 200
        body_2 = assess_2.json()
        if body_2["decision"] == "challenge" and body_2["challenge"] is not None:
            chal_id = body_2["challenge"]["id"]
            hold_ms = body_2["challenge"]["hold_ms"]
            nonce_2c = client.get("/v1/nonce", headers=hdr_chal).json()["nonce"]
            issued_nonces.append(nonce_2c)
            chal_res = client.post(
                "/v1/assess/challenge",
                headers=hdr_chal,
                json={
                    "nonce": nonce_2c,
                    "challenge_id": chal_id,
                    "action": "details_update",
                    "sdk_version": "1.0.0",
                    "hold_start_ms": 100.0,
                    "hold_end_ms": 100.0 + float(hold_ms),
                    "env": _clean_desktop_env().model_dump(exclude_none=True),
                    "behaviour": {
                        "device_class": "desktop",
                        "mouse": {"points": HUMAN_MOUSE_POINTS},
                        "keys": {"events": _make_human_key_events()},
                    },
                },
            )
            assert chal_res.status_code == 200
            if chal_res.json().get("token"):
                issued_tokens.append(chal_res.json()["token"])

        # Attempt to send raw personal details to /portal-api/details/update -> must 422
        tok_2d = issue_token(
            client.app.state.store,
            client.app.state.settings,
            action="details_update",
            band="low",
        )
        issued_tokens.append(tok_2d)

        details_bad = client.post(
            "/portal-api/details/update",
            headers={**hdr_chal, "X-Human-Token": tok_2d},
            json={
                "action": "details_update",
                "fields_updated": ["name", "address"],
                "full_name": CANARY_TYPED_SECRETS[2],
                "address": CANARY_TYPED_SECRETS[3],
                "device_id": CANARY_TYPED_SECRETS[6],
            },
        )
        assert details_bad.status_code == 422

        # ------------------------------------------------------------------
        # 3. Centre Search & Bot Rejection Flow
        # ------------------------------------------------------------------
        hdr_bot = {
            "X-Forwarded-For": CANARY_FULL_IPS[1],
            "User-Agent": "HeadlessChrome/120.0",
            "X-Session-Id": CANARY_SESSION_IDS[3],
        }
        nonce_3 = client.get("/v1/nonce", headers=hdr_bot).json()["nonce"]
        issued_nonces.append(nonce_3)
        bot_env = _clean_desktop_env().model_dump()
        bot_env["webdriver"] = True
        assess_3 = client.post(
            "/v1/assess",
            headers=hdr_bot,
            json={
                "nonce": nonce_3,
                "action": "centre_search",
                "sdk_version": "1.0.0",
                "schema_version": 1,
                "env": bot_env,
                "behaviour": {
                    "device_class": "desktop",
                    "mouse": {"points": _make_bot_mouse_points()},
                    "keys": {"events": _make_bot_key_events()},
                },
            },
        )
        assert assess_3.status_code == 200
        id_bot = assess_3.json()["request_id"]

        # Mark feedback via Admin API
        fb_resp = client.post(
            "/admin/feedback",
            headers={"X-Admin-Key": admin_key},
            json={"assessment_id": id_bot, "feedback": "fn"},
        )
        assert fb_resp.status_code == 200

    # ======================================================================
    # SCAN 1: Inspect every database table, column name, and cell value
    # ======================================================================
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    assert "assessments" in table_names
    assert "challenges" in table_names

    total_rows_scanned = 0
    with db.engine.connect() as conn:
        for table in table_names:
            columns = [col["name"] for col in inspector.get_columns(table)]
            for col_name in columns:
                assert col_name.lower() not in FORBIDDEN_DB_COLUMNS, (
                    f"Table {table!r} has prohibited column {col_name!r}"
                )

            rows = conn.execute(text(f"SELECT * FROM {table}")).mappings().all()  # noqa: S608
            for row in rows:
                total_rows_scanned += 1
                row_dict = dict(row)
                serialized_row = json.dumps(row_dict, default=str)

                # 1a. No canary typed text, form values, or device IDs
                for secret in CANARY_TYPED_SECRETS:
                    assert secret not in serialized_row, (
                        f"Canary secret {secret!r} leaked into {table}"
                    )
                # 1b. No full IPv4 or IPv6 addresses
                for full_ip in CANARY_FULL_IPS:
                    assert full_ip not in serialized_row, f"Full IP {full_ip!r} leaked into {table}"
                _assert_no_unmasked_ip_in_text(serialized_row)

                # 1c. No raw X-Session-Id or raw User-Agent strings
                for sess_id in CANARY_SESSION_IDS:
                    assert sess_id not in serialized_row, (
                        f"Raw session ID {sess_id!r} leaked into {table}"
                    )
                for ua_str in CANARY_USER_AGENTS:
                    assert ua_str not in serialized_row, f"Raw User-Agent leaked into {table}"

                # 1d. If table is assessments, verify session_hash and derived features
                if table == "assessments":
                    sh = str(row_dict["session_hash"])
                    assert re.fullmatch(r"[0-9a-f]{16}", sh), (
                        f"session_hash must be a 16-hex-char digest, got {sh!r}"
                    )
                    feats_raw = row_dict.get("features")
                    if feats_raw is not None:
                        feats = json.loads(feats_raw) if isinstance(feats_raw, str) else feats_raw
                        assert isinstance(feats, dict)
                        for fk, fv in feats.items():
                            assert str(fk).lower() not in FORBIDDEN_DB_COLUMNS
                            assert isinstance(fv, (int, float)) and not isinstance(fv, bool), (
                                f"Feature {fk!r} is non-numeric: {fv!r}"
                            )

    assert total_rows_scanned >= 4

    # ======================================================================
    # SCAN 2: Inspect every captured structured log line
    # ======================================================================
    assert len(caplog.records) >= 6
    for rec in caplog.records:
        line = rec.getMessage()
        parsed = json.loads(line)
        all_keys = _collect_json_keys(parsed)

        # 2a. No forbidden keys at any nesting depth
        leaked_keys = all_keys & FORBIDDEN_LOG_KEYS
        assert not leaked_keys, f"Forbidden keys in log line: {leaked_keys}"

        # 2b. No canary typed characters, form values, full IPs, session IDs, nonces, or JWTs
        for secret in CANARY_TYPED_SECRETS:
            assert secret not in line
        for full_ip in CANARY_FULL_IPS:
            assert full_ip not in line
        for sess_id in CANARY_SESSION_IDS:
            assert sess_id not in line
        for ua_str in CANARY_USER_AGENTS:
            assert ua_str not in line
        for nonce_val in issued_nonces:
            assert nonce_val not in line
        for tok_val in issued_tokens:
            assert tok_val not in line

        # 2c. ip_bucket is strictly a coarse /24 or /48 network prefix
        if "ip_bucket" in parsed:
            bucket = parsed["ip_bucket"]
            assert bucket.endswith("/24") or bucket.endswith("/48") or bucket == "unknown"
            _assert_no_unmasked_ip_in_text(bucket)


def test_schema_and_db_reject_typed_chars_and_raw_traces() -> None:
    """Verify schema and DB guards reject raw typed characters and raw trace arrays."""
    # Raw characters ('a', '9', 'Enter', '@') must be rejected by KeyEvent / KeyBehaviour
    for raw_key in ("a", "Z", "9", "Enter", "Backspace", "@", "KeyA", "password123"):
        with pytest.raises(ValidationError):
            KeyEvent(key_class=raw_key, down_ms=10.0, up_ms=80.0)
        with pytest.raises(ValidationError):
            KeyBehaviour(events=[[raw_key, 10.0, 80.0]])

    # Coarse key_class values are accepted
    valid_kb = KeyBehaviour(
        events=[["letter", 10.0, 80.0], ["digit", 120.0, 190.0], ["backspace", 210.0, 260.0]]
    )
    assert len(valid_kb.events) == 3

    # sanitize_derived_features rejects any prohibited raw trace or text key
    for bad_key in ("points", "events", "gestures", "clicks", "keystrokes", "text", "key"):
        with pytest.raises(ValueError, match="prohibited raw trace key"):
            sanitize_derived_features({bad_key: 1.0})

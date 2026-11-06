"""Tests for human verification JWT issuance and single-use verification (P5-06)."""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path

import jwt
import pytest

from app.config import Settings, load_settings
from app.store import InMemoryStore
from app.tokens import (
    TokenClaims,
    TokenError,
    issue_token,
    verify_token,
    verify_token_response,
    write_keypair_files,
)


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def hs256_settings() -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        jwt_secret="super-secret-hs256-key-at-least-32-bytes-long",
        jwt_algorithm="HS256",
        jwt_issuer="botguard",
        jwt_audience="botguard-portal",
        jwt_expire_seconds=90,
    )


class TestTokenIssuanceAndVerification:
    def test_hs256_issue_and_verify_roundtrip(
        self, store: InMemoryStore, hs256_settings: Settings
    ) -> None:
        token = issue_token(store, hs256_settings, action="otp_request", band="low")
        claims: TokenClaims = verify_token(
            store, hs256_settings, token, expected_action="otp_request"
        )

        assert claims.iss == "botguard"
        assert claims.aud == "botguard-portal"
        assert claims.act == "otp_request"
        assert claims.band == "low"
        assert claims.exp == pytest.approx(claims.iat + 90.0, abs=1.0)
        assert len(claims.jti) >= 16

    def test_rs256_key_files_roundtrip(
        self, store: InMemoryStore, hs256_settings: Settings, tmp_path: Path
    ) -> None:
        priv_path, pub_path = write_keypair_files(tmp_path, algorithm="RS256")
        rs_settings = dataclasses.replace(
            hs256_settings,
            jwt_algorithm="RS256",
            jwt_private_key_file=str(priv_path),
            jwt_public_key_file=str(pub_path),
        )
        token = issue_token(store, rs_settings, action="login", band="medium", ttl=60)
        claims = verify_token(store, rs_settings, token, expected_action="login")
        assert claims.act == "login"
        assert claims.band == "medium"

    def test_es256_key_files_roundtrip(
        self, store: InMemoryStore, hs256_settings: Settings, tmp_path: Path
    ) -> None:
        priv_path, pub_path = write_keypair_files(tmp_path, algorithm="ES256")
        es_settings = dataclasses.replace(
            hs256_settings,
            jwt_algorithm="ES256",
            jwt_private_key_file=str(priv_path),
            jwt_public_key_file=str(pub_path),
        )
        token = issue_token(store, es_settings, action="details_update", band="low", ttl=120)
        claims = verify_token(store, es_settings, token, expected_action="details_update")
        assert claims.act == "details_update"
        assert claims.band == "low"


class TestSingleUseJtiAndReplayPrevention:
    def test_jti_single_use_rejects_second_verification(
        self, store: InMemoryStore, hs256_settings: Settings
    ) -> None:
        token = issue_token(store, hs256_settings, action="otp_request", band="low")
        first = verify_token(store, hs256_settings, token)
        assert first.act == "otp_request"

        with pytest.raises(TokenError) as exc_info:
            verify_token(store, hs256_settings, token)
        assert exc_info.value.code == "token_replayed_or_revoked"

    def test_non_consuming_verify_allows_subsequent_consume(
        self, store: InMemoryStore, hs256_settings: Settings
    ) -> None:
        token = issue_token(store, hs256_settings, action="centre_search", band="low")
        peek = verify_token(store, hs256_settings, token, consume=False)
        assert peek.act == "centre_search"
        consumed = verify_token(store, hs256_settings, token, consume=True)
        assert consumed.jti == peek.jti

        with pytest.raises(TokenError) as exc_info:
            verify_token(store, hs256_settings, token)
        assert exc_info.value.code == "token_replayed_or_revoked"


class TestSecurityAndValidationFailures:
    def test_expired_token_rejected(self, store: InMemoryStore, hs256_settings: Settings) -> None:
        past = time.time() - 300.0
        token = issue_token(
            store, hs256_settings, action="otp_request", band="low", ttl=60, now=past
        )
        with pytest.raises(TokenError) as exc_info:
            verify_token(store, hs256_settings, token)
        assert exc_info.value.code == "token_expired"

    def test_wrong_action_rejected(self, store: InMemoryStore, hs256_settings: Settings) -> None:
        token = issue_token(store, hs256_settings, action="centre_search", band="low")
        with pytest.raises(TokenError) as exc_info:
            verify_token(store, hs256_settings, token, expected_action="otp_request")
        assert exc_info.value.code == "action_mismatch"

    def test_bad_signature_rejected(self, store: InMemoryStore, hs256_settings: Settings) -> None:
        token = issue_token(store, hs256_settings, action="otp_request", band="low")
        other_settings = dataclasses.replace(
            hs256_settings,
            jwt_secret="different-secret-key-at-least-32-bytes-long-xyz",
        )
        with pytest.raises(TokenError) as exc_info:
            verify_token(store, other_settings, token)
        assert exc_info.value.code == "invalid_signature"

    def test_algorithm_mismatch_rejected(
        self, store: InMemoryStore, hs256_settings: Settings, tmp_path: Path
    ) -> None:
        priv_path, pub_path = write_keypair_files(tmp_path, algorithm="RS256")
        rs_settings = dataclasses.replace(
            hs256_settings,
            jwt_algorithm="RS256",
            jwt_private_key_file=str(priv_path),
            jwt_public_key_file=str(pub_path),
        )
        hs_token = issue_token(store, hs256_settings, action="otp_request", band="low")
        with pytest.raises(TokenError) as exc_info:
            verify_token(store, rs_settings, hs_token)
        assert exc_info.value.code == "invalid_algorithm"

    def test_missing_required_claim_rejected(
        self, store: InMemoryStore, hs256_settings: Settings
    ) -> None:
        incomplete_payload = {
            "iss": hs256_settings.jwt_issuer,
            "aud": hs256_settings.jwt_audience,
            "iat": time.time(),
            "exp": time.time() + 90.0,
        }
        forged = jwt.encode(incomplete_payload, hs256_settings.jwt_secret, algorithm="HS256")
        with pytest.raises(TokenError) as exc_info:
            verify_token(store, hs256_settings, forged)
        assert exc_info.value.code == "missing_claim"

    def test_verify_token_response_helper(
        self, store: InMemoryStore, hs256_settings: Settings
    ) -> None:
        token = issue_token(store, hs256_settings, action="otp_request", band="low")
        ok_resp = verify_token_response(store, hs256_settings, token, expected_action="otp_request")
        assert ok_resp.valid is True
        assert ok_resp.band == "low"
        assert ok_resp.action == "otp_request"
        assert ok_resp.expires_at is not None
        assert ok_resp.reason is None

        replay_resp = verify_token_response(
            store, hs256_settings, token, expected_action="otp_request"
        )
        assert replay_resp.valid is False
        assert replay_resp.reason == "token_replayed_or_revoked"

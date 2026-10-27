"""Tests for nonce issuance and verification (P5-03).

Covers: issuance, single-use enforcement, TTL expiry, context binding,
and the context-hash helper.
"""

from __future__ import annotations

import time

import pytest

from app.nonce import (
    NonceError,
    context_hash_from_headers,
    issue_nonce,
    issue_nonce_response,
    make_context_hash,
    verify_nonce,
)
from app.store import InMemoryStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fresh_store() -> InMemoryStore:
    return InMemoryStore()


def _ctx(ip: str = "192.168.1.5", ua: str = "Mozilla/5.0") -> str:
    return make_context_hash(ip, ua)


# ---------------------------------------------------------------------------
# make_context_hash
# ---------------------------------------------------------------------------


class TestMakeContextHash:
    def test_returns_16_hex_chars(self) -> None:
        h = make_context_hash("192.168.1.5", "Mozilla/5.0")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        h1 = make_context_hash("10.0.0.1", "ua")
        h2 = make_context_hash("10.0.0.1", "ua")
        assert h1 == h2

    def test_same_subnet_same_hash(self) -> None:
        """Two IPs in the same /24 produce the same hash (coarsening)."""
        h1 = make_context_hash("192.168.1.5", "ua")
        h2 = make_context_hash("192.168.1.99", "ua")
        assert h1 == h2

    def test_different_subnet_different_hash(self) -> None:
        h1 = make_context_hash("192.168.1.5", "ua")
        h2 = make_context_hash("192.168.2.5", "ua")
        assert h1 != h2

    def test_different_ua_different_hash(self) -> None:
        h1 = make_context_hash("192.168.1.5", "Chrome/120")
        h2 = make_context_hash("192.168.1.5", "Firefox/100")
        assert h1 != h2

    def test_ipv6_coarsened_to_48(self) -> None:
        """Two IPv6 addresses differing only beyond /48 get the same hash."""
        h1 = make_context_hash("2001:db8::1", "ua")
        h2 = make_context_hash("2001:db8::2", "ua")
        assert h1 == h2

    def test_unknown_ip_does_not_raise(self) -> None:
        h = make_context_hash("not-an-ip", "ua")
        assert len(h) == 16


# ---------------------------------------------------------------------------
# Issue nonce
# ---------------------------------------------------------------------------


class TestIssueNonce:
    def test_returns_nonempty_string(self) -> None:
        store = fresh_store()
        token = issue_nonce(store, context_hash=_ctx())
        assert isinstance(token, str)
        assert len(token) > 10

    def test_stored_in_store(self) -> None:
        store = fresh_store()
        token = issue_nonce(store, context_hash=_ctx())
        assert store.get(f"nonce:{token}") is not None

    def test_each_call_returns_unique_token(self) -> None:
        store = fresh_store()
        ctx = _ctx()
        tokens = {issue_nonce(store, context_hash=ctx) for _ in range(50)}
        assert len(tokens) == 50

    def test_custom_ttl_respected(self) -> None:
        store = fresh_store()
        token = issue_nonce(store, context_hash=_ctx(), ttl=1)
        assert store.get(f"nonce:{token}") is not None
        time.sleep(1.1)
        assert store.get(f"nonce:{token}") is None


# ---------------------------------------------------------------------------
# Verify nonce — happy path
# ---------------------------------------------------------------------------


class TestVerifyNonce:
    def test_valid_nonce_accepted(self) -> None:
        store = fresh_store()
        ctx = _ctx()
        token = issue_nonce(store, context_hash=ctx)
        verify_nonce(store, token, context_hash=ctx)  # must not raise

    def test_valid_nonce_is_consumed(self) -> None:
        """After successful verification the nonce is gone from the store."""
        store = fresh_store()
        ctx = _ctx()
        token = issue_nonce(store, context_hash=ctx)
        verify_nonce(store, token, context_hash=ctx)
        assert store.get(f"nonce:{token}") is None

    def test_issue_nonce_response_dict(self) -> None:
        store = fresh_store()
        resp = issue_nonce_response(store, context_hash=_ctx(), ttl=120)
        assert "nonce" in resp
        assert resp["expires_in"] == 120


# ---------------------------------------------------------------------------
# Verify nonce — error cases
# ---------------------------------------------------------------------------


class TestVerifyNonceErrors:
    def test_nonexistent_nonce_raises(self) -> None:
        store = fresh_store()
        with pytest.raises(NonceError, match="invalid_or_expired"):
            verify_nonce(store, "no-such-nonce", context_hash=_ctx())

    def test_second_use_raises(self) -> None:
        """Replay: the same nonce cannot be used twice."""
        store = fresh_store()
        ctx = _ctx()
        token = issue_nonce(store, context_hash=ctx)
        verify_nonce(store, token, context_hash=ctx)
        with pytest.raises(NonceError, match="invalid_or_expired"):
            verify_nonce(store, token, context_hash=ctx)

    def test_expired_nonce_raises(self) -> None:
        store = fresh_store()
        ctx = _ctx()
        token = issue_nonce(store, context_hash=ctx, ttl=1)
        time.sleep(1.1)
        with pytest.raises(NonceError, match="invalid_or_expired"):
            verify_nonce(store, token, context_hash=ctx)

    def test_context_mismatch_raises(self) -> None:
        """Nonce issued for one client must not be accepted by another."""
        store = fresh_store()
        ctx_a = make_context_hash("192.168.1.1", "ChromeUA")
        ctx_b = make_context_hash("10.0.0.1", "FirefoxUA")
        token = issue_nonce(store, context_hash=ctx_a)
        with pytest.raises(NonceError, match="nonce_context_mismatch"):
            verify_nonce(store, token, context_hash=ctx_b)

    def test_context_mismatch_nonce_is_consumed(self) -> None:
        """Even a mismatched nonce is consumed (prevents brute-force)."""
        store = fresh_store()
        ctx_a = make_context_hash("1.2.3.4", "UA-A")
        ctx_b = make_context_hash("5.6.7.8", "UA-B")
        token = issue_nonce(store, context_hash=ctx_a)
        with pytest.raises(NonceError):
            verify_nonce(store, token, context_hash=ctx_b)
        # The nonce must be gone even after a mismatch.
        assert store.get(f"nonce:{token}") is None


# ---------------------------------------------------------------------------
# context_hash_from_headers helper
# ---------------------------------------------------------------------------


class TestContextHashFromHeaders:
    def test_none_ip_does_not_raise(self) -> None:
        h = context_hash_from_headers(None, "ua")
        assert len(h) == 16

    def test_none_ua_does_not_raise(self) -> None:
        h = context_hash_from_headers("1.2.3.4", None)
        assert len(h) == 16

    def test_both_none_does_not_raise(self) -> None:
        h = context_hash_from_headers(None, None)
        assert len(h) == 16

    def test_consistent_with_make_context_hash(self) -> None:
        h1 = context_hash_from_headers("192.168.1.1", "Chrome")
        h2 = make_context_hash("192.168.1.1", "Chrome")
        assert h1 == h2

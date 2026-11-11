"""Tests for sliding-window rate limiting (P5-07)."""

from __future__ import annotations

import dataclasses

import pytest

from app.config import Settings, load_settings
from app.ratelimit import (
    RateLimiter,
    RateLimitError,
    check_rate_limit,
    enforce_rate_limit,
)
from app.store import InMemoryStore


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def settings() -> Settings:
    base = load_settings()
    return dataclasses.replace(
        base,
        rate_limit_nonce_per_min=5,
        rate_limit_assess_per_min=3,
    )


class TestSlidingWindowRateLimiting:
    def test_per_ip_bucket_coarsening_and_limit_enforcement(self, store: InMemoryStore) -> None:
        # Two different host IPs in the same /24 share the same coarse IP bucket
        for i in range(1, 4):
            res = check_rate_limit(
                store,
                endpoint="assess",
                client_ip=f"192.168.10.{i}",
                limit=3,
                window_seconds=60,
            )
            assert res.allowed is True
            assert res.ip_count == i

        exceeded = check_rate_limit(
            store,
            endpoint="assess",
            client_ip="192.168.10.250",
            limit=3,
            window_seconds=60,
        )
        assert exceeded.allowed is False
        assert exceeded.exceeded_bucket == "ip"
        assert exceeded.retry_after_seconds == 60

        # A different /24 subnet is unaffected
        other_subnet = check_rate_limit(
            store,
            endpoint="assess",
            client_ip="192.168.11.1",
            limit=3,
            window_seconds=60,
        )
        assert other_subnet.allowed is True
        assert other_subnet.ip_count == 1

    def test_per_session_limit_triggers_independently(self, store: InMemoryStore) -> None:
        for idx, ip in enumerate(("10.1.0.1", "10.2.0.1"), start=1):
            res = check_rate_limit(
                store,
                endpoint="assess",
                client_ip=ip,
                session_id="sess-abc",
                limit=10,
                session_limit=2,
            )
            assert res.allowed is True
            assert res.session_count == idx

        exceeded = check_rate_limit(
            store,
            endpoint="assess",
            client_ip="10.3.0.1",
            session_id="sess-abc",
            limit=10,
            session_limit=2,
        )
        assert exceeded.allowed is False
        assert exceeded.exceeded_bucket == "session"

    def test_separate_limits_for_nonce_and_assess_endpoints(
        self, store: InMemoryStore, settings: Settings
    ) -> None:
        limiter = RateLimiter(store, settings, challenge_limit_per_min=2)
        ip = "203.0.113.42"

        # Exhaust /v1/assess limit (3/min)
        for _ in range(3):
            assert limiter.check_assess(ip).allowed is True
        assert limiter.check_assess(ip).allowed is False

        # /v1/nonce (5/min) and /v1/assess/challenge (2/min) remain independent
        for _ in range(5):
            assert limiter.check_nonce(ip).allowed is True
        assert limiter.check_nonce(ip).allowed is False

        assert limiter.check_challenge(ip).allowed is True
        assert limiter.check_challenge(ip).allowed is True
        assert limiter.check_challenge(ip).allowed is False

    def test_enforce_rate_limit_raises_error(self, store: InMemoryStore) -> None:
        enforce_rate_limit(store, endpoint="nonce", client_ip="127.0.0.1", limit=1)
        with pytest.raises(RateLimitError) as exc_info:
            enforce_rate_limit(store, endpoint="nonce", client_ip="127.0.0.1", limit=1)
        assert exc_info.value.code == "rate_limit_exceeded"
        assert exc_info.value.retry_after_seconds == 60

    def test_challenge_rate_limit_per_session_and_ip_bucket(
        self, store: InMemoryStore, settings: Settings
    ) -> None:
        """Verify P7-08: check_challenge enforces per-session and per-IP-bucket limits."""
        cfg = dataclasses.replace(
            settings,
            rate_limit_challenge_per_min=4,
            rate_limit_challenge_session_per_min=2,
        )
        limiter = RateLimiter(store, cfg)

        # Session 'sess-1' can make at most 2 challenge attempts even though IP bucket allows 4
        assert limiter.check_challenge("198.51.100.10", session_id="sess-1").allowed is True
        assert limiter.check_challenge("198.51.100.10", session_id="sess-1").allowed is True
        res_sess_exceeded = limiter.check_challenge("198.51.100.10", session_id="sess-1")
        assert res_sess_exceeded.allowed is False
        assert res_sess_exceeded.exceeded_bucket == "session"

        # Another session ('sess-2') in the same /24 consumes #4, then hits IP limit (#5)
        assert limiter.check_challenge("198.51.100.20", session_id="sess-2").allowed is True
        res_ip_exceeded = limiter.check_challenge("198.51.100.20", session_id="sess-2")
        assert res_ip_exceeded.allowed is False
        assert res_ip_exceeded.exceeded_bucket == "ip"

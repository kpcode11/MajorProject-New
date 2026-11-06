"""Sliding-window rate limiting per coarse IP bucket, session ID, and endpoint (P5-07).

Uses :meth:`~app.store.Store.sliding_window_count` so identical rate-limiting
semantics apply across :class:`~app.store.InMemoryStore` and
:class:`~app.store.RedisStore`.

Privacy:
- Client IP addresses are coarsened to ``/24`` (IPv4) or ``/48`` (IPv6) via
  :func:`~app.nonce._coarsen_ip` before building store keys; full IPs are
  never stored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config import Settings
from app.nonce import _coarsen_ip
from app.store import Store

_RL_PREFIX = "rl:"
DEFAULT_WINDOW_SECONDS = 60
DEFAULT_CHALLENGE_LIMIT_PER_MIN = 10


@dataclass(frozen=True)
class RateLimitResult:
    """Result of checking a sliding-window rate limit."""

    allowed: bool
    endpoint: str
    ip_count: int
    session_count: int | None
    limit: int
    window_seconds: int
    retry_after_seconds: int
    exceeded_bucket: Literal["ip", "session"] | None = None


class RateLimitError(Exception):
    """Raised when a request exceeds its sliding-window rate limit."""

    def __init__(self, result: RateLimitResult) -> None:
        bucket = result.exceeded_bucket or "ip"
        super().__init__(
            f"Rate limit exceeded for endpoint {result.endpoint!r} ({bucket} bucket, "
            f"limit={result.limit}/{result.window_seconds}s)"
        )
        self.result = result
        self.code = "rate_limit_exceeded"
        self.retry_after_seconds = result.retry_after_seconds


def check_rate_limit(
    store: Store,
    *,
    endpoint: str,
    client_ip: str | None,
    limit: int,
    session_id: str | None = None,
    session_limit: int | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> RateLimitResult:
    """Record one request and check per-IP-bucket and per-session sliding windows.

    Args:
        store: Backing :class:`~app.store.Store`.
        endpoint: Endpoint identifier (e.g. ``"nonce"``, ``"assess"``, ``"challenge"``).
        client_ip: Raw client IP address (coarsened to /24 or /48 before storage).
        limit: Maximum allowed requests per ``window_seconds`` for the IP bucket.
        session_id: Optional session identifier (or context hash) for per-session limiting.
        session_limit: Optional override for the per-session limit (defaults to ``limit``).
        window_seconds: Sliding window width in seconds (default 60).

    Returns:
        A :class:`RateLimitResult` indicating whether the request is within limits.
    """
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")
    if window_seconds <= 0:
        raise ValueError(f"window_seconds must be positive, got {window_seconds}")

    ip_bucket = _coarsen_ip(client_ip or "0.0.0.0")
    ip_key = f"{_RL_PREFIX}{endpoint}:ip:{ip_bucket}"
    ip_count = store.sliding_window_count(ip_key, window_seconds)

    sess_count: int | None = None
    eff_sess_limit = session_limit if session_limit is not None else limit
    if session_id and session_id.strip():
        sess_key = f"{_RL_PREFIX}{endpoint}:sess:{session_id.strip()}"
        sess_count = store.sliding_window_count(sess_key, window_seconds)

    exceeded_bucket: Literal["ip", "session"] | None = None
    if ip_count > limit:
        exceeded_bucket = "ip"
    elif sess_count is not None and sess_count > eff_sess_limit:
        exceeded_bucket = "session"

    allowed = exceeded_bucket is None
    return RateLimitResult(
        allowed=allowed,
        endpoint=endpoint,
        ip_count=ip_count,
        session_count=sess_count,
        limit=limit,
        window_seconds=window_seconds,
        retry_after_seconds=0 if allowed else window_seconds,
        exceeded_bucket=exceeded_bucket,
    )


def enforce_rate_limit(
    store: Store,
    *,
    endpoint: str,
    client_ip: str | None,
    limit: int,
    session_id: str | None = None,
    session_limit: int | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> RateLimitResult:
    """Check rate limits and raise :class:`RateLimitError` when exceeded."""
    res = check_rate_limit(
        store,
        endpoint=endpoint,
        client_ip=client_ip,
        limit=limit,
        session_id=session_id,
        session_limit=session_limit,
        window_seconds=window_seconds,
    )
    if not res.allowed:
        raise RateLimitError(res)
    return res


class RateLimiter:
    """Endpoint-aware sliding-window rate limiter configured from :class:`~app.config.Settings`."""

    def __init__(
        self,
        store: Store,
        settings: Settings,
        *,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        challenge_limit_per_min: int = DEFAULT_CHALLENGE_LIMIT_PER_MIN,
    ) -> None:
        self.store = store
        self.settings = settings
        self.window_seconds = window_seconds
        self.challenge_limit_per_min = challenge_limit_per_min

    def check_nonce(
        self,
        client_ip: str | None,
        *,
        session_id: str | None = None,
    ) -> RateLimitResult:
        """Check the ``GET /v1/nonce`` sliding-window rate limit."""
        return check_rate_limit(
            self.store,
            endpoint="nonce",
            client_ip=client_ip,
            limit=self.settings.rate_limit_nonce_per_min,
            session_id=session_id,
            window_seconds=self.window_seconds,
        )

    def check_assess(
        self,
        client_ip: str | None,
        *,
        session_id: str | None = None,
    ) -> RateLimitResult:
        """Check the ``POST /v1/assess`` sliding-window rate limit."""
        return check_rate_limit(
            self.store,
            endpoint="assess",
            client_ip=client_ip,
            limit=self.settings.rate_limit_assess_per_min,
            session_id=session_id,
            window_seconds=self.window_seconds,
        )

    def check_challenge(
        self,
        client_ip: str | None,
        *,
        session_id: str | None = None,
    ) -> RateLimitResult:
        """Check the ``POST /v1/assess/challenge`` sliding-window rate limit."""
        return check_rate_limit(
            self.store,
            endpoint="challenge",
            client_ip=client_ip,
            limit=self.challenge_limit_per_min,
            session_id=session_id,
            window_seconds=self.window_seconds,
        )

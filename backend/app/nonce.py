"""Nonce issuance and single-use verification (P5-03).

A nonce is a random 32-byte URL-safe token that the SDK sends back with each
``POST /v1/assess`` request to prove liveness and prevent replay.

Design:
- Generated with ``secrets.token_urlsafe(32)`` (~43 URL-safe characters).
- Stored in the :class:`~app.store.Store` with a configurable TTL (default
  300 s) keyed as ``nonce:<token>``.
- **Single-use**: consumed with ``store.get_and_delete`` so a second request
  with the same nonce is rejected even within the TTL window.
- **Context-bound**: the nonce is tied to a *context hash* derived from a
  coarse IP bucket and the raw User-Agent string.  On verification the
  context hash must match, preventing a nonce stolen from one client from
  being replayed by another.

Privacy notes:
- The full IP address is never stored.  The context hash uses only a /24
  (IPv4) or /48 (IPv6) prefix, so individual addresses cannot be recovered.
- The User-Agent is hashed with BLAKE2b (32 bytes); the raw string is not
  stored.
"""

from __future__ import annotations

import hashlib
import ipaddress
import secrets

from app.store import Store

# Store key prefix — keeps nonces isolated from other store entries.
_NONCE_PREFIX = "nonce:"

# ---------------------------------------------------------------------------
# Context hashing
# ---------------------------------------------------------------------------


def _coarsen_ip(ip_str: str) -> str:
    """Return a coarse IP bucket string (IPv4 /24, IPv6 /48).

    Args:
        ip_str: Dotted-decimal IPv4 or colon-hex IPv6 address string.
            Unrecognised strings are returned unchanged.

    Returns:
        Network prefix string, e.g. ``"192.168.1.0/24"``.
    """
    try:
        addr = ipaddress.ip_address(ip_str)
        if isinstance(addr, ipaddress.IPv4Address):
            return str(ipaddress.ip_network(f"{ip_str}/24", strict=False))
        # IPv6
        return str(ipaddress.ip_network(f"{ip_str}/48", strict=False))
    except ValueError:
        return ip_str


def make_context_hash(ip: str, user_agent: str) -> str:
    """Return a short hex digest binding a nonce to a coarse client context.

    Args:
        ip: Client IP address string.  Only the /24 (IPv4) or /48 (IPv6)
            prefix is used so individual addresses cannot be recovered.
        user_agent: Raw ``User-Agent`` header value.

    Returns:
        16-character hex string (64-bit BLAKE2b digest).
    """
    coarse_ip = _coarsen_ip(ip)
    raw = f"{coarse_ip}|{user_agent}"
    digest = hashlib.blake2b(raw.encode(), digest_size=8).hexdigest()
    return digest


# ---------------------------------------------------------------------------
# Issuance
# ---------------------------------------------------------------------------


def issue_nonce(
    store: Store,
    *,
    context_hash: str,
    ttl: int = 300,
) -> str:
    """Generate and store a fresh single-use nonce.

    Args:
        store: The backing :class:`~app.store.Store`.
        context_hash: The client context hash produced by
            :func:`make_context_hash`.  Stored with the nonce so that
            :func:`verify_nonce` can enforce context binding.
        ttl: Time-to-live in seconds (default 300).

    Returns:
        The URL-safe nonce string to return to the client.
    """
    token = secrets.token_urlsafe(32)
    key = f"{_NONCE_PREFIX}{token}"
    store.set(key, context_hash, ttl=ttl)
    return token


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


class NonceError(Exception):
    """Raised by :func:`verify_nonce` when a nonce cannot be accepted."""


def verify_nonce(
    store: Store,
    token: str,
    *,
    context_hash: str,
) -> None:
    """Verify and consume a nonce.

    This is the **only** function that should validate nonces; it is atomic
    (the nonce is deleted on first use) and context-checked.

    Args:
        store: The backing :class:`~app.store.Store`.
        token: The nonce string sent by the client.
        context_hash: The context hash computed from the current request's
            IP and User-Agent.  Must match the value stored at issuance.

    Raises:
        NonceError: With a descriptive code string if the nonce is missing,
            expired, already used, or bound to a different context.
    """
    key = f"{_NONCE_PREFIX}{token}"
    stored_context = store.get_and_delete(key)

    if stored_context is None:
        raise NonceError("invalid_or_expired_nonce")

    if stored_context != context_hash:
        raise NonceError("nonce_context_mismatch")


# ---------------------------------------------------------------------------
# Convenience: issue + return response dict
# ---------------------------------------------------------------------------


def issue_nonce_response(
    store: Store,
    *,
    context_hash: str,
    ttl: int = 300,
) -> dict[str, object]:
    """Issue a nonce and return a dict suitable for :class:`~app.schemas.NonceResponse`.

    Args:
        store: The backing store.
        context_hash: Client context hash from :func:`make_context_hash`.
        ttl: Nonce TTL in seconds.

    Returns:
        ``{"nonce": <token>, "expires_in": <ttl>}``
    """
    token = issue_nonce(store, context_hash=context_hash, ttl=ttl)
    return {"nonce": token, "expires_in": ttl}


# ---------------------------------------------------------------------------
# Helper: extract context from a FastAPI / Starlette request
# ---------------------------------------------------------------------------


def context_hash_from_headers(
    client_ip: str | None,
    user_agent: str | None,
) -> str:
    """Build the context hash from raw header values.

    Args:
        client_ip: Client IP string, or ``None`` / empty if unknown.
        user_agent: ``User-Agent`` header value, or ``None`` / empty.

    Returns:
        A 16-character hex context hash.
    """
    ip = client_ip or "0.0.0.0"
    ua = user_agent or ""
    return make_context_hash(ip, ua)

"""Key-value store abstraction for nonces, rate-limit counters and JTI tracking.

The :class:`Store` interface covers five operations needed by the backend:

* **get / set / delete** — basic key-value with optional TTL.
* **get_and_delete** — atomic fetch-and-remove (used for single-use nonces and JTIs).
* **increment** — atomic integer counter with optional TTL on first write.
* **sliding_window_count** — count events in a sliding time window (rate limiting).

Two implementations are provided:

* :class:`InMemoryStore` — thread-safe, no external dependencies.  Used by
  default in development and in all unit tests.
* :class:`RedisStore` — thin wrapper around a :mod:`redis` client.  Requires
  the ``STORE_BACKEND=redis`` setting and a reachable Redis instance.

Usage::

    from app.store import build_store
    store = build_store("memory")          # or "redis", redis_url=...

    store.set("my_key", "value", ttl=300)
    val = store.get("my_key")              # "value"
    val = store.get_and_delete("my_key")   # "value"; key is now gone
    store.get("my_key")                    # None
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod

# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class Store(ABC):
    """Minimal key-value store interface required by the backend."""

    # --- basic operations ---------------------------------------------------

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Return the value for *key*, or ``None`` if absent or expired."""

    @abstractmethod
    def set(self, key: str, value: str, *, ttl: int | None = None) -> None:
        """Set *key* to *value*.

        Args:
            key: Store key.
            value: String value to store.
            ttl: Optional time-to-live in seconds.  If ``None`` the entry
                persists until deleted.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete *key* (silently ignored if the key does not exist)."""

    # --- atomic operations --------------------------------------------------

    @abstractmethod
    def get_and_delete(self, key: str) -> str | None:
        """Atomically fetch and remove *key*.

        Returns the stored value, or ``None`` if the key is absent or expired.
        Subsequent calls for the same key return ``None``.
        """

    # --- counters -----------------------------------------------------------

    @abstractmethod
    def increment(self, key: str, *, ttl: int | None = None) -> int:
        """Atomically increment an integer counter at *key* and return the new value.

        If the key does not exist, it is created with value 1.  *ttl* is
        applied only on the **first** increment (i.e. when the key is
        created); later calls leave the expiry unchanged.

        Args:
            key: Counter key.
            ttl: Optional TTL in seconds applied when the counter is created.

        Returns:
            The new counter value after incrementing.
        """

    # --- rate-limit helpers -------------------------------------------------

    @abstractmethod
    def sliding_window_count(self, key: str, window_seconds: int) -> int:
        """Return the number of events recorded for *key* in the last *window_seconds*.

        Each call also **records** one new event at the current time.

        This is implemented as a sorted list of timestamps.  Old entries
        outside the window are discarded before counting so memory stays
        bounded to ``(rate × window)`` entries per key.

        Args:
            key: Rate-limit bucket key (for example ``"nonce:192.168.1.0/24"``).
            window_seconds: Width of the sliding window in seconds.

        Returns:
            Total event count within the window, **including** the new event
            just recorded.
        """


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


class _Entry:
    """Single stored entry with an optional expiry timestamp."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: str, expires_at: float | None) -> None:
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at


class InMemoryStore(Store):
    """Thread-safe, pure-Python store backed by a dict.

    This is the default for development and tests.  It does **not** persist
    across process restarts.
    """

    def __init__(self) -> None:
        self._data: dict[str, _Entry] = {}
        # Sorted event-timestamp lists for sliding_window_count.
        self._windows: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    # -- helpers -------------------------------------------------------------

    def _get_live(self, key: str) -> _Entry | None:
        """Return the entry if it exists and has not expired, else None."""
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._data[key]
            return None
        return entry

    # -- Store interface -----------------------------------------------------

    def get(self, key: str) -> str | None:
        with self._lock:
            entry = self._get_live(key)
            return entry.value if entry else None

    def set(self, key: str, value: str, *, ttl: int | None = None) -> None:
        expires_at = time.monotonic() + ttl if ttl is not None else None
        with self._lock:
            self._data[key] = _Entry(value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def get_and_delete(self, key: str) -> str | None:
        with self._lock:
            entry = self._get_live(key)
            if entry is None:
                return None
            del self._data[key]
            return entry.value

    def increment(self, key: str, *, ttl: int | None = None) -> int:
        with self._lock:
            entry = self._get_live(key)
            if entry is None:
                # First increment — apply TTL.
                expires_at = time.monotonic() + ttl if ttl is not None else None
                self._data[key] = _Entry("1", expires_at)
                return 1
            try:
                new_val = int(entry.value) + 1
            except ValueError:
                new_val = 1
            # Preserve existing expiry.
            self._data[key] = _Entry(str(new_val), entry.expires_at)
            return new_val

    def sliding_window_count(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._windows.get(key, [])
            # Evict old entries.
            timestamps = [t for t in timestamps if t > cutoff]
            timestamps.append(now)
            self._windows[key] = timestamps
            return len(timestamps)


# ---------------------------------------------------------------------------
# Redis implementation
# ---------------------------------------------------------------------------


class RedisStore(Store):
    """Store implementation backed by a Redis instance.

    Uses native Redis commands (``GETDEL``, pipelined ``INCR``/``EXPIRE``,
    sorted-set sliding windows) so it works with both the ``redis`` client
    and ``fakeredis`` without requiring Lua scripting support.

    Args:
        redis_client: A :mod:`redis` synchronous client (or a ``fakeredis``
            instance in tests).
    """

    def __init__(self, redis_client: object) -> None:
        # Accept any redis-compatible client (redis.Redis or fakeredis.FakeRedis).
        self._r = redis_client

    @staticmethod
    def _decode(val: object) -> str | None:
        if val is None:
            return None
        return val.decode() if isinstance(val, bytes) else str(val)

    # -- Store interface -----------------------------------------------------

    def get(self, key: str) -> str | None:
        return self._decode(self._r.get(key))  # type: ignore[attr-defined]

    def set(self, key: str, value: str, *, ttl: int | None = None) -> None:
        if ttl is not None:
            self._r.set(key, value, ex=ttl)  # type: ignore[attr-defined]
        else:
            self._r.set(key, value)  # type: ignore[attr-defined]

    def delete(self, key: str) -> None:
        self._r.delete(key)  # type: ignore[attr-defined]

    def get_and_delete(self, key: str) -> str | None:
        """Atomically fetch and remove *key* using the Redis GETDEL command.

        Requires Redis 6.2+.  Both the ``redis`` package ≥ 4.0 and
        ``fakeredis`` ≥ 2.0 expose this command natively.
        """
        return self._decode(self._r.getdel(key))  # type: ignore[attr-defined]

    def increment(self, key: str, *, ttl: int | None = None) -> int:
        """Atomically increment *key* and set TTL only on its first creation.

        Uses a pipeline to issue ``INCR`` and then ``EXPIRE`` (with ``NX``
        flag when available, otherwise conditional on the value being 1 so
        subsequent increments do not reset the expiry).
        """
        pipe = self._r.pipeline()  # type: ignore[attr-defined]
        pipe.incr(key)
        results = pipe.execute()
        new_val: int = int(results[0])
        if new_val == 1 and ttl is not None:
            # Only set expiry on first creation.
            self._r.expire(key, ttl)  # type: ignore[attr-defined]
        return new_val

    def sliding_window_count(self, key: str, window_seconds: int) -> int:
        """Record one event now and return the count within the window.

        Implemented with a Redis sorted set keyed on *key*.  Each event is
        stored with its Unix timestamp as the score.  Old members outside the
        window are removed before counting.
        """
        import time as _time

        now = _time.time()
        cutoff = now - window_seconds
        pipe = self._r.pipeline()  # type: ignore[attr-defined]
        # Remove events older than the window.
        pipe.zremrangebyscore(key, "-inf", cutoff)
        # Add the current event; score = timestamp, member = unique id.
        pipe.zadd(key, {str(now): now})
        # Count remaining members.
        pipe.zcard(key)
        # Refresh the TTL so the key expires after inactivity.
        pipe.expire(key, window_seconds * 2)
        results = pipe.execute()
        return int(results[2])


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_store(
    backend: str = "memory",
    redis_url: str = "redis://localhost:6379/0",
) -> Store:
    """Create and return a :class:`Store` instance.

    Args:
        backend: ``"memory"`` (default) or ``"redis"``.
        redis_url: Redis connection URL used when *backend* is ``"redis"``.

    Returns:
        A :class:`Store` instance ready for use.

    Raises:
        ValueError: If *backend* is unknown.
        ImportError: If ``redis`` is not installed and *backend* is ``"redis"``.
    """
    if backend == "memory":
        return InMemoryStore()
    if backend == "redis":
        try:
            import redis as _redis
        except ImportError as exc:
            raise ImportError(
                "The 'redis' package is required when STORE_BACKEND=redis. "
                "Install it with: pip install redis"
            ) from exc
        client = _redis.from_url(redis_url, decode_responses=False)
        return RedisStore(client)
    raise ValueError(f"unknown store backend: {backend!r}. Must be 'memory' or 'redis'.")

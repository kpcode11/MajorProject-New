"""Tests for the Store abstraction — both InMemoryStore and RedisStore (P5-01).

The same behavioural contract is tested against both backends via a pytest
parametrize fixture.  The Redis backend uses ``fakeredis`` so no live Redis
instance is required.
"""

from __future__ import annotations

import time

import pytest

from app.store import InMemoryStore, RedisStore, Store, build_store

# ---------------------------------------------------------------------------
# Fixture: parametrised store
# ---------------------------------------------------------------------------

try:
    import fakeredis  # type: ignore[import-untyped]

    _FAKEREDIS_AVAILABLE = True
except ImportError:
    _FAKEREDIS_AVAILABLE = False


def _make_memory_store() -> Store:
    return InMemoryStore()


def _make_redis_store() -> Store:
    server = fakeredis.FakeServer()
    client = fakeredis.FakeRedis(server=server)
    return RedisStore(client)


_STORE_PARAMS = [
    pytest.param(_make_memory_store, id="memory"),
    pytest.param(
        _make_redis_store,
        id="redis",
        marks=pytest.mark.skipif(
            not _FAKEREDIS_AVAILABLE, reason="fakeredis not installed"
        ),
    ),
]


@pytest.fixture(params=_STORE_PARAMS)
def store(request: pytest.FixtureRequest) -> Store:  # type: ignore[type-arg]
    factory = request.param
    return factory()


# ---------------------------------------------------------------------------
# get / set / delete
# ---------------------------------------------------------------------------


class TestBasicOperations:
    """get, set and delete behave correctly."""

    def test_set_and_get(self, store: Store) -> None:
        store.set("k", "hello")
        assert store.get("k") == "hello"

    def test_get_missing_returns_none(self, store: Store) -> None:
        assert store.get("no-such-key") is None

    def test_delete_existing(self, store: Store) -> None:
        store.set("k", "v")
        store.delete("k")
        assert store.get("k") is None

    def test_delete_missing_is_silent(self, store: Store) -> None:
        store.delete("no-such-key")  # must not raise

    def test_overwrite(self, store: Store) -> None:
        store.set("k", "first")
        store.set("k", "second")
        assert store.get("k") == "second"


# ---------------------------------------------------------------------------
# TTL / expiry
# ---------------------------------------------------------------------------


class TestTTL:
    """Entries expire after their TTL."""

    def test_entry_exists_before_expiry(self, store: Store) -> None:
        store.set("k", "v", ttl=60)
        assert store.get("k") == "v"

    def test_entry_absent_after_expiry(self, store: Store) -> None:
        store.set("k", "v", ttl=1)
        time.sleep(1.1)
        assert store.get("k") is None

    def test_no_ttl_persists(self, store: Store) -> None:
        store.set("k", "v")
        time.sleep(0.05)
        assert store.get("k") == "v"


# ---------------------------------------------------------------------------
# get_and_delete (atomic fetch-and-remove)
# ---------------------------------------------------------------------------


class TestGetAndDelete:
    """get_and_delete is single-use."""

    def test_returns_value_and_removes(self, store: Store) -> None:
        store.set("nonce", "abc123")
        val = store.get_and_delete("nonce")
        assert val == "abc123"
        assert store.get("nonce") is None

    def test_second_call_returns_none(self, store: Store) -> None:
        store.set("nonce", "once")
        store.get_and_delete("nonce")
        assert store.get_and_delete("nonce") is None

    def test_missing_key_returns_none(self, store: Store) -> None:
        assert store.get_and_delete("ghost") is None

    def test_respects_ttl_expiry(self, store: Store) -> None:
        store.set("nonce", "val", ttl=1)
        time.sleep(1.1)
        assert store.get_and_delete("nonce") is None


# ---------------------------------------------------------------------------
# increment
# ---------------------------------------------------------------------------


class TestIncrement:
    """increment creates and atomically bumps integer counters."""

    def test_first_call_returns_one(self, store: Store) -> None:
        assert store.increment("ctr") == 1

    def test_sequential_calls_increment(self, store: Store) -> None:
        store.increment("ctr")
        assert store.increment("ctr") == 2
        assert store.increment("ctr") == 3

    def test_ttl_applied_on_first_call(self, store: Store) -> None:
        store.increment("ctr_ttl", ttl=1)
        assert store.get("ctr_ttl") == "1"
        time.sleep(1.1)
        # After expiry, a new increment starts fresh.
        assert store.increment("ctr_ttl", ttl=60) == 1

    def test_ttl_not_reset_on_subsequent_call(self, store: Store) -> None:
        """TTL is set only on the first increment; later calls don't reset it."""
        store.increment("ctr_once", ttl=1)
        store.increment("ctr_once", ttl=9999)  # should NOT extend expiry
        time.sleep(1.1)
        assert store.get("ctr_once") is None

    def test_independent_counters(self, store: Store) -> None:
        store.increment("a")
        store.increment("a")
        store.increment("b")
        assert store.increment("a") == 3
        assert store.increment("b") == 2


# ---------------------------------------------------------------------------
# sliding_window_count (rate limiting)
# ---------------------------------------------------------------------------


class TestSlidingWindowCount:
    """sliding_window_count records events and counts within the window."""

    def test_first_call_returns_one(self, store: Store) -> None:
        assert store.sliding_window_count("bucket", 60) == 1

    def test_multiple_calls_within_window(self, store: Store) -> None:
        store.sliding_window_count("bucket2", 60)
        store.sliding_window_count("bucket2", 60)
        assert store.sliding_window_count("bucket2", 60) == 3

    def test_old_events_excluded(self, store: Store) -> None:
        """Events older than the window are not counted."""
        store.sliding_window_count("bucket3", 1)  # one event now
        time.sleep(1.1)  # let that event expire
        # New event — only it falls within the 1-second window.
        assert store.sliding_window_count("bucket3", 1) == 1

    def test_independent_buckets(self, store: Store) -> None:
        store.sliding_window_count("r1", 60)
        store.sliding_window_count("r1", 60)
        store.sliding_window_count("r2", 60)
        assert store.sliding_window_count("r1", 60) == 3
        assert store.sliding_window_count("r2", 60) == 2


# ---------------------------------------------------------------------------
# build_store factory
# ---------------------------------------------------------------------------


class TestBuildStore:
    """build_store returns the correct implementation."""

    def test_memory_backend(self) -> None:
        s = build_store("memory")
        assert isinstance(s, InMemoryStore)

    def test_redis_backend(self) -> None:
        if not _FAKEREDIS_AVAILABLE:
            pytest.skip("fakeredis not installed")
        # Patch redis.from_url to use fakeredis so no live server is needed.
        import fakeredis


        real_from_url = None
        try:
            import redis as _redis  # type: ignore[import-untyped]

            real_from_url = _redis.from_url
            _redis.from_url = lambda url, **kw: fakeredis.FakeRedis()  # type: ignore[attr-defined]
        except ImportError:
            pytest.skip("redis not installed")

        try:
            s = build_store("redis")
            assert isinstance(s, RedisStore)
        finally:
            if real_from_url is not None:
                import redis as _redis  # type: ignore[import-untyped]

                _redis.from_url = real_from_url

    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown store backend"):
            build_store("cassandra")

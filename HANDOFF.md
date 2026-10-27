# Handoff

**Updated:** 2026-10-27  |  **By:** Kiro  |  **Branch:** main  |  **Last commit:** b8ffaae

## Current task

- ID: P5-02 — API schemas and limits
- State: ready to start.

## Done in P5-01

- Expanded `backend/app/config.py` with a full `Settings` dataclass and
  `load_settings()` function. Settings are resolved from environment variables
  (highest priority) → YAML file → built-in defaults. Covers: `STORE_BACKEND`,
  `REDIS_URL`, `DATABASE_URL`, JWT material and algorithm, model/config paths,
  nonce TTL, rate-limit caps, body-size limit, feature-storage toggle, and
  assessment TTL.
- Implemented `backend/app/store.py`:
  - Abstract `Store` interface (get, set, delete, get_and_delete, increment,
    sliding_window_count).
  - `InMemoryStore` — thread-safe, no deps; TTL via `time.monotonic()`.
  - `RedisStore` — uses `GETDEL` (native, no Lua) and pipelined `INCR`/
    `EXPIRE`; sliding window via Redis sorted sets.
  - `build_store(backend, redis_url)` factory.
- 19 settings tests (`tests/test_settings.py`) + 44 store tests
  (`tests/test_store.py`, parametrised over both backends via `fakeredis`).
- Full test suite: 156 tests, 0 failures. Lint: 0 issues.

## Exact next step

- Implement `backend/app/schemas.py` (P5-02): Pydantic v2 models for all
  requests and responses from Appendix B. Add field-level validation:
  max 600 mouse points, max 300 key events, numeric ranges, string lengths,
  and a max body size guard (64 KB). The existing `EnvSignals` model (P4-01)
  must be kept; the new models build on top of it.

## Files touched in P5-01

- `backend/app/config.py` — expanded from rule-config-only to full settings
- `backend/app/store.py` — implemented from empty stub
- `backend/tests/test_settings.py` — new
- `backend/tests/test_store.py` — new
- `PROGRESS.md` — P5-01 marked DONE with commit hash

## Commands to run first

    cd backend
    .\.venv\Scripts\Activate.ps1
    python -m pytest -q --tb=short
    python -m ruff check app/ tests/

## Known problems / gotchas

- `fakeredis` 2.x does not support Lua scripting (`EVALSHA`/`EVAL`). The
  `RedisStore` was rewritten to use only native commands (`GETDEL`, `INCR`,
  sorted sets). This is fine for Redis 6.2+ which is the target.
- The pytest cache directory has a Windows permissions issue (harmless warning).
- `EnvSignals` already exists in `schemas.py` (P4-01); preserve it exactly
  when expanding that file.

## Questions for the human

- None.

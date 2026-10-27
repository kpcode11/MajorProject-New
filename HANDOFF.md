# Handoff

**Updated:** 2026-10-27  |  **By:** Kiro  |  **Branch:** main  |  **Last commit:** ddc4dab

## Current task

- ID: P5-06 — Human tokens (JWT)
- State: ready to start.

## Done in this session (P5-01, P5-02, P5-03, P5-05)

**P5-01:** Settings and score store
- Expanded `backend/app/config.py` with full `Settings` dataclass and
  `load_settings()` (env > YAML > defaults). 20 settings: store backend,
  Redis/DB URLs, JWT config, model paths, nonce TTL, rate limits, body size,
  feature storage, retention TTLs.
- Implemented `backend/app/store.py`: abstract `Store`, `InMemoryStore`
  (thread-safe, TTL via `time.monotonic()`), `RedisStore` (uses `GETDEL`,
  pipelined `INCR`/`EXPIRE`, sorted-set sliding windows). 
- 63 tests (19 settings + 44 store, parametrised over both backends).

**P5-02:** API schemas and limits
- Complete Pydantic v2 schemas in `backend/app/schemas.py` covering Appendix B:
  `EnvSignals` (with new field limits), `MouseBehaviour`, `KeyBehaviour`,
  `TouchBehaviour`, `TimingSignals`, `BehaviourPayload`, `AssessRequest`,
  `AssessResponse`, `ChallengeInfo`, `ChallengeAssessRequest`,
  `TokenVerifyRequest/Response`, `NonceResponse`, `HealthResponse`,
  `ErrorResponse`.
- Enforced limits: max 600 mouse points, 300 key events, 20 gestures × 100
  points; numeric ranges; string lengths; key class validation.
- Fixed one pre-existing test (`test_rules.py`) that passed an out-of-range
  timezone_offset_min — now uses `model_construct` to bypass validation and
  test the rule directly.
- 64 schema tests + 156 existing = 220 total.

**P5-03:** Nonces
- Implemented `backend/app/nonce.py`: `issue_nonce()`, `verify_nonce()`,
  `make_context_hash()` (BLAKE2b of coarse IP /24 or /48 + User-Agent),
  `NonceError` exception, `context_hash_from_headers()` helper.
- Single-use enforcement via `store.get_and_delete`; context binding prevents
  cross-client replay.
- 23 nonce tests.

**P5-05:** Risk policy
- Created `backend/config/policy.yaml` (Appendix C.1 structure): action classes
  (low/medium/high with allow_below/deny_at_or_above thresholds), action
  mappings, fail-safe modes, band cutoffs.
- Implemented `backend/app/policy.py`: `PolicyEngine`, `load_policy()`,
  `decide()`, `score_to_band()`, `decide_redis_down()`,
  `decide_model_error()`. Returns `Decision(verdict, band, degraded)`.
- 34 policy tests covering all action classes, boundaries, fail-safe modes.

**Summary:** 277 backend tests pass, 0 failures. Lint clean.

## Exact next step

- Implement `backend/app/tokens.py` (P5-06): JWT issuance with claims `iss`,
  `aud`, `act`, `iat`, `exp`, `jti`, `band`. Support HS256 (dev, HMAC secret)
  and RS256/ES256 (production, key files). Single-use `jti` tracking via Store.
  Verification function with signature check, expiry check, `jti` replay
  prevention, and optional `act` claim match.

## Files touched in this session

- `backend/app/config.py` — expanded to full settings
- `backend/app/store.py` — implemented Store + 2 backends
- `backend/app/schemas.py` — complete API schemas
- `backend/app/nonce.py` — nonce issuance and verification
- `backend/app/policy.py` — risk policy engine
- `backend/config/policy.yaml` — new policy config
- `backend/tests/test_settings.py` — new
- `backend/tests/test_store.py` — new
- `backend/tests/test_schemas.py` — new
- `backend/tests/test_nonce.py` — new
- `backend/tests/test_policy.py` — new
- `backend/tests/test_rules.py` — fixed one test for schema validation
- `PROGRESS.md` — P5-01, P5-02, P5-03, P5-05 marked DONE with commit hashes

## Commands to run first

    cd backend
    .\.venv\Scripts\Activate.ps1
    python -m pytest -q --tb=short
    python -m ruff check app/ tests/

## Known problems / gotchas

- P5-04 (model scoring) is still TODO — it requires importing ML feature code
  from the `ml` package and loading the ONNX model at
  `backend/models/mouse-v1/model.onnx`. The model files exist, but the ML
  package needs to be installed as a local dependency first.
- `fakeredis` 2.x doesn't support Lua scripting; `RedisStore` uses only native
  commands (`GETDEL`, `INCR`, sorted sets) which works fine for Redis 6.2+.
- The pytest cache directory has a Windows permissions warning (harmless).

## Questions for the human

- None.

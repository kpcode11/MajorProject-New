## Phase 5 — Scoring backend

**Goal:** A FastAPI service that issues nonces, scores sessions (rules + ONNX models + fusion), decides, issues signed tokens and logs decisions without PII.

### Tasks

- [ ] **P5-01** `config.py`: settings from environment/YAML (`STORE_BACKEND=memory|redis`, `REDIS_URL`, `DATABASE_URL` (default SQLite), key material, model paths, thresholds file, limits). Also implement `store.py`: a small `Store` interface (get/set/delete with TTL, atomic get-and-delete, counters and sliding windows) with an in-memory implementation (default for dev and tests) and a Redis implementation; run the same tests against both (use `fakeredis` for Redis).
- [ ] **P5-02** `schemas.py`: Pydantic v2 models for all requests/responses (Appendix B). Enforce limits: max body 64 KB, max trace points (for example 600 mouse points, 300 key events), numeric ranges, string lengths.
- [ ] **P5-03** `nonce.py`: issue random 32-byte URL-safe nonces; store via the `Store` abstraction with TTL (default 300 s) bound to a context hash (IP bucket + user-agent hash); single use (atomic get-and-delete).
- [ ] **P5-04** `scoring.py`:
  - Load ONNX sessions once at startup (mouse, keyboard, later touch) with metadata checks (feature order and version).
  - Extract features by importing the **same** feature code as the ML package (`botguard_ml.features`) — install it as a local dependency. Do not duplicate feature code.
  - Run models, apply stored calibration, fuse per `fusion` metadata, combine with the rule score, return `ScoreResult(score, band, reasons, model_versions)`.
  - Explainability: top-3 contributing features per modality (use pre-computed SHAP-style approximations or tree contributions available from the model/ONNX path; if not feasible at serving time, return rule reasons plus the top features by global importance and note the limitation).
- [ ] **P5-05** `policy.py`: map score + action class to `allow | challenge | deny` using `config/policy.yaml` (Appendix C). Never return the exact score to untrusted clients; return a band (`low`, `medium`, `high`). Exact score goes only to logs and the admin API.
- [ ] **P5-06** `tokens.py`: JWT with claims `iss`, `aud`, `act`, `iat`, `exp` (60-120 s), `jti`, `band`. Support HS256 for development and RS256/ES256 via key files for production-like mode. `jti` single-use via the Store.
- [ ] **P5-07** `ratelimit.py`: sliding-window limits in the Store per IP bucket, per session id, per endpoint. Separate limits for `/v1/nonce` and `/v1/assess`.
- [ ] **P5-08** `db.py`: SQLAlchemy models (SQLite by default, PostgreSQL optional) and migrations (Alembic) for `assessments` and `challenges` (Appendix B.5). No raw traces stored by default. Optional feature storage behind a config flag with TTL.
- [ ] **P5-09** `main.py`: endpoints `GET /v1/nonce`, `POST /v1/assess`, `POST /v1/assess/challenge`, `POST /v1/token/verify`, `GET /v1/health`, admin endpoints (Phase 9), with consistent error format and request ids.
- [ ] **P5-10** Middleware dependency `require_human_token(action)` for protected routes (used by the portal's protected API).
- [ ] **P5-11** Fail-safe policy (configurable, documented in `docs/architecture.md`): Store/Redis unavailable -> deny sensitive actions; model error -> rules-only decision and `degraded=true`; DB down -> continue and buffer logs.
- [ ] **P5-12** Structured logging with request id; never log payload contents or full IPs.
- [ ] **P5-13** Tests (pytest + httpx `AsyncClient`):
  - nonce single-use, expiry, and context binding;
  - oversize/malformed payload returns 4xx quickly;
  - replayed assess payload rejected;
  - token expiry, wrong action, reused `jti`, bad signature;
  - rate limit triggers;
  - fail-safe behaviour when Redis/model is unavailable (use fakes);
  - scoring with fixture payloads gives expected bands (a clean human-like fixture -> low; a headless/straight-line-bot fixture -> high).
- [ ] **P5-14** Latency micro-benchmark script `backend/bench_scoring.py` (1,000 calls; prints p50/p95/p99).

### Deliverables

Runnable backend, tests, OpenAPI document exported to `docs/api.md`, benchmark output in `results/system/scoring_latency.json`.

### Acceptance criteria

- [ ] `pytest backend/tests -q` passes; coverage on `nonce`, `tokens`, `policy`, `ratelimit` at least 85%.
- [ ] p95 scoring time under 200 ms on the developer machine (report hardware).
- [ ] Security tests listed above pass.
- [ ] No endpoint returns the raw score to unauthenticated callers.
- [ ] `python scripts/tasks.py serve` starts the backend (in-memory store, SQLite) and `/v1/health` reports the loaded model versions. Optional: a docker-compose profile with Redis + PostgreSQL also works.

---

# Handoff

## Last completed task
- **ID:** P5-14 (completing Phase 5: P5-01..P5-14)
- **Branch:** main
- **Summary:** Completed all remaining Phase 5 tasks (`P5-04`, `P5-06`, `P5-07`, `P5-08`, `P5-09`, `P5-10`, `P5-11`, `P5-12`, `P5-13`, `P5-14`) for the FastAPI risk-scoring and token backend:
  - **`P5-04` (`backend/app/scoring.py`, `backend/tests/test_scoring.py`)**: Startup ONNX model loading (`mouse-v1`, `keyboard-v1`, `fusion-v1`), metadata schema/version validation, feature extraction via `botguard_ml.features`, calibration, missing-modality-safe score fusion, rule combination (`R01..R14`), and top-3 feature attribution (27 tests).
  - **`P5-06` (`backend/app/tokens.py`, `backend/tests/test_tokens.py`)**: JWT human-token issuance and single-use `jti` verification supporting `HS256`, `RS256`, and `ES256` with action binding (11 tests).
  - **`P5-07` (`backend/app/ratelimit.py`, `backend/tests/test_ratelimit.py`)**: Sliding-window rate limiting per coarse IP bucket (`/24` IPv4, `/48` IPv6) and session ID across `/v1/nonce`, `/v1/assess`, and `/v1/assess/challenge` (4 tests).
  - **`P5-08` (`backend/app/db.py`, `backend/migrations/versions/0001_initial_schema.py`, `backend/tests/test_db.py`)**: SQLAlchemy 2.0 `assessments` and `challenges` tables, raw-trace prohibition (`sanitize_derived_features`), optional TTL-limited feature storage, and in-memory write buffering when DB is unreachable (4 tests).
  - **`P5-09`..`P5-13` (`backend/app/main.py`, `backend/tests/test_api.py`, `docs/architecture.md`, `docs/api.md`)**: FastAPI service with `GET /v1/nonce`, `POST /v1/assess`, `POST /v1/assess/challenge`, `POST /v1/token/verify`, `GET /v1/health`, 64 KB body-size cap (`MaxBodySizeMiddleware`), `require_human_token(action)` dependency, configurable degraded-mode fail-safe policy, privacy-safe structured logging, and 12 end-to-end API/security tests.
  - **`P5-14` (`backend/bench_scoring.py`, `results/system/scoring_latency.json`, `scripts/tasks.py`)**: 1,000-call latency micro-benchmark (`p50 = 1.650 ms`, `p95 = 15.161 ms < 200 ms`, `p99 = 22.069 ms`, `325.6 req/s`) and `python scripts/tasks.py serve` command.

## Current / next task
- **ID:** P6-01
- **Status:** TODO
- **Phase file:** `docs/plan/phase_6.md`
- **Exact next step:**
  1. Read `docs/plan/phase_6.md` for `P6-01` (`SDK package and CI`).
  2. Set up the TypeScript browser SDK package under `sdk/` with build, lint, test, and bundle-size scripts.

## Files touched in the last session
- `backend/app/scoring.py`
- `backend/app/tokens.py`
- `backend/app/ratelimit.py`
- `backend/app/db.py`
- `backend/app/main.py`
- `backend/migrations/versions/0001_initial_schema.py`
- `backend/bench_scoring.py`
- `backend/tests/test_scoring.py`
- `backend/tests/test_tokens.py`
- `backend/tests/test_ratelimit.py`
- `backend/tests/test_db.py`
- `backend/tests/test_api.py`
- `docs/architecture.md`
- `docs/api.md`
- `results/system/scoring_latency.json`
- `scripts/tasks.py`
- `PROGRESS.md`
- `HANDOFF.md`

## Commands run and results
- `ml\.venv\Scripts\python.exe scripts\tasks.py lint` -> exit code 0 (`All checks passed!`, 0 ruff or mypy issues across `ml` and `backend`).
- `ml\.venv\Scripts\python.exe scripts\tasks.py test-fast` -> exit code 0 (66 passed in `ml`, 335 passed in `backend`).
- `backend\.venv\Scripts\python.exe backend\bench_scoring.py` -> exit code 0 (`p50=1.650 ms | p95=15.161 ms | p99=22.069 ms`, saved to `results/system/scoring_latency.json`).

## Known issues / open questions
- None. All Phase 0–5 deliverables, lint checks, and tests pass.

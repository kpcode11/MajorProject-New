# Handoff

**Updated:** 2026-11-14 15:11  |  **By:** Antigravity  |  **Branch:** phase-9-dashboard-privacy  |  **Last commit:** see `git log -1`

## Current task
- ID: P9-07 — Privacy impact assessment (`docs/privacy_impact.md`)
- State: `DONE` (next task is **P9-08** — `Optional local feature extraction` [Stretch] or **P9-09** — `Accessibility audit`)

## Done in Phase 9 so far
- Recorded human decision in `docs/decision_log.md` to skip Phase 8 (`P8-*` marked `SKIPPED` in `PROGRESS.md`) and proceed directly to Phase 9 (`phase-9-dashboard-privacy`), using `supabase/DESIGN.md` for the Phase 9 Admin Dashboard UI (`P9-02`).
- **P9-01 (`c7073d9`):** Added `ADMIN_API_KEY` in `backend/app/config.py`, `backend/app/admin.py` (`create_admin_router`, `require_admin_api_key`), derived feature propagation in `backend/app/scoring.py` and `backend/app/main.py`, feedback/purge helpers in `backend/app/db.py`, and 4 unit tests in `backend/tests/test_admin_api.py`.
- **P9-02 (`affede1`):** Implemented the 6 Admin Dashboard views in `portal/src/pages/AdminDashboardPage.tsx`, `portal/src/adminApi.ts`, `portal/src/designTokens.ts`, `portal/src/dashboard/RechartsCompat.tsx`, and `dashboard/`.
- **P9-03 (`143026b`):** Added `portal/test/dashboard.test.tsx` and `backend/tests/test_dashboard_smoke.py`.
- **P9-04 (`7f10bd9`):** Implemented `backend/app/retention.py` (`run_retention_purge`, `RetentionScheduler`, `FakeClock`, `SystemClock`, `PurgeResult`, and CLI `python -m app.retention --once`), added `RETENTION_PURGE_INTERVAL_SECONDS` in `backend/app/config.py`, wired lifespan scheduling in `backend/app/main.py` and `POST /admin/privacy/purge` in `backend/app/admin.py`, and added 6 unit tests in `backend/tests/test_retention.py`.
- **P9-05 (`c965218`):** Implemented in-memory rotating per-page-load session identifiers in the SDK (`generateSessionId`, `SESSION_ROTATION_MS`, `X-Session-Id` header in `sdk/src/index.ts` and `sdk/src/transport.ts`) and daily-rotated session hashing (`daily_session_salt`, `make_session_hash`, coarse `/24` & `/48` IP buckets in `backend/app/nonce.py` and `backend/app/main.py`), verified by `backend/tests/test_session_privacy.py` and `sdk/test/api.test.ts`.
- **P9-06 (`ee236bf`):** Added `backend/tests/test_privacy_scan.py` to execute end-to-end portal (`otp_request`, `details_update`, `centre_search`), step-up challenge, bot rejection, and extra-field form injection flows, then scan every database table/column/cell and structured log line to verify zero leakage of typed characters, form values, full IPs, or persistent device identifiers.
- **P9-07:** Wrote `docs/privacy_impact.md` documenting purpose, necessity, less-invasive alternatives considered, and retention TTLs for every signal group (`EnvSignals`, `MouseBehaviour`, `KeyBehaviour`, `TimingSignals`, network/nonces/rotating session hashes, challenge telemetry, and portal metadata), plus explicit UIDAI/DPDP Act 2023-style engineering assumptions and legal review caveats.

## Exact next step
- Start **P9-08** (`Optional local feature extraction` — stretch) or **P9-09** (`Accessibility audit`: run axe-core on portal and challenge pages and fix any issues).

## Files touched (recent)
- `docs/privacy_impact.md`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/status.py
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast

## Known problems / gotchas
- Always use `_AsgiTestClient` from `test_api.py` in backend unit tests (never `fastapi.testclient.TestClient`, which hangs inside the Windows sandbox due to `anyio` socketpair creation).
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

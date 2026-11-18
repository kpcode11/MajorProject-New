# Handoff

**Updated:** 2026-11-18 19:47  |  **By:** Antigravity  |  **Branch:** phase-9-dashboard-privacy  |  **Last commit:** see `git log -1`

## Current task
- ID: P9-13 — Accessibility limitations
- State: `DONE` (all core Phase 9 tasks `P9-01`..`P9-13` are `DONE`; next optional tasks are **P9-14** / **P9-15** or Phase 10 **P10-01** — `Reproducible full evaluation`)

## Done in Phase 9 so far
- Recorded human decision in `docs/decision_log.md` to skip Phase 8 (`P8-*` marked `SKIPPED` in `PROGRESS.md`) and proceed directly to Phase 9 (`phase-9-dashboard-privacy`), using `supabase/DESIGN.md` for the Phase 9 Admin Dashboard UI (`P9-02`).
- **P9-01 (`c7073d9`):** Added `ADMIN_API_KEY` in `backend/app/config.py`, `backend/app/admin.py` (`create_admin_router`, `require_admin_api_key`), derived feature propagation in `backend/app/scoring.py` and `backend/app/main.py`, feedback/purge helpers in `backend/app/db.py`, and 4 unit tests in `backend/tests/test_admin_api.py`.
- **P9-02 (`affede1`):** Implemented the 6 Admin Dashboard views in `portal/src/pages/AdminDashboardPage.tsx`, `portal/src/adminApi.ts`, `portal/src/designTokens.ts`, `portal/src/dashboard/RechartsCompat.tsx`, and `dashboard/`.
- **P9-03 (`143026b`):** Added `portal/test/dashboard.test.tsx` and `backend/tests/test_dashboard_smoke.py`.
- **P9-04 (`7f10bd9`):** Implemented `backend/app/retention.py` (`run_retention_purge`, `RetentionScheduler`, `FakeClock`, `SystemClock`, `PurgeResult`, and CLI `python -m app.retention --once`), added `RETENTION_PURGE_INTERVAL_SECONDS` in `backend/app/config.py`, wired lifespan scheduling in `backend/app/main.py` and `POST /admin/privacy/purge` in `backend/app/admin.py`, and added 6 unit tests in `backend/tests/test_retention.py`.
- **P9-05 (`c965218`):** Implemented in-memory rotating per-page-load session identifiers in the SDK (`generateSessionId`, `SESSION_ROTATION_MS`, `X-Session-Id` header in `sdk/src/index.ts` and `sdk/src/transport.ts`) and daily-rotated session hashing (`daily_session_salt`, `make_session_hash`, coarse `/24` & `/48` IP buckets in `backend/app/nonce.py` and `backend/app/main.py`), verified by `backend/tests/test_session_privacy.py` and `sdk/test/api.test.ts`.
- **P9-06 (`ee236bf`):** Added `backend/tests/test_privacy_scan.py` to execute end-to-end portal (`otp_request`, `details_update`, `centre_search`), step-up challenge, bot rejection, and extra-field form injection flows, then scan every database table/column/cell and structured log line to verify zero leakage of typed characters, form values, full IPs, or persistent device identifiers.
- **P9-07 (`39b397d`):** Wrote `docs/privacy_impact.md` documenting purpose, necessity, less-invasive alternatives considered, and retention TTLs for every signal group, plus explicit UIDAI/DPDP Act 2023-style engineering assumptions and legal review caveats.
- **P9-08 (`ffbf0e5`):** Implemented local feature extraction mode (`sendRawTrace=false`) in `sdk/src/features.ts`, `sdk/src/config.ts`, and `sdk/src/index.ts`, added backend support for `mouse.features` / `mouse.feature_windows` and `keys.features` in `backend/app/schemas.py` and `backend/app/scoring.py`, verified $10^{-9}$ golden parity across Python and TypeScript fixtures (`sdk/test/features_parity.test.ts`, `sdk/test/fixtures/golden_feature_fixtures.json`, `backend/tests/test_local_features.py`), and saved model evaluation results to `results/system/local_features_parity.json`.
- **P9-09 (`d3606f9`):** Added `axe-core` and WCAG 2.1 AA contrast audit in `portal/test/accessibility.test.tsx` (auditing 11 states across Landing, Resident Login, Update Details, Centre Search, Admin Dashboard, and Step-up Challenge dialog) and saved results to `results/system/axe_audit.json`.
- **P9-10 (`d23a26f`):** Added `portal/test/keyboard_e2e.test.tsx` (3 keyboard-only E2E tests) and `test_e2e_keyboard_only_login_otp_flow_with_tab_enter_and_stepup` in `backend/tests/test_e2e_portal.py`.
- **P9-11 (`1305d22`):** Documented NVDA / Windows Narrator / VoiceOver smoke-test walkthrough in `docs/accessibility.md` and added ARIA landmark/live-region/progressbar announcement smoke test in `portal/test/accessibility.test.tsx`.
- **P9-12 (`4521b1e`):** Enforced missing-mouse valid-keyboard fairness cap (`MISSING_MOUSE_VALID_KB_MAX_SCORE=0.50`, `MIN_TYPING_WINDOW_KEYS=10`) in `backend/app/scoring.py` and added 6 E2E tests in `backend/tests/test_missing_modality_e2e.py`.
- **P9-13:** Documented missing-modality fairness rules and 6 known accessibility limitations in `docs/accessibility.md`.

## Exact next step
- Decide whether to skip optional trajectory neural model tasks (**P9-14** / **P9-15**) and proceed to Phase 10 (**P10-01** — `Reproducible full evaluation`).

## Files touched (recent)
- `docs/accessibility.md`, `backend/app/scoring.py`, `backend/tests/test_missing_modality_e2e.py`, `portal/test/accessibility.test.tsx`, `portal/test/keyboard_e2e.test.tsx`, `PROGRESS.md`, `HANDOFF.md`

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

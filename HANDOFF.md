# Handoff

**Updated:** 2026-11-16 11:55  |  **By:** Antigravity  |  **Branch:** phase-9-dashboard-privacy  |  **Last commit:** see `git log -1`

## Current task
- ID: P9-09 — Accessibility audit
- State: `DONE` (next task is **P9-10** — `Keyboard-only portal test`)

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
- **P9-09:** Added `axe-core` and WCAG 2.1 AA contrast audit in `portal/test/accessibility.test.tsx` (auditing 11 states across Landing, Resident Login, Update Details, Centre Search, Admin Dashboard, and Step-up Challenge dialog) and saved results to `results/system/axe_audit.json`. Fixed WCAG AA button/text colour contrast (`#0369a1` primary portal buttons, `#157347` `primaryText` on light canvas), added skip-to-main-content link and focus-visible outlines in `portal/src/App.tsx`, added `aria-invalid` / `aria-describedby` error associations in portal forms, added `scope="col"` and keyboard row selection (`tabIndex={0}`, `Enter`/`Space`) in `portal/src/pages/AdminDashboardPage.tsx`, and aligned `aria-label` attributes with visible button labels (WCAG 2.5.3) in `sdk/src/challenge.ts`.

## Exact next step
- Start **P9-10** (`Keyboard-only portal test`): complete the login/OTP flow with keyboard navigation only in an E2E test.

## Files touched (recent)
- `portal/package.json`, `portal/package-lock.json`, `portal/src/App.tsx`, `portal/src/designTokens.ts`, `portal/src/pages/LandingPage.tsx`, `portal/src/pages/ResidentLoginPage.tsx`, `portal/src/pages/UpdateDetailsPage.tsx`, `portal/src/pages/CentreSearchPage.tsx`, `portal/src/pages/AdminDashboardPage.tsx`, `portal/test/accessibility.test.tsx`, `sdk/src/challenge.ts`, `results/system/axe_audit.json`, `results/system/sdk_size.json`, `data/fixtures/backend_contract_schema.json`, `PROGRESS.md`, `HANDOFF.md`

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

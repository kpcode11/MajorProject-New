# Handoff

**Updated:** 2026-11-08 22:02  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-04 — Portal API statistics (`backend/app/portal.py`)
- State: not started (`TODO`; P7-03 is DONE)

## Done in Phase 7 so far
- **P7-01 (`556745c`):** Created `portal/` React 19 + Vite 8 + TypeScript 6 + Vitest 5 + ESLint 10 + Prettier scaffold linking `@botguard/sdk` (`file:../sdk`). Added prominent `"DEMO — not a government portal"` disclaimer banner, `<BotGuardProvider>` root wrapper with reactive `running` state in `sdk/src/react/index.tsx`, Vite `/v1` and `/portal-api` dev proxy to `http://127.0.0.1:8000`, `portal/test/app.test.tsx`, `scripts/tasks.py` integration, and `.github/workflows/ci.yml` `portal` job.
- **P7-02 (`47e287c`):** Added mock portal pages in `portal/src/pages/` (`LandingPage.tsx`, `ResidentLoginPage.tsx` with identifier text field and **Send OTP** button, `UpdateDetailsPage.tsx` form, `CentreSearchPage.tsx`), client helper `portal/src/api.ts` (`callPortalEndpoint`), top/card navigation in `portal/src/App.tsx`, and 4 unit tests in `portal/test/app.test.tsx`.
- **P7-03:** Added `backend/app/portal.py` (`create_portal_router`) mounting `POST /portal-api/otp/request`, `POST /portal-api/details/update`, and `POST /portal-api/centres/search` protected by `require_human_token("otp_request" | "details_update" | "centre_search")`, wired into `create_app()` in `backend/app/main.py`, aligned portal page action names (`otp_request`, `details_update`, `centre_search`), and added `backend/tests/test_portal_api.py`.

## Exact next step
- Start **P7-04** (`Portal API statistics`): add a counter endpoint `GET /portal-api/stats` showing accepted vs rejected calls (overall and per action/endpoint) for use in the demo, and add unit tests in `backend/tests/test_portal_api.py`.

## Files touched (recent)
- `backend/app/portal.py`, `backend/tests/test_portal_api.py` (new); `backend/app/main.py`, `backend/tests/test_api.py`, `portal/src/pages/LandingPage.tsx`, `portal/src/pages/ResidentLoginPage.tsx`, `portal/src/pages/UpdateDetailsPage.tsx`, `portal/test/app.test.tsx`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast
    cd portal; npm test

## Known problems / gotchas
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

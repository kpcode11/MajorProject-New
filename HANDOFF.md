# Handoff

**Updated:** 2026-11-08 21:53  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-03 — Protected portal API (`backend/app/`)
- State: not started (`TODO`; P7-02 is DONE)

## Done in Phase 7 so far
- **P7-01 (`556745c`):** Created `portal/` React 19 + Vite 8 + TypeScript 6 + Vitest 5 + ESLint 10 + Prettier scaffold linking `@botguard/sdk` (`file:../sdk`). Added prominent `"DEMO — not a government portal"` disclaimer banner, `<BotGuardProvider>` root wrapper with reactive `running` state in `sdk/src/react/index.tsx`, Vite `/v1` and `/portal-api` dev proxy to `http://127.0.0.1:8000`, `portal/test/app.test.tsx`, `scripts/tasks.py` integration, and `.github/workflows/ci.yml` `portal` job.
- **P7-02:** Added mock portal pages in `portal/src/pages/` (`LandingPage.tsx`, `ResidentLoginPage.tsx` with identifier text field and **Send OTP** button, `UpdateDetailsPage.tsx` form, `CentreSearchPage.tsx`), client helper `portal/src/api.ts` (`callPortalEndpoint`), top/card navigation in `portal/src/App.tsx`, and 4 unit tests in `portal/test/app.test.tsx`.

## Exact next step
- Start **P7-03** (`Protected portal API`): add FastAPI routes under `/portal-api/`:
  - `POST /portal-api/otp/request` (`action="login"`)
  - `POST /portal-api/details/update` (`action="update_details"`)
  - `POST /portal-api/centres/search` (`action="centre_search"`)
  Each route requires a valid `X-Human-Token` for its action via `require_human_token(action)` (and prepares for `P7-04` `/portal-api/stats` and `P7-05` protection mode switch). Add unit tests in `backend/tests/test_portal_api.py`.

## Files touched (recent)
- `portal/src/api.ts`, `portal/src/pages/LandingPage.tsx`, `portal/src/pages/ResidentLoginPage.tsx`, `portal/src/pages/UpdateDetailsPage.tsx`, `portal/src/pages/CentreSearchPage.tsx` (new); `portal/src/App.tsx`, `portal/test/app.test.tsx`, `PROGRESS.md`, `HANDOFF.md`

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

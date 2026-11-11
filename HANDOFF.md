# Handoff

**Updated:** 2026-11-11 13:14  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-06 — Accessible step-up UI (`sdk/src/challenge.ts`, `portal/src/`)
- State: not started (`TODO`; P7-05 is DONE)

## Done in Phase 7 so far
- **P7-01 (`556745c`):** Created `portal/` React 19 + Vite 8 + TypeScript 6 + Vitest 5 + ESLint 10 + Prettier scaffold linking `@botguard/sdk` (`file:../sdk`). Added prominent `"DEMO — not a government portal"` disclaimer banner, `<BotGuardProvider>` root wrapper with reactive `running` state in `sdk/src/react/index.tsx`, Vite `/v1` and `/portal-api` dev proxy to `http://127.0.0.1:8000`, `portal/test/app.test.tsx`, `scripts/tasks.py` integration, and `.github/workflows/ci.yml` `portal` job.
- **P7-02 (`47e287c`):** Added mock portal pages in `portal/src/pages/` (`LandingPage.tsx`, `ResidentLoginPage.tsx` with identifier text field and **Send OTP** button, `UpdateDetailsPage.tsx` form, `CentreSearchPage.tsx`), client helper `portal/src/api.ts` (`callPortalEndpoint`), top/card navigation in `portal/src/App.tsx`, and 4 unit tests in `portal/test/app.test.tsx`.
- **P7-03 (`1d9bd4a`):** Added `backend/app/portal.py` (`create_portal_router`) mounting `POST /portal-api/otp/request`, `POST /portal-api/details/update`, and `POST /portal-api/centres/search` protected by `require_human_token("otp_request" | "details_update" | "centre_search")`, wired into `create_app()` in `backend/app/main.py`, aligned portal page action names, and added `backend/tests/test_portal_api.py`.
- **P7-04 (`4790ef6`):** Added `PortalStatsTracker` and `GET /portal-api/stats` in `backend/app/portal.py` and `backend/app/main.py` tracking `accepted`, `rejected`, `total`, `by_action`, and `by_reason` counters across all `/portal-api/*` protected routes.
- **P7-05:** Added `PROTECTION_MODE` (`off | passive`, default `passive`) in `backend/app/config.py`, bypassed token enforcement in `require_human_token` when `protection_mode == "off"`, and exposed `protection_mode` in `GET /portal-api/stats`; verified with `test_protection_mode_off_allows_unauthenticated_portal_calls`.

## Exact next step
- Start **P7-06** (`Accessible step-up UI`): verify and wire the default **press-and-hold** button step-up UI (`0.8–1.5 s` server-chosen random hold duration) and single-click keyboard alternative path (Space/Enter activation) in the mock portal (`portal/`) and SDK (`sdk/src/challenge.ts`), with no image or text puzzles, plus unit tests in `portal/test/`.

## Files touched (recent)
- `backend/app/config.py`, `backend/app/main.py`, `backend/app/portal.py`, `backend/tests/test_portal_api.py`, `PROGRESS.md`, `HANDOFF.md`

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

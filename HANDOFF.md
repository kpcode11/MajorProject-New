# Handoff

**Updated:** 2026-11-11 13:38  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-10 — Challenge tests (`backend/tests/test_api.py`, `sdk/test/challenge.test.ts`)
- State: not started (`TODO`; P7-09 is DONE)

## Done in Phase 7 so far
- **P7-01 (`556745c`):** Created `portal/` React 19 + Vite 8 + TypeScript 6 + Vitest 5 + ESLint 10 + Prettier scaffold linking `@botguard/sdk` (`file:../sdk`).
- **P7-02 (`47e287c`):** Added mock portal pages (`LandingPage.tsx`, `ResidentLoginPage.tsx` with identifier text field and **Send OTP** button, `UpdateDetailsPage.tsx` form, `CentreSearchPage.tsx`), client helper `portal/src/api.ts`, and 4 unit tests in `portal/test/app.test.tsx`.
- **P7-03 (`1d9bd4a`):** Added `backend/app/portal.py` (`create_portal_router`) mounting `POST /portal-api/otp/request`, `POST /portal-api/details/update`, and `POST /portal-api/centres/search` protected by `require_human_token`.
- **P7-04 (`4790ef6`):** Added `PortalStatsTracker` and `GET /portal-api/stats` tracking `accepted`, `rejected`, `total`, `by_action`, and `by_reason` counters.
- **P7-05 (`5f02c1e`):** Added `PROTECTION_MODE` (`off | passive`, default `passive`) in `backend/app/config.py`, bypassed token enforcement when `off`, and exposed `protection_mode` in `GET /portal-api/stats`.
- **P7-06 (`5af2f3a`):** Enhanced the default accessible press-and-hold step-up UI (`sdk/src/challenge.ts`) with `data-testid` hooks, `Space`/`Enter` single-press keyboard alternative handler (`onKbAltKeyDown`), visible `:focus-visible` ring, Tab focus trapping, and focus restoration, and verified end-to-end step-up interaction in `portal/test/app.test.tsx`.
- **P7-07 (`554c422`):** Enhanced `POST /v1/assess/challenge` in `backend/app/main.py` to re-score using the original session's `original_score` blended with any challenge `env`/`behaviour` features and hold timing, returning `allow` (with token) or `deny`.
- **P7-08 (`97d96b7`):** Added configurable `RATE_LIMIT_CHALLENGE_PER_MIN`, `RATE_LIMIT_CHALLENGE_SESSION_PER_MIN`, and `CHALLENGE_TTL_SECONDS`, enforced per-session and per-IP-bucket sliding-window rate limits on `POST /v1/assess/challenge`, and verified single-use `challenge_id` consumption.
- **P7-09:** Added comprehensive accessibility unit tests in `sdk/test/challenge.test.ts` verifying ARIA roles/labels (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`, `role="progressbar"`, `role="status"`), visible `:focus-visible` outline, initial focus, `Tab`/`Shift+Tab` modal focus trapping, focus restoration on close, and keyboard single-press `Space`/`Enter` completion without time pressure.

## Exact next step
- Start **P7-10** (`Challenge tests`): add dedicated challenge test suite covering all required scenarios in `docs/plan/phase_7.md` (`challenge success, timeout, replay, too-fast completion, wrong id`) across backend (`backend/tests/test_challenge.py`) and SDK (`sdk/test/challenge.test.ts`).

## Files touched (recent)
- `sdk/test/challenge.test.ts`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast
    cd sdk; npm test

## Known problems / gotchas
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

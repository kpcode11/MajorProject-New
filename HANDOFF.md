# Handoff

**Updated:** 2026-11-11 13:34  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-09 — Challenge accessibility (`sdk/src/challenge.ts`, `sdk/test/challenge.test.ts`, `portal/test/app.test.tsx`)
- State: not started (`TODO`; P7-08 is DONE)

## Done in Phase 7 so far
- **P7-01 (`556745c`):** Created `portal/` React 19 + Vite 8 + TypeScript 6 + Vitest 5 + ESLint 10 + Prettier scaffold linking `@botguard/sdk` (`file:../sdk`). Added prominent `"DEMO — not a government portal"` disclaimer banner, `<BotGuardProvider>` root wrapper, Vite `/v1` and `/portal-api` dev proxy, `portal/test/app.test.tsx`, `scripts/tasks.py` integration, and `.github/workflows/ci.yml` `portal` job.
- **P7-02 (`47e287c`):** Added mock portal pages (`LandingPage.tsx`, `ResidentLoginPage.tsx` with identifier text field and **Send OTP** button, `UpdateDetailsPage.tsx` form, `CentreSearchPage.tsx`), client helper `portal/src/api.ts`, and 4 unit tests in `portal/test/app.test.tsx`.
- **P7-03 (`1d9bd4a`):** Added `backend/app/portal.py` (`create_portal_router`) mounting `POST /portal-api/otp/request`, `POST /portal-api/details/update`, and `POST /portal-api/centres/search` protected by `require_human_token`.
- **P7-04 (`4790ef6`):** Added `PortalStatsTracker` and `GET /portal-api/stats` tracking `accepted`, `rejected`, `total`, `by_action`, and `by_reason` counters.
- **P7-05 (`5f02c1e`):** Added `PROTECTION_MODE` (`off | passive`, default `passive`) in `backend/app/config.py`, bypassed token enforcement when `off`, and exposed `protection_mode` in `GET /portal-api/stats`.
- **P7-06 (`5af2f3a`):** Enhanced the default accessible press-and-hold step-up UI (`sdk/src/challenge.ts`) with `data-testid` hooks, `Space`/`Enter` single-press keyboard alternative handler (`onKbAltKeyDown`), visible `:focus-visible` ring, Tab focus trapping, and focus restoration, and verified end-to-end step-up interaction in `portal/test/app.test.tsx`.
- **P7-07 (`554c422`):** Enhanced `POST /v1/assess/challenge` in `backend/app/main.py` to re-score using the original session's `original_score` blended with any challenge `env`/`behaviour` features and hold timing, returning `allow` (with token) or `deny`.
- **P7-08:** Added configurable `RATE_LIMIT_CHALLENGE_PER_MIN` (per IP bucket, default 10), `RATE_LIMIT_CHALLENGE_SESSION_PER_MIN` (per session, default 5), and `CHALLENGE_TTL_SECONDS` (default 60) in `backend/app/config.py`, wired into `RateLimiter.check_challenge` (`backend/app/ratelimit.py`) and `POST /v1/assess` (`backend/app/main.py`), and verified single-use `challenge_id` consumption and 429 rate-limiting in `backend/tests/test_ratelimit.py` and `backend/tests/test_api.py`.

## Exact next step
- Start **P7-09** (`Challenge accessibility`): verify and test labelled controls (`aria-labelledby`, `aria-describedby`, `aria-label`, `role="progressbar"`, `role="status"`), focus handling (initial focus, Tab/Shift+Tab trapping, focus restoration), visible focus ring, keyboard path (`Space`/`Enter` hold and single-press keyboard alternative), and absence of countdown time pressure in `sdk/src/challenge.ts` and `sdk/test/challenge.test.ts`.

## Files touched (recent)
- `backend/app/config.py`, `backend/app/ratelimit.py`, `backend/app/main.py`, `backend/tests/test_ratelimit.py`, `backend/tests/test_api.py`, `PROGRESS.md`, `HANDOFF.md`

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

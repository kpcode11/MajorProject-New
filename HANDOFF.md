# Handoff

**Updated:** 2026-11-11 13:46  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-12 — Simulator tier 1 (`simulator/tiers.py` or `simulator/tier1_http.py`)
- State: not started (`TODO`; P7-11 is DONE)

## Done in Phase 7 so far
- **P7-01 (`556745c`):** Created `portal/` React 19 + Vite 8 + TypeScript 6 + Vitest 5 + ESLint 10 + Prettier scaffold linking `@botguard/sdk` (`file:../sdk`).
- **P7-02 (`47e287c`):** Added mock portal pages (`LandingPage.tsx`, `ResidentLoginPage.tsx` with identifier text field and **Send OTP** button, `UpdateDetailsPage.tsx` form, `CentreSearchPage.tsx`), client helper `portal/src/api.ts`, and 4 unit tests in `portal/test/app.test.tsx`.
- **P7-03 (`1d9bd4a`):** Added `backend/app/portal.py` (`create_portal_router`) mounting `POST /portal-api/otp/request`, `POST /portal-api/details/update`, and `POST /portal-api/centres/search` protected by `require_human_token`.
- **P7-04 (`4790ef6`):** Added `PortalStatsTracker` and `GET /portal-api/stats` tracking `accepted`, `rejected`, `total`, `by_action`, and `by_reason` counters.
- **P7-05 (`5f02c1e`):** Added `PROTECTION_MODE` (`off | passive`, default `passive`) in `backend/app/config.py`, bypassed token enforcement when `off`, and exposed `protection_mode` in `GET /portal-api/stats`.
- **P7-06 (`5af2f3a`):** Enhanced the default accessible press-and-hold step-up UI (`sdk/src/challenge.ts`) with `data-testid` hooks, `Space`/`Enter` single-press keyboard alternative handler (`onKbAltKeyDown`), visible `:focus-visible` ring, Tab focus trapping, and focus restoration, and verified end-to-end step-up interaction in `portal/test/app.test.tsx`.
- **P7-07 (`554c422`):** Enhanced `POST /v1/assess/challenge` in `backend/app/main.py` to re-score using the original session's `original_score` blended with any challenge `env`/`behaviour` features and hold timing, returning `allow` (with token) or `deny`.
- **P7-08 (`97d96b7`):** Added configurable `RATE_LIMIT_CHALLENGE_PER_MIN`, `RATE_LIMIT_CHALLENGE_SESSION_PER_MIN`, and `CHALLENGE_TTL_SECONDS`, enforced per-session and per-IP-bucket sliding-window rate limits on `POST /v1/assess/challenge`, and verified single-use `challenge_id` consumption.
- **P7-09 (`06bbafc`):** Verified ARIA labels/roles, initial focus, `Tab`/`Shift+Tab` modal focus trap, focus restoration on close, visible `:focus-visible` outline, and keyboard `Space`/`Enter` single-press path without countdown pressure in `sdk/test/challenge.test.ts`.
- **P7-10 (`20615d7`):** Added dedicated step-up challenge test suite `backend/tests/test_challenge.py` and timeout test in `sdk/test/challenge.test.ts`.
- **P7-11:** Added `simulator/allowlist.txt`, `simulator/safety.py` (`validate_target_url`, `load_allowlist`, `extract_host`, `SimulatorTargetError`), `simulator/__init__.py`, `backend/tests/test_simulator_safety.py` (16 unit tests), and wired `simulator/` into `scripts/tasks.py` `lint()`.

## Exact next step
- Start **P7-12** (`Simulator tier 1`): implement Tier 1 plain HTTP client posting directly to the protected portal endpoint (`/portal-api/otp/request`) without a browser, enforcing `validate_target_url` first, and recording the outcome (`allowed` when protection is `off`, `blocked-at-api` / `401` when protection is `passive`). Add unit tests.

## Files touched (recent)
- `simulator/allowlist.txt`, `simulator/__init__.py`, `simulator/safety.py`, `backend/tests/test_simulator_safety.py` (new); `simulator/.gitkeep` (deleted); `scripts/tasks.py`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast

## Known problems / gotchas
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

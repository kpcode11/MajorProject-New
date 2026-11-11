# Handoff

**Updated:** 2026-11-11 15:34  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-17 — Human-like reference run (`simulator/reference_human.py`)
- State: `TODO`

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
- **P7-11 (`b65d5ae`):** Added `simulator/allowlist.txt`, `simulator/safety.py` (`validate_target_url`, `load_allowlist`, `extract_host`, `SimulatorTargetError`), `simulator/__init__.py`, `backend/tests/test_simulator_safety.py` (16 unit tests), and wired `simulator/` into `scripts/tasks.py` `lint()`.
- **P7-12 (`7b234d9`):** Added `simulator/tier1_http.py` (`run_tier1_session`, `SimRunResult`, `SimOutcome`, `DEFAULT_TIER1_USER_AGENTS`), exported them in `simulator/__init__.py`, and added unit tests in `backend/tests/test_simulator_tier1.py`.
- **P7-13 (`f5e438f`):** Added `simulator/tier2_playwright.py` (`run_tier2_session`, `drive_tier2_playwright_page`, `build_tier2_env_signals`, `build_tier2_behaviour_payload`, `PlaywrightPageLike`) and 3 unit tests in `backend/tests/test_simulator_tier2.py`.
- **P7-14 (`ea2e017`):** Added `simulator/tier3_stealth.py` (`run_tier3_session`, `drive_tier3_playwright_page`, `apply_tier3_context_adjustments`, `build_tier3_env_signals`, `build_tier3_behaviour_payload`, `TIER3_INIT_SCRIPT`, `TIER3_PROFILES`) and 4 unit tests in `backend/tests/test_simulator_tier3.py`.
- **P7-15 (`c7dd2aa`):** Added `simulator/humanlike.py` (`bezier_path`, `generate_humanlike_mouse_trajectory`, `generate_humanlike_key_events`) and `simulator/tier4_humanlike.py` (`run_tier4_session`, `drive_tier4_playwright_page`) and 4 unit tests in `backend/tests/test_simulator_tier4.py`.
- **P7-16:** Added `simulator/run_all.py` (`run_all_tiers`, `run_randomized_tier_session`, `summarize_sim_runs`, `write_sim_runs_jsonl`), generated `results/system/sim_runs.jsonl` (200 sessions across Tiers 1-4 for `off` and `passive`), and added 2 unit tests in `backend/tests/test_simulator_run_all.py`.

## Exact next step
- Start **P7-17** (`Human-like reference run`): implement a scripted "human-like reference" run (and keyboard-only accessibility reference run) using recorded or hand-written realistic input events to show that a normal session passes (clearly labelled as a demo script, not a validation dataset).

## Files touched (recent)
- `simulator/run_all.py`, `backend/tests/test_simulator_run_all.py`, `results/system/sim_runs.jsonl` (new); `simulator/__init__.py`, `simulator/tier1_http.py`, `simulator/tier2_playwright.py`, `PROGRESS.md`, `HANDOFF.md`

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

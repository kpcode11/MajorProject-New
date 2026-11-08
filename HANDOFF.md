# Handoff

**Updated:** 2026-11-08 21:45  |  **By:** Antigravity  |  **Branch:** phase-7-mock-portal  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-02 — Demo portal pages (`portal/src/`)
- State: not started (`TODO`; P7-01 is DONE)

## Done in Phase 7 so far
- **P7-01:** Created `portal/` React 19 + Vite 8 + TypeScript 6 + Vitest 5 + ESLint 10 + Prettier scaffold linking `@botguard/sdk` (`file:../sdk`). Added prominent `"DEMO — not a government portal"` disclaimer banner, `<BotGuardProvider>` root wrapper with reactive `running` state in `sdk/src/react/index.tsx`, Vite `/v1` and `/portal-api` dev proxy to `http://127.0.0.1:8000`, `portal/test/app.test.tsx`, `scripts/tasks.py` integration (`setup`, `lint`, `test`), and `.github/workflows/ci.yml` `portal` job.

## Exact next step
- Start **P7-02** (`Demo portal pages`): implement the mock citizen portal pages in `portal/src/`:
  1. Landing page (navigation cards + explanation of passive verification)
  2. "Resident login" page with an identifier text field and "Send OTP" button
  3. "Update details" form (mouse + keyboard heavy)
  4. "Centre search" page (rapid query endpoint targeted by bots)
  Add component/page unit tests in `portal/test/`.

## Files touched (recent)
- `portal/package.json`, `portal/package-lock.json`, `portal/tsconfig.json`, `portal/vite.config.ts`, `portal/vitest.config.ts`, `portal/eslint.config.js`, `portal/.prettierrc.json`, `portal/.prettierignore`, `portal/index.html`, `portal/src/main.tsx`, `portal/src/App.tsx`, `portal/test/app.test.tsx` (new); `portal/.gitkeep` (deleted)
- `sdk/src/react/index.tsx`, `results/system/sdk_size.json`, `scripts/tasks.py`, `.github/workflows/ci.yml`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast
    cd portal; npm test

## Known problems / gotchas
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- When `sdk/src/` changes, run `npm run build` in `sdk/` so `portal/` picks up the updated `@botguard/sdk` build.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

# Handoff

**Updated:** 2026-11-07  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-02 — Environment collector (`sdk/src/collectors/env.ts`)
- State: in progress (not started in code)

## Done in Phase 6 so far
- P6-01 DONE: `sdk/` package (Vite 8 library build ES + UMD, TypeScript 6 strict, vitest 5 + happy-dom, ESLint 10 flat config + typescript-eslint strict, Prettier). `sdk/src/config.ts` (defaults, `HARD_LIMITS` mirroring backend `schemas.py`, `resolveConfig`, `endpointUrl`), `sdk/test/config.test.ts` (12 tests). CI job `sdk` in `.github/workflows/ci.yml`. `scripts/tasks.py` `setup` runs `npm ci`, `lint` runs SDK lint+typecheck, `test`/`test-fast` run SDK tests (skipped with a notice if Node or `sdk/node_modules` is missing).
- Also fixed a pre-existing `ruff format` failure in `backend/tests/test_db.py` (trailing blank line only).

## Exact next step
- Write `sdk/src/collectors/env.ts` returning an object matching backend `EnvSignals` (Appendix B.2; field names in `backend/app/schemas.py`). Coarsen values (screen buckets, dpr/hw/memory buckets, renderer class). No fingerprint hash, no raw UA string sent. Add `sdk/test/env.test.ts`.

## Files touched (recent)
- `sdk/*` (new), `.github/workflows/ci.yml`, `scripts/tasks.py`, `backend/tests/test_db.py`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py test-fast
    cd sdk; npm run lint; npm run typecheck; npm test; npm run build

## Known problems / gotchas
- On this machine `npm install` needs network (run outside the sandbox); always run npm from `sdk/`, never the repo root.
- Git writes to `.git` need elevated permission in the agent sandbox.
- PROGRESS.md commit column for P6 tasks: fill the hash in the following task's commit.

## Dataset / long-job state
- None (Phase 6 needs no datasets).

## Questions for the human
- None.

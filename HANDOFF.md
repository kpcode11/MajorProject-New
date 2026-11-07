# Handoff

**Updated:** 2026-11-07 21:17  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-03 — Mouse collector (`sdk/src/collectors/mouse.ts`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`):** `sdk/` package skeleton (Vite 8 ES + UMD build, TypeScript 6 strict, vitest 5 + happy-dom, ESLint 10 + Prettier), `sdk/src/config.ts`, `sdk/test/config.test.ts` (12 tests), CI `sdk` job in `.github/workflows/ci.yml`, `scripts/tasks.py` integration.
- **P6-02:** `sdk/src/collectors/env.ts` and `sdk/test/env.test.ts` (20 tests). Collects Appendix B.2 coarse environment signals (`webdriver`, parsed UA family/major/OS, platform, client hints, language count & primary tag, timezone offset, screen resolution buckets, viewport/outer dimensions, DPR/CPU/memory buckets, classified WebGL renderer, plugins count, touch capability, native function integrity, localStorage availability, visibility) and `deviceClass()`. Never stores or sends raw UA/renderer strings or fingerprint hashes.

## Exact next step
- Implement `sdk/src/collectors/mouse.ts` for `P6-03`: attach passive listeners for `mousemove` (throttled to ~60 Hz / `mouseThrottleMs`), `mousedown`, `mouseup`, `click`, `wheel`; record `isTrusted`; maintain bounded ring buffers (`maxMousePoints`, `maxClicks`) trimmed to `windowMs`; output `MouseBehaviour` (`points`, `clicks`, `untrusted_count`, `wheel_events`) matching `backend/app/schemas.py`. Add `sdk/test/mouse.test.ts`.

## Files touched (recent)
- `sdk/src/collectors/env.ts` (new)
- `sdk/test/env.test.ts` (new)
- `sdk/src/index.ts`
- `PROGRESS.md`
- `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py test-fast
    cd sdk; npm run lint; npm run typecheck; npm test; npm run build

## Known problems / gotchas
- Always run `npm` commands from `sdk/`, never the repo root.
- Git writes to `.git` require elevated permission outside the sandbox on this machine.

## Dataset / long-job state
- None (Phase 6 needs no datasets).

## Questions for the human
- None.

# Handoff

**Updated:** 2026-11-08 21:16  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-13 — SDK/backend contract test (`sdk/test/contract.test.ts` + backend JSON Schema export)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`)..P6-11 (`b03e6c3`):** SDK package, config, CI `sdk` job, `env`, `mouse`, `keyboard`, `scroll`, `timing` collectors, `transport`, `BotGuard` public API, pluggable `challenge` UI, `@botguard/sdk/react` (`BotGuardProvider` & `useBotGuard`), `performance` controls, and 98 vitest tests across 11 suites.
- **P6-12:** Added `sdk/scripts/size-report.mjs` (invoked automatically by `npm run build` and `npm run size`) and generated `results/system/sdk_size.json` (plus tracked `results/system/scoring_latency.json` in `.gitignore`). Core ES bundle is `10.90 KB` gzipped (`35.06 KB` raw), UMD bundle is `10.05 KB` gzipped (`28.69 KB` raw), and React wrapper is `1.02 KB` gzipped (`3.05 KB` raw) — all well below the 30 KB gzipped target.

## Exact next step
- Implement `P6-13` (`SDK/backend contract test`): generate the canonical JSON Schema from the backend's Pydantic models (`AssessRequest`, `ChallengeAssessRequest`) and validate SDK-produced payloads (`buildAssessPayload`, `buildChallengePayload`, and live `BotGuard.assess()` / `BotGuard.runChallenge()` snapshots) against both the generated JSON Schema in `sdk/test/contract.test.ts` and the backend Pydantic validator.

## Files touched (recent)
- `sdk/scripts/size-report.mjs`, `results/system/sdk_size.json` (new); `sdk/package.json`; `sdk/vite.config.ts`; `.gitignore`; `PROGRESS.md`; `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py test-fast
    cd sdk; npm run lint; npm run typecheck; npm test; npm run build

## Known problems / gotchas
- Run `npm` only from `sdk/`. Git writes need elevated permission in the agent sandbox.
- happy-dom marks dispatched events untrusted; tests override `isTrusted` with `Object.defineProperty`.

## Dataset / long-job state
- None.

## Questions for the human
- None.

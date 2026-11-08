# Handoff

**Updated:** 2026-11-08 21:13  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-12 — SDK bundle report (`results/system/sdk_size.json`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`)..P6-10 (`30a8a73`):** SDK package, config, CI `sdk` job, `env`, `mouse`, `keyboard`, `scroll`, `timing` collectors, `transport`, `BotGuard` public API, pluggable `challenge` UI, `@botguard/sdk/react` (`BotGuardProvider` & `useBotGuard`), and `performance` controls.
- **P6-11:** Completed full SDK acceptance test suite (`sdk/test/sdk_suite.test.ts` + 10 unit/integration test files = 11 test files, 98 tests total). Verifies bounded collector outputs, zero typed-character or form-field-value exposure across typed/pasted/prefilled/autofilled inputs on `BotGuard.assess()`, mouse throttling, `< 64 KB` body cap under worst-case multi-modality stress, and zero `window`/`document` listener leaks across repeated `start()`/`stop()` cycles.

## Exact next step
- Implement `P6-12` (`SDK bundle report`): build ES module and UMD bundles, write a script (`sdk/scripts/size-report.mjs`) that computes raw and gzipped sizes for `dist/botguard.js`, `dist/botguard.umd.cjs`, and `dist/react/index.js`, and saves the report to `results/system/sdk_size.json` (verifying core gzipped size < 30 KB). Then proceed to `P6-13` (`SDK/backend contract test`).

## Files touched (recent)
- `sdk/test/sdk_suite.test.ts` (new); `PROGRESS.md`; `HANDOFF.md`

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

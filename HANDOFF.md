# Handoff

**Updated:** 2026-11-08 21:07  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-10 — SDK performance controls (`sdk/src/`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`):** `sdk/` package, `config.ts`, CI `sdk` job, `scripts/tasks.py` integration.
- **P6-02 (`d1f02a4`):** `collectors/env.ts` (coarse Appendix B.2 snapshot, `deviceClass()`).
- **CI fix (`c476a63`):** track small `backend/models/**/*.onnx`; ignore `*.db`.
- **P6-03 (`8b92328`):** `ringbuffer.ts`, `collectors/mouse.ts` (`MouseCollector`).
- **P6-04 (`115c28f`):** `collectors/keyboard.ts` (`KeyboardCollector`, `keyClass`). Backend `KeyBehaviour` gained `untrusted_count`.
- **P6-05 (`714e96c`):** `collectors/scroll.ts` (`ScrollCollector`) and `collectors/timing.ts` (`TimingCollector`).
- **P6-06 (`044bd2c`):** `src/transport.ts` (`fetchNonce`, `buildAssessPayload`, `buildChallengePayload`, `postAssess`, `postChallenge`, `safeAssess`, `safeSubmitChallenge`, `BotGuardTransportError`).
- **P6-07 (`b7676cb`):** `src/index.ts` (`BotGuardClient` class and `BotGuard` singleton facade).
- **P6-08 (`6c46c30`):** `src/challenge.ts` (`renderPressHoldChallenge`, `createChallengeHandler`, `defaultPressHoldRenderer`, `BotGuardChallengeCancelledError`).
- **P6-09:** `src/react/index.tsx` (`BotGuardProvider` and `useBotGuard()` hook exported at `@botguard/sdk/react` with optional React peer dependency, keeping zero runtime dependencies in the core bundle). Added `sdk/test/react.test.tsx` (3 tests; 91 SDK tests total).

## Exact next step
- Implement `P6-10` (`SDK performance controls`): verify and complete passive listener enforcement, throttling, `requestIdleCallback` / Web Worker aggregation helpers, bounded ring buffers, and explicit listener-leak / memory-clearing guarantees on `stop()` with dedicated performance tests in `sdk/test/performance.test.ts`.

## Files touched (recent)
- `sdk/src/react/index.tsx`, `sdk/test/react.test.tsx` (new); `sdk/package.json`; `sdk/package-lock.json`; `sdk/tsconfig.build.json`; `PROGRESS.md`; `HANDOFF.md`

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

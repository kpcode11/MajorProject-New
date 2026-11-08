# Handoff

**Updated:** 2026-11-08 21:11  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-11 — SDK tests (`sdk/test/`)
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
- **P6-09 (`1417f3f`):** `src/react/index.tsx` (`BotGuardProvider` and `useBotGuard()` hook exported at `@botguard/sdk/react`).
- **P6-10:** `src/performance.ts` (`scheduleIdleTask` with `requestIdleCallback` + bounded timer fallback, `createThrottleGate`) wired into `BotGuardClient`; verified passive listener registration, 10,000-event storm memory/payload bounding (< 64 KB), and zero listener leaks after `stop()` in `sdk/test/performance.test.ts` (4 tests; 95 SDK tests total).

## Exact next step
- Implement `P6-11` (`SDK tests`), `P6-12` (`SDK bundle report` -> `results/system/sdk_size.json`), and `P6-13` (`SDK/backend contract test`).

## Files touched (recent)
- `sdk/src/performance.ts`, `sdk/test/performance.test.ts` (new); `sdk/src/index.ts`; `PROGRESS.md`; `HANDOFF.md`

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

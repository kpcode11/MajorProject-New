# Handoff

**Updated:** 2026-11-08 20:20  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-08 — SDK challenge UI (`sdk/src/challenge.ts`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`):** `sdk/` package, `config.ts`, CI `sdk` job, `scripts/tasks.py` integration.
- **P6-02 (`d1f02a4`):** `collectors/env.ts` (coarse Appendix B.2 snapshot, `deviceClass()`).
- **CI fix (`c476a63`):** track small `backend/models/**/*.onnx`; ignore `*.db`.
- **P6-03 (`8b92328`):** `ringbuffer.ts`, `collectors/mouse.ts` (`MouseCollector`).
- **P6-04 (`115c28f`):** `collectors/keyboard.ts` (`KeyboardCollector`, `keyClass`). Backend `KeyBehaviour` gained `untrusted_count`.
- **P6-05 (`714e96c`):** `collectors/scroll.ts` (`ScrollCollector`) and `collectors/timing.ts` (`TimingCollector`).
- **P6-06 (`044bd2c`):** `src/transport.ts` (`fetchNonce`, `buildAssessPayload`, `buildChallengePayload`, `postAssess`, `postChallenge`, `safeAssess`, `safeSubmitChallenge`, `BotGuardTransportError`).
- **P6-07:** `src/index.ts` (`BotGuardClient` class and `BotGuard` singleton facade with `start()`, `assess(action)`, `runChallenge(challenge, action, options?)`, `stop()`, `setChallengeHandler()`, `prefetchNonce()`). Idempotent `start()`/`stop()`, `requestIdleCallback` scheduling (`useIdleCallback`), non-throwing assessment/challenge lifecycle, and 5 integration tests in `sdk/test/api.test.ts` (83 SDK tests total).

## Exact next step
- Implement `P6-08` (`sdk/src/challenge.ts`): render a pluggable step-up challenge UI (default accessible press-and-hold modal/widget with keyboard Space/Enter support and custom renderer pluggability) and wire it as the default `challengeHandler` in `BotGuardClient`. Add `sdk/test/challenge.test.ts`.

## Files touched (recent)
- `sdk/src/index.ts`, `sdk/src/collectors/timing.ts`, `sdk/test/api.test.ts` (new); `PROGRESS.md`; `HANDOFF.md`

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

# Handoff

**Updated:** 2026-11-08 20:12  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-07 — SDK public API (`sdk/src/index.ts`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`):** `sdk/` package, `config.ts`, CI `sdk` job, `scripts/tasks.py` integration.
- **P6-02 (`d1f02a4`):** `collectors/env.ts` (coarse Appendix B.2 snapshot, `deviceClass()`).
- **CI fix (`c476a63`):** track small `backend/models/**/*.onnx`; ignore `*.db`.
- **P6-03 (`8b92328`):** `ringbuffer.ts`, `collectors/mouse.ts` (`MouseCollector`).
- **P6-04 (`115c28f`):** `collectors/keyboard.ts` (`KeyboardCollector`, `keyClass`). Backend `KeyBehaviour` gained `untrusted_count`.
- **P6-05 (`714e96c`):** `collectors/scroll.ts` (`ScrollCollector`) and `collectors/timing.ts` (`TimingCollector`).
- **P6-06:** `src/transport.ts` (`fetchNonce`, `buildAssessPayload`, `buildChallengePayload`, `postAssess`, `postChallenge`, `safeAssess`, `safeSubmitChallenge`, `BotGuardTransportError`). Enforces the 64 KB body cap (`trimToBodyLimit`), per-attempt `AbortController` timeouts (`requestTimeoutMs`), exponential backoff retries on network/timeout/429/5xx (`maxRetries`, `retryBaseDelayMs`), and non-throwing degraded fallback responses so host pages never block. Added `sdk/test/transport.test.ts` (10 tests; 78 SDK tests total).

## Exact next step
- Implement `P6-07` (`SDK public API`) and `P6-08` (`SDK challenge UI` hookup): expose `BotGuard.start(options?)`, `BotGuard.assess(action)`, `BotGuard.runChallenge(challengeInfo, action, options?)`, `BotGuard.stop()` (plus an instantiable `BotGuardClient` class) in `sdk/src/index.ts`. Ensure `start()` and `stop()` are idempotent and safe to call multiple times, and wire up collectors + transport.

## Files touched (recent)
- `sdk/src/transport.ts`, `sdk/test/transport.test.ts` (new); `sdk/src/index.ts`; `PROGRESS.md`; `HANDOFF.md`

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

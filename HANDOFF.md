# Handoff

**Updated:** 2026-11-08 20:06  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-06 — SDK transport (`sdk/src/transport.ts`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`):** `sdk/` package, `config.ts`, CI `sdk` job, `scripts/tasks.py` integration.
- **P6-02 (`d1f02a4`):** `collectors/env.ts` (coarse Appendix B.2 snapshot, `deviceClass()`).
- **CI fix (`c476a63`):** track small `backend/models/**/*.onnx`; ignore `*.db`.
- **P6-03 (`8b92328`):** `ringbuffer.ts`, `collectors/mouse.ts` (`MouseCollector`).
- **P6-04 (`115c28f`):** `collectors/keyboard.ts` (`KeyboardCollector`, `keyClass`). Backend `KeyBehaviour` gained `untrusted_count`.
- **P6-05:** `collectors/scroll.ts` (`ScrollCollector`: passive capture scroll listener, ignores untrusted events, capped at 100,000) and `collectors/timing.ts` (`TimingCollector`: tracks `ms_since_load`, `ms_to_first_interaction` on first trusted interaction, `ms_since_nonce` via `markNonce()`, `scroll_events`, and `focus_changes` across capture `focus`/`blur` and document `visibilitychange`). Added `sdk/test/timing.test.ts` (5 tests; 68 SDK tests total).

## Exact next step
- Implement `sdk/src/transport.ts` for `P6-06`: fetch nonce (`GET /v1/nonce`), build assess/challenge payloads (`AssessRequest`, `ChallengeAssessRequest`), POST to `/v1/assess` and `/v1/assess/challenge`, handle errors, retries with exponential backoff (`maxRetries`, `retryBaseDelayMs`), timeouts (`AbortController` / `requestTimeoutMs`), and ensure transport errors never block the host page. Add `sdk/test/transport.test.ts`.

## Files touched (recent)
- `sdk/src/collectors/scroll.ts`, `sdk/src/collectors/timing.ts`, `sdk/test/timing.test.ts` (new); `sdk/src/index.ts`; `PROGRESS.md`; `HANDOFF.md`

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

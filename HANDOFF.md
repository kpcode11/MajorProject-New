# Handoff

**Updated:** 2026-11-08 21:01  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-09 — React SDK integration (`sdk/src/react/index.tsx`)
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
- **P6-08:** `src/challenge.ts` (`renderPressHoldChallenge`, `createChallengeHandler`, `defaultPressHoldRenderer`, `BotGuardChallengeCancelledError`) wired as the default handler in `BotGuardClient.runChallenge()`. Supports accessible press-and-hold (mouse, touch, keyboard `Space`/`Enter`), a single-press keyboard accessibility alternative button, `Cancel` / `Escape` handling, and custom `ChallengeRenderer` pluggability. Added `sdk/test/challenge.test.ts` (5 tests; 88 SDK tests total).

## Exact next step
- Implement `P6-09` (`sdk/src/react/index.tsx`): `BotGuardProvider` and `useBotGuard()` hook with React as an optional peer dependency (`peerDependencies` in `package.json`, `react` + `@types/react` + `@testing-library/react` or `react-dom` in devDependencies for testing, and externalised in Vite or separate entry so core bundle keeps zero runtime dependencies). Add `sdk/test/react.test.tsx`.

## Files touched (recent)
- `sdk/src/challenge.ts`, `sdk/test/challenge.test.ts` (new); `sdk/src/index.ts`; `sdk/test/api.test.ts`; `PROGRESS.md`; `HANDOFF.md`

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

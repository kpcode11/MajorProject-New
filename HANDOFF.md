# Handoff

**Updated:** 2026-11-08 19:23  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-04 — Keyboard collector (`sdk/src/collectors/keyboard.ts`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`):** `sdk/` package (Vite 8 ES + UMD, TS 6 strict, vitest 5 + happy-dom, ESLint 10, Prettier), `config.ts`, CI `sdk` job, `scripts/tasks.py` integration.
- **P6-02 (`d1f02a4`):** `collectors/env.ts` — coarse Appendix B.2 snapshot, `deviceClass()`; no raw UA/renderer strings, no hash.
- **CI fix (`c476a63`):** `.gitignore` now tracks small `backend/models/**/*.onnx` (CI needs them) and ignores `*.db`.
- **P6-03:** `src/ringbuffer.ts` (bounded `RingBuffer<T>`), `collectors/mouse.ts` (`MouseCollector`: passive capture listeners; `mousemove` throttled by `mouseThrottleMs`; down/up add boundary points and pair into `[x, y, down_ms, up_ms]` clicks; `click` without a press within 100 ms -> zero-dwell click; `wheel` counted; `isTrusted === false` events counted in `untrusted_count` and never stored; `snapshot()` returns the last `windowMs`; `stop()` removes listeners and clears memory). Tests in `test/mouse.test.ts` (8).

## Exact next step
- Implement `collectors/keyboard.ts` (P6-04): `keydown`/`keyup` timing with key class only (`letter|digit|space|punct|modifier|enter|backspace|other`, mapped in code from `event.key`/`event.code` in memory; never stored). Pair down/up per physical key, bounded `RingBuffer` (`maxKeyEvents`), count `paste` events and suspected autofill (input events without key presses); never read input values. Output `KeyBehaviour` (`events`, `paste_events`, `autofill_suspected`) per `backend/app/schemas.py`. Test that a typed known string never appears in the serialised payload. Reuse the trusted-event test helper pattern from `test/mouse.test.ts` (happy-dom marks dispatched events untrusted; tests override `isTrusted`).

## Files touched (recent)
- `sdk/src/ringbuffer.ts`, `sdk/src/collectors/mouse.ts`, `sdk/test/mouse.test.ts` (new); `sdk/src/index.ts`; `PROGRESS.md`; `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py test-fast
    cd sdk; npm run lint; npm run typecheck; npm test; npm run build

## Known problems / gotchas
- Run `npm` only from `sdk/`. Git writes need elevated permission in the agent sandbox.
- Backend `KeyBehaviour` has no `untrusted_count` field (extra keys are ignored by Pydantic); R11 reads `behaviour.keys.untrusted_count` if present.

## Dataset / long-job state
- None.

## Questions for the human
- None.

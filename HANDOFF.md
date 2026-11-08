# Handoff

**Updated:** 2026-11-08 19:28  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P6-05 — Scroll and timing collectors (`sdk/src/collectors/scroll.ts`, `sdk/src/collectors/timing.ts`)
- State: not started (`TODO`)

## Done in Phase 6 so far
- **P6-01 (`9f0c704`):** `sdk/` package, `config.ts`, CI `sdk` job, `scripts/tasks.py` integration.
- **P6-02 (`d1f02a4`):** `collectors/env.ts` (coarse Appendix B.2 snapshot, `deviceClass()`).
- **CI fix (`c476a63`):** track small `backend/models/**/*.onnx`; ignore `*.db`.
- **P6-03 (`8b92328`):** `ringbuffer.ts`, `collectors/mouse.ts` (`MouseCollector`).
- **P6-04:** `collectors/keyboard.ts` (`KeyboardCollector`, `keyClass`). Key identity is read only inside `keyClass()` and never stored; down/up pairing is FIFO per class; auto-repeat ignored; untrusted events counted only; `paste` counted; `autofill_suspected` set by `input` events on text fields with no recent key-down/paste (element kind checked, value never read); pending presses cleared on window blur / after 5 s. Backend `KeyBehaviour` gained `untrusted_count` (0..300) because `scoring.py` uses `model_dump()`, which dropped unknown keys before rule R11 read them; backend test added in `tests/test_schemas.py`.

## Exact next step
- P6-05: `collectors/scroll.ts` (count scroll events, passive) and `collectors/timing.ts` (focus/blur and `visibilitychange` transition count, ms from page load to first trusted interaction, `ms_since_load`, `ms_since_nonce` given a nonce timestamp). Output must match backend `TimingSignals` (`ms_since_load`, `ms_to_first_interaction`, `ms_since_nonce`, `scroll_events`, `focus_changes`; all ≤ 3,600,000 ms / count caps in `schemas.py`).

## Files touched (recent)
- `sdk/src/collectors/keyboard.ts`, `sdk/test/keyboard.test.ts` (new); `sdk/src/index.ts`; `backend/app/schemas.py`; `backend/tests/test_schemas.py`; `PROGRESS.md`; `HANDOFF.md`

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

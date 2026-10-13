# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** pending

## Current task

- ID: P3-03 — keyboard privacy scan
- State: ready to start.

## Done in the previous task

- Added `ml/src/botguard_ml/loaders/aalto_keystrokes.py`.
- Streams one participant TSV at a time and supports deterministic seeded
  participant sampling.
- Converts each sentence with at least 10 key events into a canonical
  keyboard window.
- Maps source key identities to coarse `key_class` values in memory and
  excludes sentence text, typed text, key identity, and keystroke identity
  from output.
- Writes per-participant Parquet shards and resumable `_state.json` progress.
- Counts malformed participants instead of aborting the complete batch.
- Added `scripts/build_keyboard_events.py` and wired
  `python scripts/tasks.py train-keyboard`.
- Added fixture coverage and a real one-participant smoke test.

## Exact next step

- Add a privacy scan that reads every produced keyboard shard and fails if it
  contains typed text, sentences, key identities, or other prohibited columns.

## Files touched in P3-02

- `ml/src/botguard_ml/loaders/aalto_keystrokes.py`
- `ml/tests/test_aalto_keystrokes.py`
- `scripts/build_keyboard_events.py`
- `scripts/tasks.py`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`
- Real Aalto one-participant smoke test: 13 windows, 661 events

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- The local Aalto copy is approximately 18.85 GB; do not process all
  participants without an explicit bounded run.
- The dataset root supports both the configured top-level path and its nested
  `Keystrokes` directory layout.
- The loader output is intentionally human-only (`label=0`); synthetic bot
  windows are a later task.
- Work is on `phase-2-mouse-model`.

## Questions for the human (P3-03)

- None.

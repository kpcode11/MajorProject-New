# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-3-keyboard  |  **Last commit:** pending

## Current task

- ID: P3-04 — keyboard features
- State: ready to start.

## Done in the previous task

- Added `ml/src/botguard_ml/privacy.py` to scan every keyboard Parquet shard
  in batches.
- Rejects prohibited columns including sentence text, user input, letters,
  key codes, keystroke IDs, typed text, and generic text columns.
- Added `scripts/scan_keyboard_privacy.py`.
- Added `python scripts/tasks.py keyboard-privacy`.
- Added safe and unsafe fixture tests.
- Validated one real generated Aalto shard: 1 shard and 661 rows scanned.

## Exact next step

- Implement text-agnostic keyboard features from Appendix A.3, including
  dwell, flight/inter-key intervals, variability, burstiness, pause, and
  correction-free timing features.

## Files touched in P3-03

- `ml/src/botguard_ml/privacy.py`
- `ml/tests/test_privacy.py`
- `scripts/scan_keyboard_privacy.py`
- `scripts/tasks.py`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`
- Real Aalto loader plus privacy-scan smoke test

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Do not use source sentence, user input, letter, key code, or keystroke ID
  fields as keyboard model features.
- Keyboard shards are human-only until the synthetic generators task.
- Work is now on the dedicated `phase-3-keyboard` branch.

## Questions for the human (P3-04)

- None.

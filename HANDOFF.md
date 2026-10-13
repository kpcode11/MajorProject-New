# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-3-keyboard  |  **Last commit:** pending

## Current task

- ID: P3-07 — keyboard evaluation
- State: ready to start.

## Done in the previous task

- Added `ml/src/botguard_ml/features/keyboard_shards.py`.
- Builds text-agnostic feature rows from human Aalto event shards.
- Generates configurable-prevalence K1, K2, and K4 training bot windows.
- Groups human rows by participant and synthetic rows by generator/seed block.
- Rejects K3 in training shard construction so it remains held out.
- Writes `keyboard_features.schema.json`.
- Added `scripts/build_keyboard_features.py`.
- Added `python scripts/tasks.py train-keyboard --stage features`.
- Added fixture coverage and real smoke validation.

## Exact next step

- Train and evaluate keyboard baselines using the Phase 2 protocol, including
  per-generator recall for K1-K4 (with K3 held out), typist-speed terciles,
  human FPR, calibration, and grouped bootstrap confidence intervals.

## Files touched in P3-06

- `ml/src/botguard_ml/features/keyboard_shards.py`
- `ml/tests/test_keyboard_shards.py`
- `scripts/build_keyboard_features.py`
- `scripts/tasks.py`
- `docs/plan/phase_3.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`
- Real Aalto smoke: 2 participants, 30 human windows, 1,272 events, 15 bot windows

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- K3 is intentionally absent from training feature shards; generate it only
  in a held-out evaluation path.
- The current feature build uses all event shards under the input root and
  writes one feature table; future large runs may shard output further.
- Human data are typing-test windows, not ordinary browsing.
- Work is on the dedicated `phase-3-keyboard` branch.

## Questions for the human (P3-07)

- None.

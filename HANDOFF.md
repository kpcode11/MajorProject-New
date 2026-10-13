# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-3-keyboard  |  **Last commit:** e7006fa

## Current task

- ID: P3-06 — keyboard feature shards
- State: ready to start.

## Done in the previous task

- Added `ml/src/botguard_ml/synthetic/keyboard.py`.
- Implemented deterministic K1 constant, K2 uniform, K3 mimic, and K4 burst
  generators.
- Added `fit_human_timing`, which fits K3 log-normal timing parameters from
  supplied training-human windows only.
- Added optional slow K1 variants to avoid learning only that bots are fast.
- Added generator metadata, labels, and bot-specific split groups.
- Added tests for determinism, K3 profile requirements, and K4 pause output.

## Exact next step

- Build keyboard feature shards from human Aalto windows plus configurable
  synthetic bot prevalence, grouping humans by participant and bots by
  generator/seed block while holding K3 out of training.

## Files touched in P3-05

- `ml/src/botguard_ml/synthetic/keyboard.py`
- `ml/tests/test_synthetic_keyboard.py`
- `docs/plan/phase_3.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- K3 must never be fitted using validation or test participants.
- Generated keyboard sessions contain only timing and coarse key classes.
- Work is on the dedicated `phase-3-keyboard` branch.

## Questions for the human (P3-06)

- None.

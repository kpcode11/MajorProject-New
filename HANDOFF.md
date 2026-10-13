# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-3-keyboard  |  **Last commit:** pending

## Current task

- ID: P3-08 — optional second human keyboard source
- State: ready to start.

## Done in the previous task

- Added `ml/src/botguard_ml/keyboard_eval.py`.
- Added grouped Logistic Regression evaluation using the Phase 2 split
  convention.
- Excludes K3 from training and forces any K3 rows into evaluation.
- Reports overall metrics, per-generator reports, speed terciles, human FPR,
  and grouped bootstrap ROC-AUC intervals.
- Added `scripts/evaluate_keyboard.py`.
- Added `python scripts/tasks.py train-keyboard --stage evaluate`.
- Added fixture tests for generator reporting and K3 holdout handling.

## Exact next step

- Check whether SU-AIS BB-MAS or the configured UL keystroke repository is
  available and usable. If not, document the single-human-source limitation
  and continue without inventing a second source.

## Files touched in P3-07

- `ml/src/botguard_ml/keyboard_eval.py`
- `ml/tests/test_keyboard_eval.py`
- `scripts/evaluate_keyboard.py`
- `scripts/tasks.py`
- `docs/plan/phase_3.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Real final keyboard metrics require a bounded feature-shard run and
  sufficient human and bot groups.
- K3 must remain evaluation-only.
- Work is on the dedicated `phase-3-keyboard` branch.

## Questions for the human (P3-08)

- None.

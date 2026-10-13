# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-3-keyboard  |  **Last commit:** pending

## Current task

- ID: P3-10 — desktop fusion
- State: ready to start.

## Done in P3-09

- Added `export_keyboard_onnx()` with median imputation, standard scaling, and
  Logistic Regression.
- Excluded K3 training rows and recorded that policy in `metadata.json`.
- Added `scripts/export_keyboard_onnx.py` and the
  `train-keyboard --stage onnx` task.
- Added native-vs-ONNX parity and metadata tests.
- Declared `skl2onnx` directly in the ML package dependencies.

## Exact next step

- Inspect the mouse and keyboard evaluation outputs, then implement pseudo-
  session score-level fusion with explicit missing-modality behavior.

## Files touched in P3-09

- `ml/src/botguard_ml/export_onnx.py`
- `ml/tests/test_keyboard_onnx.py`
- `scripts/export_keyboard_onnx.py`
- `ml/pyproject.toml`
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

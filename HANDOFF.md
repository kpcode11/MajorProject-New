# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** e8e7ef2

## Current task

- ID: P2-12 — mouse ONNX export
- State: ready to start.

## Done in the previous task

- Added LightGBM SHAP explanations in `ml/src/botguard_ml/explanations.py`.
- Added `shap_summary` with mean signed and absolute contributions.
- Added `top_contributing_features`, returning the top three contributors for
  every scored window by absolute SHAP magnitude.
- Added `scripts/run_mouse_shap.py`, writing
  `results/mouse/shap_summary.csv` and
  `results/mouse/shap_top_features.json`.
- Added `train-mouse --stage shap`.
- Added focused tests for ranking and summary output.

## Exact next step

- Export the mouse model to `backend/models/mouse-<version>/model.onnx` with
  metadata, then add native-vs-ONNX parity coverage.

## Files touched in P2-11

- `ml/src/botguard_ml/explanations.py`
- `ml/tests/test_explanations.py`
- `scripts/run_mouse_shap.py`
- `scripts/tasks.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`
- LightGBM plus SHAP integration smoke test

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- SHAP execution requires generated feature shards under
  `data/processed/mouse_features/`.
- SHAP currently explains the fixed LightGBM baseline configuration, not
  unavailable optimized parameters.
- Work is on `phase-2-mouse-model`.

## Dataset / long-job state

- No generated SHAP reports remain in the worktree.

## Questions for the human (P2-12)

- None.

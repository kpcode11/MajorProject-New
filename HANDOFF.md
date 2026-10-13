# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** b132069

## Current task

- ID: P2-11 — mouse SHAP explanations
- State: ready to start.

## Done in the previous task

- Added feature-group ablations in `ml/src/botguard_ml/ablations.py` for
  kinematics, geometry, timing, and click features.
- Added shortcut-inclusive and shortcut-exclusive configurations.
- Every configuration uses the same deterministic grouped split and Logistic
  Regression evaluator.
- Added `scripts/run_mouse_ablations.py`, writing
  `results/mouse/ablations.csv`.
- Added focused ablation coverage and group-count tests.

## Exact next step

- Add a SHAP summary workflow and a helper returning the top three contributing
  features for each scored window.

## Files touched in P2-10

- `ml/src/botguard_ml/ablations.py`
- `ml/tests/test_ablations.py`
- `scripts/run_mouse_ablations.py`
- `scripts/tasks.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Ablation execution requires generated feature shards under
  `data/processed/mouse_features/`.
- Git marks this workspace safe in the local user's global Git configuration
  due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1
  (`phase-1-dataset-audit`).

## Dataset / long-job state

- No generated ablation tables remain in the worktree.

## Questions for the human (P2-11)

- None.

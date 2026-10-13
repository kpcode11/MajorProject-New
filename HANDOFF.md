# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** f99752a

## Current task

- ID: P2-06 — LightGBM optimisation
- State: ready to start.

## Done in the previous task

- Added reproducible mouse baselines in `ml/src/botguard_ml/baselines.py`:
  majority class, scaled Logistic Regression, Random Forest, and LightGBM.
- All models use the same deterministic grouped train/test split.
- Metrics include accuracy, balanced accuracy, ROC-AUC, sample counts, and
  train/test group counts.
- Added `scripts/run_mouse_baselines.py` and
  `python scripts/tasks.py train-mouse --stage baselines`.
- Results are written to `results/mouse/baselines.csv`.

## Exact next step

- Implement a time-boxed Optuna LightGBM search with grouped cross-validation
  on training groups only and save `results/mouse/hparams.json`.

## Files touched in P2-05

- `ml/src/botguard_ml/baselines.py`
- `ml/tests/test_baselines.py`
- `scripts/run_mouse_baselines.py`
- `scripts/tasks.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Baseline execution requires generated feature shards under
  `data/processed/mouse_features/`.
- Git marks this workspace safe in the local user's global Git configuration
  due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1
  (`phase-1-dataset-audit`).

## Dataset / long-job state

- No generated feature shards remain in the worktree.

## Questions for the human (P2-06)

- None.

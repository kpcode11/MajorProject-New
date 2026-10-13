# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** pending

## Current task

- ID: P2-05 — mouse baselines
- State: ready to start.

## Done in the previous task

- Implemented leakage-safe split utilities in
  `ml/src/botguard_ml/splits.py`.
- `grouped_split` creates deterministic group-level train/test partitions.
- `cross_phase_split` holds out a requested domain/phase.
- `cross_dataset_split` holds out a requested dataset.
- `leave_one_bot_type_out` holds out only the requested bot type.
- All strategies validate required feature metadata and reject empty or
  overlapping group partitions.
- Added tests asserting complete coverage and disjoint `split_group` values.

## Exact next step

- Implement identical-split mouse baselines: majority class, scaled Logistic
  Regression, Random Forest, and LightGBM.
- Save results under `results/mouse/baselines.csv`.

## Files touched in P2-04

- `ml/src/botguard_ml/splits.py`
- `ml/tests/test_splits.py`
- `ml/tests/test_mouse_features.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Git marks this workspace safe in the local user's global Git configuration
  due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1
  (`phase-1-dataset-audit`).

## Dataset / long-job state

- No generated feature shards remain in the worktree.

## Questions for the human (P2-05)

- None.

# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** pending

## Current task

- ID: P2-10 — mouse ablations
- State: ready to start.

## Done in the previous task

- Added score evaluation utilities in `ml/src/botguard_ml/eval/__init__.py`.
- Supports in-distribution, cross-phase, cross-dataset, and
  leave-one-bot-type-out splits.
- Reports ROC-AUC, PR-AUC, Brier score, 1% human-FPR bot recall,
  confusion counts, row/group counts, and group-bootstrap 95% CIs.
- Added CaptchaSolve30k human-FPR-by-game-type reporting.
- Added `scripts/evaluate_mouse.py` for CSV evaluation output.
- Insufficient-data splits are reported honestly rather than producing
  invented metrics.

## Exact next step

- Implement feature-group and shortcut-feature ablations for kinematics,
  geometry, timing, click features, and with/without shortcut columns.
- Save comparable results under `results/mouse/`.

## Files touched in P2-09

- `ml/src/botguard_ml/eval/__init__.py`
- `ml/tests/test_eval.py`
- `scripts/evaluate_mouse.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Evaluation consumes precomputed score tables; it does not invent scores when
  model outputs or datasets are unavailable.
- Git marks this workspace safe in the local user's global Git configuration
  due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1
  (`phase-1-dataset-audit`).

## Dataset / long-job state

- No generated evaluation tables remain in the worktree.

## Questions for the human (P2-10)

- None.

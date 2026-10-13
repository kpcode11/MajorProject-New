# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** pending

## Current task

- ID: P2-09 — mouse evaluation
- State: ready to start.

## Done in the previous task

- Added grouped three-way calibration in `ml/src/botguard_ml/calibrate.py`.
- Calibration groups are never used for fitting the raw model or evaluation.
- Supports isotonic regression and Platt logistic scaling.
- Reports raw and calibrated Brier scores plus reliability-bin records.
- Added `scripts/calibrate_mouse_scores.py` for reproducible JSON output.
- Added tests for both calibration methods and partition accounting.

## Exact next step

- Implement Appendix E evaluation: in-distribution, cross-phase,
  cross-dataset, leave-one-bot-type-out, human-FPR stress test, and grouped
  bootstrap confidence intervals under `results/mouse/`.

## Files touched in P2-08

- `ml/src/botguard_ml/calibrate.py`
- `ml/tests/test_calibrate.py`
- `scripts/calibrate_mouse_scores.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Calibration requires a score table with `score`, `label`, and `split_group`
  columns.
- Git marks this workspace safe in the local user's global Git configuration
  due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1
  (`phase-1-dataset-audit`).

## Dataset / long-job state

- No generated score tables remain in the worktree.

## Questions for the human (P2-09)

- None.

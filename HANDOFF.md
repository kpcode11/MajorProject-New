# Handoff

**Updated:** 2026-10-13  |  **By:** Cursor  |  **Branch:** phase-2-mouse-model  |  **Last commit:** ad62ff1

## Current task

- ID: P2-02 — mouse feature extraction
- State: ready to start.

## Done in this task so far

- P2-01 added `segment_trajectory` in `ml/src/botguard_ml/features/mouse.py` with pause and `down`/`up`/`click` splitting, `min_points`/`min_path_px` filters, and focused tests.
- Segmentation defaults are recorded in `ml/configs/mouse_features.yaml`.
- `python scripts/tasks.py test-fast` and `python scripts/tasks.py lint` passed.

## Exact next step

- Implement Appendix A.2 mouse features per segment and window-level aggregation (mean, std, max over segments plus window timing stats) in `features/mouse.py`, with docstrings, hand-computed unit tests, and hypothesis property tests.

## Files touched (uncommitted or recently changed)

- `ml/src/botguard_ml/features/mouse.py` — `segment_trajectory`.
- `ml/tests/test_mouse_segmentation.py` — pause, boundary, and minimum-size coverage.
- `ml/configs/mouse_features.yaml` — window and segment parameters.

## Commands to run first

    python scripts/status.py
    python scripts/tasks.py test-fast

## Known problems / gotchas

- Git marks this workspace safe in the local user's global Git configuration due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1 (`phase-1-dataset-audit`).

## Dataset / long-job state

- No dataset operation has started.

## Questions for the human (P2-02)

- None.

# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** e5213db

## Current task

- ID: P2-03 — mouse feature shards
- State: ready to start.

## Done in the previous task

- P2-02 implements the Appendix A.2 mouse feature set in
  `ml/src/botguard_ml/features/mouse.py`.
- Segment features cover kinematics, geometry, timing, and click-related
  measurements, with explicit formula/unit documentation.
- Window features aggregate segment values by mean, sample standard deviation,
  and maximum, and include configurable shortcut features plus window timing.
- Added hand-computed examples and Hypothesis tests for finite outputs,
  bounded straightness, and translation invariance.
- P2-01 segmentation defaults remain in
  `ml/configs/mouse_features.yaml`.

## Exact next step

- Implement `python scripts/tasks.py train-mouse --stage features
  --max-sessions N` to stream canonical mouse windows, extract features, and
  write resumable shards under `data/processed/mouse_features/` plus
  `mouse_features.schema.json`.
- Include `dataset`, `domain`, `session_id`, `subject_id`, `split_group`,
  `label`, and `bot_type` in every feature row.

## Files touched in P2-02

- `ml/src/botguard_ml/features/mouse.py`
- `ml/tests/test_mouse_features.py`
- `ml/configs/mouse_features.yaml`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`
- Focused mouse feature and segmentation tests

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Git marks this workspace safe in the local user's global Git configuration
  due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1
  (`phase-1-dataset-audit`).
- Avoid asserting translation invariance for subnormal-scale paths: adding a
  translation can round away a displacement smaller than float precision.

## Dataset / long-job state

- No dataset operation has started for P2-03.

## Questions for the human (P2-03)

- None.

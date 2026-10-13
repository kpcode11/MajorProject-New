# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** 53c535b

## Current task

- ID: P2-04 — leakage-safe split utilities
- State: ready to start.

## Done in the previous task

- Added `botguard_ml.features.shards` to stream canonical Parquet events,
  extract window features, and write one resumable feature shard per source.
- Added stable metadata columns: `dataset`, `domain`, `session_id`,
  `subject_id`, `split_group`, `label`, and `bot_type`.
- Added `mouse_features.schema.json` and `_state.json` tracking under
  `data/processed/mouse_features/`.
- Added `python scripts/tasks.py train-mouse --stage features
  --max-sessions N`.
- Added focused shard and resumability tests.

## Exact next step

- Implement `grouped_split`, `cross_phase_split`, `cross_dataset_split`, and
  `leave_one_bot_type_out` in `ml/src/botguard_ml/splits.py`.
- Add tests proving no `split_group` occurs in more than one split.

## Files touched in P2-03

- `ml/src/botguard_ml/features/shards.py`
- `ml/tests/test_mouse_shards.py`
- `scripts/build_mouse_features.py`
- `scripts/tasks.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`
- `python scripts/tasks.py train-mouse --stage features --max-sessions 1`

All passed. The smoke shard was removed after validation. Windows pytest cache
warnings are pre-existing and harmless.

## Known problems / gotchas

- Git marks this workspace safe in the local user's global Git configuration
  due to a sandbox ownership mismatch.
- Work is on `phase-2-mouse-model`, created from completed Phase 1
  (`phase-1-dataset-audit`).

## Dataset / long-job state

- No generated feature shards remain in the worktree.

## Questions for the human (P2-04)

- None.

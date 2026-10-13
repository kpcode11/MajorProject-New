# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-3-keyboard  |  **Last commit:** fdad7d8

## Current task

- ID: P3-09 — keyboard ONNX export
- State: ready to start.

## Done in P3-08

- Checked the configured dataset root and found no BB-MAS data.
- Confirmed `ul_keystroke_repo` remains a placeholder with `repo_only` status.
- Recorded the single-human-source limitation in the Aalto dataset card and
  Phase 3 plan. No unsupported second-source loader was added.

## Exact next step

- Inspect the existing mouse ONNX export and keyboard model pipeline, then add
  a keyboard ONNX export with metadata and parity coverage.

## Files touched in P3-08

- `docs/datasets/aalto_keystrokes.md`
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

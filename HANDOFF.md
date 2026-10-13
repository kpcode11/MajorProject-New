# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** pending

## Current task

- ID: P3-02 — Aalto keyboard loader
- State: ready to start.

## Done in the previous task

- Inventoried the configured Aalto dataset without loading it into memory.
- Corrected `scripts/inventory.py` so aggregate file counts and sizes cover
  all directory entries while printed tree output remains capped.
- Confirmed 168,593 participant files, one metadata file, one README, and
  approximately 18.85 GB on disk.
- Read the supplied README and recorded its citation, non-commercial
  attribution terms, tab-separated format, timestamp units, and known logging
  caveat.
- Added `docs/datasets/aalto_keystrokes.md` with the dataset card and the
  participant-streaming/privacy processing decision.

## Exact next step

- Implement `ml/src/botguard_ml/loaders/aalto_keystrokes.py` to stream seeded
  participant files, create sentence windows with at least 10 events, map
  key identity to `key_class` in memory, and write progress-aware Parquet
  shards without retaining text or key identities.

## Files touched in P3-01

- `scripts/inventory.py`
- `docs/datasets/inventory_aalto_keystrokes.txt`
- `docs/datasets/aalto_keystrokes.md`
- `PROGRESS.md`

## Validation

- `python scripts/inventory.py aalto_keystrokes`
- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- The local Aalto copy is extracted and approximately 18.85 GB; never
  concatenate participant files or load the metadata table wholesale.
- Raw `SENTENCE`, `USER_INPUT`, `LETTER`, `KEYCODE`, and `KEYSTROKE_ID` must
  not enter canonical keyboard shards.
- The configured branch remains `phase-2-mouse-model`; do not switch branches
  without explicit instruction.

## Questions for the human (P3-02)

- None.

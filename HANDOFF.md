# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** pending

## Current task

- ID: P3-01 — Aalto inventory and card
- State: ready to start.

## Done in the previous task

- Added `docs/model_card.md` with the mouse model summary, input and feature
  construction, grouped evaluation protocol, intended use, limitations,
  privacy boundaries, and deployment status.
- Explicitly documented that complete source shards and final real-data metrics
  are unavailable, so no unsupported metric is claimed.
- Marked P2-13 complete in the phase plan and progress ledger.

## Exact next step

- Inventory the Aalto keystroke dataset safely, record its availability and
  licence/format facts, and write its dataset card without loading large files
  into memory.

## Files touched in P2-13

- `docs/model_card.md`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- Documentation-only change; no test run required.

## Known problems / gotchas

- The model card deliberately reports no final model metric because complete
  feature shards are unavailable.
- Work is on `phase-2-mouse-model`.

## Questions for the human (P3-01)

- None.

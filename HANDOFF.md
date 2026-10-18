# Handoff

**Updated:** 2026-10-18  |  **By:** User  |  **Branch:** phase-4-env-rules  |  **Last commit:** 6960b1a

## Current task

- ID: P5-01 - Settings and score store
- State: ready to start.

## Done in P4-07

- Recorded the decision to defer the optional BotD comparison.
- Did not add a BotD runtime dependency or download an unpinned artifact.
- Documented the local R01-R13 rule suite as the current baseline.
- Added the future requirements for any BotD comparison: pinned version,
  licence review, fixture adapter, and a new decision entry.
- Marked Phase 4 acceptance criteria complete in `docs/plan/phase_4.md`.

## Exact next step

- Begin Phase 5 by implementing backend settings and a privacy-safe score
  store, preserving the documented model/rule boundaries.

## Files touched in P4-07

- `docs/decision_log.md`
- `docs/signals.md`
- `docs/plan/phase_4.md`
- `PROGRESS.md`

## Validation

Documentation and decision-log task; no code validation required. The complete
rule implementation was previously validated with:

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

## Known problems / gotchas

- Phase 4 environment rules remain on `phase-4-env-rules`.
- Do not use persistent identifiers or fingerprint hashes.
- Hard rules must bypass model scoring.

## Questions for the human

- None.

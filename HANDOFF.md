# Handoff

**Updated:** 2026-10-18  |  **By:** User  |  **Branch:** phase-4-env-rules  |  **Last commit:** pending

## Current task

- ID: P4-07 - Optional BotD comparison
- State: ready to start.

## Done in P4-06

- Added `docs/signals.md` documenting all 26 `EnvSignals` fields.
- Classified signals as low-sensitivity context, derived integrity, or
  server-side control.
- Documented aggregation, retention boundaries, and missing-signal handling.
- Explicitly prohibited persistent identifiers, fingerprint hashes, raw
  headers, exact hardware identifiers, location, content, typed characters,
  key identities, clipboard data, and raw renderer/plugin details.
- Documented normal-browser and headless fixture coverage.

## Exact next step

- Decide whether the optional offline BotD comparison is appropriate. Do not
  add a runtime dependency; record a decision before any external comparison.

## Files touched in P4-06

- `docs/signals.md`
- `docs/plan/phase_4.md`
- `PROGRESS.md`

## Validation

Documentation-only task; no code validation required. Previous P4-05
validation remains passing:

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

## Known problems / gotchas

- Phase 4 work continues on `phase-4-env-rules`.
- Do not use persistent identifiers or fingerprint hashes in environment rules.
- Hard rules must bypass model scoring.

## Questions for the human

- None.

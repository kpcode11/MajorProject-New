# Handoff

**Updated:** 2026-10-18  |  **By:** User  |  **Branch:** phase-4-env-rules  |  **Last commit:** pending

## Current task

- ID: P4-06 - Signal privacy documentation
- State: ready to start.

## Done in P4-05

- Added a normal Chrome on Windows aggregate fixture test requiring a zero
  rule score and no fired rules.
- Added a headless-browser aggregate fixture test requiring a score above
  0.8 and the expected webdriver, software-renderer, zero-plugin,
  viewport-anomaly, and native-integrity rules.
- Preserved the existing individual passing and failing tests for R01-R13.
- Full project tests and lint pass.

## Exact next step

- Document every environment signal and its privacy class in
  `docs/signals.md`, including what is collected, what is bucketed, and what
  is explicitly prohibited.

## Files touched in P4-05

- `backend/tests/test_rules.py`
- `docs/plan/phase_4.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

Both passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Phase 4 work continues on `phase-4-env-rules`.
- Do not use persistent identifiers or fingerprint hashes in environment rules.
- Hard rules must bypass model scoring.

## Questions for the human

- None.

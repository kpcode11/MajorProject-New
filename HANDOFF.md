# Handoff

**Updated:** 2026-10-18  |  **By:** Copilot  |  **Branch:** phase-4-env-rules  |  **Last commit:** pending

## Current task

- ID: P4-04 - Configurable rule weights
- State: ready to start.

## Done in P4-03

- Added `RuleScore` in `backend/app/rules.py`.
- Combined fired rule weights using:
  `rule_score = 1 - prod(1 - weight_i)`.
- Preserved fired rule IDs and human-readable reasons.
- Marked R13 rate-limit violations as hard model bypasses.
- Added invalid nonce/signature as an explicit hard model bypass.
- Added `evaluate_rule_score()` to evaluate and combine the complete ruleset.
- Added tests for zero score, noisy-OR arithmetic, hard rules, invalid
  weights, and integrated evaluation.
- Updated the Phase 4 checklist for P4-01 through P4-03.

## Exact next step

- Implement `backend/config/rules.yaml` loading and configurable enabled
  flags/weights without changing the pure rule behavior.

## Files touched in P4-03

- `backend/app/rules.py`
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

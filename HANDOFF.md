# Handoff

**Updated:** 2026-10-15  |  **By:** Antigravity  |  **Branch:** phase-4-env-rules  |  **Last commit:** 7f1ac74

## Current task

- ID: P4-02 - Pure environment rules
- State: DONE (commit 7f1ac74).

## Done in P4-02

- Implemented `RuleResult` frozen dataclass in `backend/app/rules.py` with
  `(id, fired: bool, weight: float, reason: str)` and `to_dict()`.
- Implemented pure detection functions for all 13 rules from Phase 4:
  - `R01_NO_PAYLOAD`: fires when environment and behaviour payloads are empty.
  - `R02_WEBDRIVER`: fires when `navigator.webdriver == true`.
  - `R03_UA_PLATFORM_MISMATCH`: checks OS family consistency with `navigator.platform`.
  - `R04_UA_HINTS_MISMATCH`: checks UA vs Client Hints platform and brands consistency.
  - `R05_TZ_LANG_MISMATCH`: soft regional plausibility and valid terrestrial timezone ranges.
  - `R06_SOFTWARE_RENDERER`: flags SwiftShader, llvmpipe, virtual, and software WebGL renderers.
  - `R07_ZERO_PLUGINS_DESKTOP`: flags desktop browsers reporting zero plugins (headless marker).
  - `R08_VIEWPORT_ANOMALY`: detects non-positive window sizes, viewport > screen, or viewport > outer.
  - `R09_TOUCH_INCONSISTENT`: flags mobile devices reporting 0 touch points or touch unsupported.
  - `R10_NATIVE_FUNCTION_TAMPER`: flags native function integrity verification failures.
  - `R11_UNTRUSTED_EVENTS`: detects synthesized `isTrusted == false` input events in mouse/keys.
  - `R12_TOO_FAST`: flags actions completing unnaturally fast (<200ms after nonce or <50ms first action).
  - `R13_RATE_LIMIT`: hard rule triggered when server request-rate limits are exceeded.
- Added `evaluate_all_rules()` helper evaluating R01 through R13 with weight overrides.
- Added 62 unit tests in `backend/tests/test_rules.py` covering pass/fail cases for each rule,
  missing data safety, and full ruleset evaluations.
- All tests and lint pass cleanly (66 ML + 79 backend = 145 tests).

## Exact next step

- Task P4-03: Combine rule weights into a rule score in [0, 1] using noisy-OR formula
  `rule_score = 1 - prod(1 - weight_i for fired rules)` with reasons list; bypass model on hard rules.

## Files touched in P4-02

- `backend/app/rules.py`
- `backend/tests/test_rules.py`
- `PROGRESS.md`
- `HANDOFF.md`

## Validation

- `python scripts/tasks.py test-fast` - 145 passed.
- `python scripts/tasks.py lint` - clean (0 errors across 71 files).

## Known problems / gotchas

- Phase 4 work continues on branch `phase-4-env-rules`.
- Windows pytest cache warnings are pre-existing and harmless.

## Questions for the human

- None.

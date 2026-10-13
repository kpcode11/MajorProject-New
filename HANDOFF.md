# Handoff

**Updated:** 2026-10-14  |  **By:** Copilot  |  **Branch:** phase-3-keyboard  |  **Last commit:** pending

## Current task

- ID: P3-05 — synthetic keyboard bots
- State: ready to start.

## Done in the previous task

- Added `ml/src/botguard_ml/features/keyboard.py`.
- Implemented text-agnostic Appendix A.3 features:
  dwell and flight distributions, typing speed, down-down intervals,
  rollover, burst and pause structure, lag-1 flight autocorrelation,
  dwell-flight correlation, interval regularity, and safe missing values for
  SDK-only fields.
- Added feature schema validation and focused hand-computed tests.

## Exact next step

- Implement deterministic synthetic keyboard generators K1, K2, K3, and K4
  from Appendix D.1, fitting K3 parameters only from training participants and
  keeping K3 held out from training evaluation.

## Files touched in P3-04

- `ml/src/botguard_ml/features/keyboard.py`
- `ml/tests/test_keyboard_features.py`
- `docs/plan/phase_3.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Features accept canonical timing and coarse `key_class` only; do not add
  text or key identities.
- The Aalto loader produces human-only windows. Synthetic bot labels belong
  to the next task.
- Work is on the dedicated `phase-3-keyboard` branch.

## Questions for the human (P3-05)

- None.

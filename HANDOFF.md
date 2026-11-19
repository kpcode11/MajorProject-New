# HANDOFF.md

- **Last updated:** 2026-11-19
- **Branch:** `phase-10-final-eval-release`
- **Current phase:** Phase 10 — Final evaluation, documentation, and release (`docs/plan/phase_10.md`)
- **Last completed tasks:** `P10-09` (Claims checker, `385510b`), `P10-11` (Release metadata: MIT `LICENSE`, `CITATION.cff`, git tag `v1.0.0`)
- **Remaining TODO task:** `P10-10` — Demo-video script (`docs/demo_script.md`; human records the video `[HUMAN]`)

## What was just done
- **P10-09 (`385510b`):** Added `scripts/check_claims.py`, wired it into `.github/workflows/ci.yml`, added 3 tests in `ml/tests/test_check_claims.py`, fixed stale keyboard hyperparameters in `docs/model_card.md` and unbacked table cells in `README.md`, and saved `results/system/claims_check.json`.
- **P10-11:** Added MIT `LICENSE`, CFF 1.2.0 `CITATION.cff` (`v1.0.0`), updated `README.md` licence/citation links, verified `check_claims.py` + `lint` + `test-fast`, committed, and created annotated git tag `v1.0.0`.

## Exact next step
1. Complete `P10-10` (`docs/demo_script.md`) if desired, and obtain `[HUMAN]` sign-off on final results text and demo recording.
2. Merge `phase-10-final-eval-release` to `main` and push branch + `v1.0.0` tag when ready.

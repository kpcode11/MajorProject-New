# HANDOFF.md

- **Last updated:** 2026-11-19
- **Branch:** `phase-10-final-eval-release`
- **Current phase:** Phase 10 — Final evaluation, documentation, and release (`docs/plan/phase_10.md`)
- **Last completed task:** `P10-09` (Claims checker)
- **Next task:** `P10-11` (Release metadata: `CITATION.cff`, `LICENSE`, tag `v1.0.0` — awaiting human licence choice) / `P10-10` (Demo-video script `[HUMAN]`)

## What was just done
- **P10-09 (`scripts/check_claims.py`):** Implemented stdlib-only claims checker extracting 400 empirical numeric claims from `README.md` and `docs/model_card.md` and verifying them against 3,195 measured values across `results/` CSV/JSON files (plus 14/14 canonical headline checks).
- **Remediated doc mismatches caught by the checker:** Updated stale keyboard hyperparameters in `docs/model_card.md` (`C = 0.1`, `n_estimators = 242`, `learning_rate = 0.0806`, `num_leaves = 21`, `min_child_samples = 33`, `subsample = 0.8219`, `colsample_bytree = 0.8716` from `results/keyboard/hparams.json`), aligned `README.md` baseline/ablation rows strictly to `results/mouse/baselines.csv` and `results/mouse/ablations.csv`, and exact-matched CaptchaSolve30k FPR range (`31.71%`–`57.25%`).
- **CI & tests:** Wired `python scripts/check_claims.py` into `.github/workflows/ci.yml`, generated `results/system/claims_check.json`, and added 3 tests in `ml/tests/test_check_claims.py`.

## Exact next step
1. Confirm licence choice from human (e.g., MIT, Apache-2.0, GPL-3.0) and whether to tag `v1.0.0` now on `phase-10-final-eval-release`.
2. Create `LICENSE`, `CITATION.cff`, verify `python scripts/tasks.py lint` & `python scripts/tasks.py test-fast`, update `PROGRESS.md` + `HANDOFF.md`, commit `P10-11`, and create annotated git tag `v1.0.0`.

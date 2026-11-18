# Handoff

**Updated:** 2026-11-18 20:11  |  **By:** Antigravity  |  **Branch:** phase-9-dashboard-privacy  |  **Last commit:** see `git log -1`

## Current task
- ID: P10-02 — Final experiments
- State: `DONE` (next task is **P10-03** — `System-level results`)

## Done in Phase 10 so far
- Recorded human decision in `docs/decision_log.md` to skip optional trajectory neural model tasks (`P9-14`, `P9-15` marked `SKIPPED` in `PROGRESS.md`) and proceed directly to Phase 10.
- **P10-01 & P10-02:** Implemented `scripts/eval_all.py` and wired `python scripts/tasks.py eval-all` in `scripts/tasks.py`, generating 78 CSV/Markdown tables and 7 PNG figures under `results/` and syncing report-ready assets to `docs/report_assets/` (`results/eval_all_manifest.json`, `docs/report_assets/manifest.json`). Completed all Appendix E final experiments: dataset summary (`table1_dataset_summary`), baselines (`table2a_mouse_baselines`, `table2b_keyboard_baselines`), in-distribution / cross-phase / cross-dataset / CaptchaSolve30k human-FPR splits (`table3a_mouse_evaluation_splits`, `table3b_captchasolve30k_human_fpr`), LOBO and per-generator / K3-holdout / speed-tercile evaluations (`table4a_mouse_lobo`..`table4d_keyboard_speed_terciles`), feature-group / shortcut / rule-layer ablations (`table5a_mouse_feature_ablations`, `table5b_rule_layer_ablation`), pseudo-session fusion & modality availability (`table6a_fusion_comparison`, `table6b_modality_availability`), 1% / 5% / 20% bot prevalence reweighting (`table7a_mouse_prevalence`, `table7b_keyboard_prevalence`), policy challenge-band threshold trade-off curves (`table7c_threshold_tradeoff`), and all 7 required figures (`fig1_roc_pr_curves.png`..`fig7_latency_histogram.png`); verified by `ml/tests/test_eval_all.py`.

## Exact next step
- Start **P10-03** (`System-level results`): consolidate simulator outcomes per tier, latency distribution, and throughput under `results/system/`.

## Files touched (recent)
- `scripts/eval_all.py`, `scripts/tasks.py`, `ml/tests/test_eval_all.py`, `docs/decision_log.md`, `docs/report_assets/*`, `results/*`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/status.py
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast

## Known problems / gotchas
- Always use `_AsgiTestClient` from `test_api.py` in backend unit tests (never `fastapi.testclient.TestClient`, which hangs inside the Windows sandbox due to `anyio` socketpair creation).
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

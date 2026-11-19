# HANDOFF.md

- **Last updated:** 2026-11-19
- **Branch:** `phase-10-final-eval-release`
- **Current phase:** Phase 10 — Final evaluation, documentation, and release (`docs/plan/phase_10.md`)
- **Last completed tasks:** `P10-06` (Final model card), `P10-07` (Final technical documentation), `P10-08` (Final README)
- **Next task:** `P10-09` — Claims checker (`scripts/check_claims.py`)

## What was just done
- **P10-06 (`docs/model_card.md`):** Finalised model card with Executive Summary, Intended/Prohibited Uses, Dataset Availability disclosure (including unavailable `BeCAPTCHA-Mouse`/`CMU` and skipped Phase 8 `touch: null`), Mouse/Keyboard/Fusion metrics with 95% CIs, prevalence reweighting, threshold trade-offs, system serving performance, fairness & accessibility (`MISSING_MOUSE_VALID_KB_MAX_SCORE=0.50`, `axe-core` `0` violations across `11` states), Appendix E.7 honesty checklist, and no-auto-training update/governance policy.
- **P10-07 (`docs/architecture.md`, `docs/api.md`, `docs/signals.md`, `docs/threat_model.md`):** Updated architecture, API, and signals docs to match final Phase 9–10 implementation (`120` mouse / `31` keyboard features, `R01`–`R13`, `policy.yaml` fail-safe, `sendRawTrace=false`, rotating `X-Session-Id`, `retention.py` 7d/30d TTL, `/portal-api/*`, `/admin/*`, `touch: null`), and created `docs/threat_model.md`.
- **P10-08 (`README.md`):** Finalised `README.md` with updated Mermaid diagram, 7-component layout, dataset acquisition & disclosures, verified ML & end-to-end system/load/security tables, quickstart (`setup`, `demo`, `eval-all`, `loadtest`), Appendix E.7 honesty checklist, docs index, and dataset citations/licences.
- **Bonus evaluation fixes:** Replaced hardcoded rule-layer ablation in `scripts/eval_all.py` with measured replay (`scripts/rule_layer_ablation.py`), fixed `latency_ms` key in `scripts/system_results.py`, and regenerated `results/` and `docs/report_assets/` via `python scripts/tasks.py eval-all`.

## Exact next step
1. Set `P10-09` to `IN_PROGRESS` in `PROGRESS.md` and `HANDOFF.md`.
2. Implement `scripts/check_claims.py` (per `docs/plan/phase_10.md` P10-09) to extract numeric claims from `README.md` and `docs/model_card.md` (and report docs) and verify them against `results/` CSV/JSON files, outputting a report and failing on mismatches.
3. Add unit tests for `scripts/check_claims.py`, run it on the repo, fix any discrepancies found, run `python scripts/tasks.py lint` and `python scripts/tasks.py test-fast`, update `PROGRESS.md` + `HANDOFF.md`, and commit as `P10-09: ...`.

## Key commands
```powershell
python scripts/status.py
python scripts/tasks.py lint
python scripts/tasks.py test-fast
python scripts/tasks.py eval-all
```

# Handoff

**Updated:** 2026-11-18 21:15  |  **By:** Antigravity  |  **Branch:** phase-10-final-eval-release  |  **Last commit:** see `git log -1`

## Current task
- ID: P10-04 — Load testing
- State: `DONE` (next task is **P10-05** — `Security checks`)

## Done in Phase 10 so far
- Recorded human decision in `docs/decision_log.md` to skip optional trajectory neural model tasks (`P9-14`, `P9-15` marked `SKIPPED` in `PROGRESS.md`) and proceed directly to Phase 10.
- **P10-01 & P10-02 (`87f6b29`):** Implemented `scripts/eval_all.py` and wired `python scripts/tasks.py eval-all` in `scripts/tasks.py`, generating 78 CSV/Markdown tables and 7 PNG figures under `results/` and syncing report-ready assets to `docs/report_assets/` (`results/eval_all_manifest.json`, `docs/report_assets/manifest.json`), verified by `ml/tests/test_eval_all.py`.
- **P10-03 (`7d8b3c6`):** Added `scripts/system_results.py` (wired into `scripts/eval_all.py`) generating `results/system/sim_summary.csv` and `results/system/system_results.{json,csv,md}` (`docs/report_assets/table8_system_results.{csv,md}`) consolidating simulator tier outcomes, per-tier latency distributions, ONNX+rule scoring latency percentiles, throughput (`325.58 req/s`), SDK gzip sizes, and `axe-core` audit counts; verified by `backend/tests/test_system_results.py`.
- **P10-04:** Added `loadtest/runner.py` (wired to `python scripts/tasks.py loadtest`), `loadtest/locustfile.py`, and `loadtest/k6_scenarios.js` executing the 4 required scenarios (`normal_mix`, `protected_endpoint_flood`, `nonce_flood`, `malformed_assess_flood`; `630` requests @ `1155.42 req/s`, `0` `5xx` errors, and `0/460` malicious requests reaching the protected API) with localhost allowlist safety enforcement, saving `results/system/loadtest_summary.{json,csv,md}` and `docs/report_assets/table8_loadtest_summary.{csv,md}`, verified by `backend/tests/test_loadtest.py`.

## Exact next step
- Start **P10-05** (`Security checks`): run replay/tamper/oversize/rate-limit security checks, dependency audit (`pip-audit`, `npm audit`), and static analysis (`bandit` on backend code), and save results under `results/system/`.

## Files touched (recent)
- `loadtest/__init__.py`, `loadtest/runner.py`, `loadtest/locustfile.py`, `loadtest/k6_scenarios.js`, `backend/tests/test_loadtest.py`, `scripts/tasks.py`, `results/system/loadtest_summary.*`, `docs/report_assets/table8_loadtest_summary.*`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/status.py
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast

## Known problems / gotchas
- Always use `_AsgiTestClient` from `test_api.py` (or direct coroutine `.send(None)` stepping) in backend unit tests; never use `fastapi.testclient.TestClient` or `asyncio.run()` inside the Windows sandbox because event-loop self-pipe `socketpair()` hangs.
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

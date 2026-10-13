# Handoff

**Updated:** 2026-10-13  |  **By:** Codex  |  **Branch:** phase-1-dataset-audit  |  **Last commit:** 44974f9

## Current task

- ID: P1-12 — data manifest
- State: ready to start.

## Done in this task so far

- P0-01 created and committed the repository skeleton and ignore rules.
- P0-02 created and committed the durable handoff/progress files, plan copies, phase files, and tool pointers.
- P0-03 recorded the supplied environment and dataset configuration in `d63224c`.
- P0-04 added and validated Python package environments in `0550595` and `adea826`.
- P0-05 added the cross-platform task runner and status script in `9534e33`.
- P0-06 added the Windows Python CI workflow in `63a2c00`.
- P0-07 completed Phase 0 and created this branch in `015cc73`.
- P1-01 added the safe inventory command in `a6a0bfa`; P1-02 documented observed datasets in `31e0ecc`.
- P1-03 added and committed the streaming Bournemouth loader in `94d15f4`.
- P1-04 implemented the IEEE blog-bots loader and fixture tests in `c8c43c9`.
- P1-05 implemented the CaptchaSolve30k streaming loader and decoder tests in `6aeab38`.
- P1-06 implemented canonical mouse-event windowing and focused tests in `d0a28c7`.
- P1-07 cloned DELBOT-Mouse shallowly, inspected its 4.6 MB archive, and added a streaming loader and dataset card in `72bef69`.
- P1-08 recorded dataset availability decisions in `04e249c`.
- P1-09 added the incremental `data-audit` command and focused tests in `a4a3bd5`.
- P1-10 added and ran the bounded EDA script in `44974f9`.
- P1-11 added the pairwise human-only fingerprint experiment; commit is pending.

## Exact next step

- Update `data/manifest.json` with source metadata and hashes according to the manifest rules, then validate and commit as `P1-12: add data manifest`.

## Files touched (uncommitted or recently changed)

- `138dbc9` — P0-01 repository skeleton.
- `b59792d` — P0-02 handoff system and split plan.
- `docs/env.md` — human-provided system details; Docker CLI is absent from the current shell PATH.
- `config/datasets.example.yaml` — portable dataset configuration template.
- `ml/pyproject.toml`, `backend/pyproject.toml` — package metadata and dependencies.
- `ml/.venv`, `backend/.venv` — installed local development environments (ignored by Git).
- `scripts/tasks.py`, `scripts/status.py` — validated setup, lint, test, status, and placeholder commands.
- `.github/workflows/ci.yml` — Windows Python 3.14 setup, lint, and fast-test workflow.
- `README.md` — project scope, current status, and development commands.
- `scripts/inventory.py` — bounded inventory command; first Bournemouth report saved.
- `docs/datasets/*.md` — observed cards for Bournemouth, IEEE blog bots, and CaptchaSolve30k.
- `ml/src/botguard_ml/loaders/web_bot_detection.py` — streaming phase-1/phase-2 loader; smoke shard validated.
- `ml/src/botguard_ml/loaders/ieee_blog_bots.py` — to be added for the current task.
- `ml/tests/test_ieee_blog_bots.py` and `ml/tests/fixtures/ieee_session.json` — IEEE loader coverage.
- `ml/src/botguard_ml/loaders/captchasolve30k.py` and `ml/tests/test_captchasolve30k.py` — CaptchaSolve30k loader and decoder coverage.
- `ml/src/botguard_ml/features/windowing.py` and `ml/tests/test_windowing.py` — canonical mouse windowing and coverage.
- `ml/src/botguard_ml/loaders/delbot_mouse.py` and `ml/tests/test_delbot_mouse.py` — DELBOT archive loader and coverage.
- `docs/datasets/delbot_mouse.md` — DELBOT dataset card.
- `scripts/data_audit.py` and `scripts/test_data_audit.py` — incremental audit implementation and coverage.
- `ml/notebooks/01_mouse_eda.py` and `results/mouse/eda/` — bounded EDA script and generated figures.
- `scripts/dataset_fingerprint.py` and `results/mouse/fingerprint.json` — human-only fingerprint experiment and current insufficient-data report.

## Commands to run first

    python scripts/status.py
    python scripts/tasks.py test-fast

## Known problems / gotchas

- Git marks this workspace safe in the local user's global Git configuration due to a sandbox ownership mismatch.

## Dataset / long-job state

- No dataset operation has started.

## Questions for the human (P1-12)

- None.

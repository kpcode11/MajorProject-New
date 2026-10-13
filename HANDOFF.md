# Handoff

**Updated:** 2026-10-13  |  **By:** Codex  |  **Branch:** phase-1-dataset-audit  |  **Last commit:** a6a0bfa

## Current task

- ID: P1-02 — write observed dataset cards
- State: done — awaiting commit; P1-03 is next.

## Done in this task so far

- P0-01 created and committed the repository skeleton and ignore rules.
- P0-02 created and committed the durable handoff/progress files, plan copies, phase files, and tool pointers.
- P0-03 recorded the supplied environment and dataset configuration in `d63224c`.
- P0-04 added and validated Python package environments in `0550595` and `adea826`.
- P0-05 added the cross-platform task runner and status script in `9534e33`.
- P0-06 added the Windows Python CI workflow in `63a2c00`.
- P0-07 completed Phase 0 and created this branch in `015cc73`.
- P1-01 added the safe inventory command in `a6a0bfa`.

## Exact next step

- Commit P1-02, then inspect one observed Bournemouth session structure for the P1-03 loader fixture.

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

## Commands to run first

    python scripts/status.py
    python scripts/tasks.py test-fast

## Known problems / gotchas

- Git marks this workspace safe in the local user's global Git configuration due to a sandbox ownership mismatch.

## Dataset / long-job state

- No dataset operation has started.

## Questions for the human (P1-02)

- None.

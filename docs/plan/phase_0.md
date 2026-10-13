## Phase 0 — Scaffolding and handoff system

**Goal:** A clean repository where any agent can pick up the work, with the handoff files, task runner and CI in place.

### Tasks

- [ ] **P0-01** Create the repository layout (Section 2) with empty modules and docstrings. Add `.gitignore` (data, logs, venvs, `node_modules`, `*.parquet`, `*.zip`, `.env`, `config/datasets.local.yaml`, large `*.onnx`), `.gitattributes` (`* text=auto`), `.env.example`, `data/README.md`.
- [ ] **P0-02** Create `AGENTS.md`, `HANDOFF.md`, `PROGRESS.md` (task table below, filled from this plan), `docs/decision_log.md`, and the thin pointer files `.github/copilot-instructions.md` and `.cursor/rules/botguard.mdc` (exact contents in Appendix F and G). Copy this plan to `docs/MASTER_PLAN.md` and run `python scripts/split_plan.py` (Appendix G.4) to create `docs/plan/phase_N.md` files.
- [ ] **P0-03** `[HUMAN]` Ask the human for: RAM, free disk space, CPU cores, Python version, Node version, whether Docker/WSL2 is installed, whether `git clone` works from the agent's environment. Record in `docs/env.md`. Create `config/datasets.local.yaml` from Section 5.1 and `config/datasets.example.yaml` (placeholder root).
- [ ] **P0-04** Create `ml/pyproject.toml` and `backend/pyproject.toml` with core dependencies: `numpy`, `pandas`, `pyarrow`, `scikit-learn`, `lightgbm`, `shap`, `matplotlib`, `pyyaml`, `optuna`, `onnxruntime`, `skl2onnx`/`onnxmltools` (choose a working LightGBM-to-ONNX path and note it in the decision log), `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `pyjwt`, `redis` (optional extra), `fakeredis` (dev), `pytest`, `hypothesis`, `ruff`, `mypy`. Install into per-package virtual environments.
- [ ] **P0-05** Implement `scripts/tasks.py` with the commands in Section 3.1 (initially `setup`, `lint`, `test`, `test-fast`, `status`; others may print "not implemented yet") and `scripts/status.py` (Appendix G.2).
- [ ] **P0-06** Add `.github/workflows/ci.yml`: install, lint, fast tests for Python (Node jobs are added when `sdk/` exists).
- [ ] **P0-07** Write `README.md` stub, make the first commit on `main`, create branch `phase-1-dataset-audit`.

### `PROGRESS.md` task table (create exactly this structure; the agent fills commit hashes)

```markdown
| ID | Phase | Task (short) | Status | Commit | Notes |
|----|-------|--------------|--------|--------|-------|
| P0-01 | 0 | Repo skeleton and ignore files | TODO | | |
| ... one row per task ID in this plan ... |
```

### Acceptance criteria

- [ ] `python scripts/tasks.py setup && python scripts/tasks.py lint && python scripts/tasks.py test-fast` succeeds on a fresh clone.
- [ ] `python scripts/status.py` prints the next task correctly.
- [ ] `docs/plan/` exists; `AGENTS.md`, `HANDOFF.md`, `PROGRESS.md` exist and are consistent with each other.
- [ ] CI is green.

---

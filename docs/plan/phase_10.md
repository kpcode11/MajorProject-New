## Phase 10 — Final evaluation, documentation, release

**Goal:** Reproducible, honest results and a polished repository.

### Tasks

- [ ] **P10-01** `python scripts/tasks.py eval-all` regenerates every table and figure from scratch into `results/` and copies the report-ready ones to `docs/report_assets/`.
- [ ] **P10-02** Final experiments (Appendix E): in-distribution, leave-one-dataset-out, leave-one-bot-type-out (mouse); per-generator (keyboard, touch); fusion (pseudo-sessions); ablations (feature groups, with/without shortcut features, with/without rule layer); calibration; threshold trade-off curves (challenge band width vs bot pass-through on held-out data).
- [ ] **P10-03** System-level results: simulator outcomes per tier; latency distribution; throughput.
- [ ] **P10-04** Load test (`loadtest/`): Locust or k6 scenarios — normal mix, flood of plain HTTP requests to a protected endpoint, flood of `/v1/nonce`, flood of malformed `/v1/assess`. Report requests/second, p50/p95/p99 latency, error rates, and how many malicious requests reached the protected API.
- [ ] **P10-05** Security checks: run the replay/tamper/oversize/rate-limit test suite; `pip-audit`, `npm audit`; `bandit` on backend code; record results.
- [ ] **P10-06** Finalise `docs/model_card.md` (intended use, data, metrics with confidence intervals, limitations, fairness/accessibility notes, update policy).
- [ ] **P10-07** Finalise `docs/architecture.md`, `docs/api.md`, `docs/signals.md`, `docs/threat_model.md`.
- [ ] **P10-08** `README.md`: overview, architecture diagram, quickstart (`python scripts/tasks.py setup`, `python scripts/tasks.py demo`), how to reproduce results, dataset acquisition instructions, limitations, licences and citations.
- [ ] **P10-09** Claims check script `scripts/check_claims.py`: every number quoted in `README.md` and `docs/model_card.md` must match a value in `results/` (fail CI otherwise).
- [ ] **P10-10** Record a demo video script and a `docs/demo_script.md` (the human records the video `[HUMAN]`).
- [ ] **P10-11** Tag release `v1.0.0`; create `CITATION.cff` and `LICENSE` (ask the human which licence).

### Acceptance criteria

- [ ] Fresh-clone reproduction works: documented steps produce the same tables (within seed-determined variation).
- [ ] CI green, including claims check.
- [ ] All limitations from Section 1.2 are stated in README and model card, plus: which datasets were unavailable (BeCAPTCHA-Mouse, CMU) and whether Path A or Path B was followed in Phase 8.
- [ ] `[HUMAN]` signed off the final results text.

---

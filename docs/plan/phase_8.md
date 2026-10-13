## Phase 8 — Mobile extension (decision gate)

**Goal:** Support mobile/touch devices honestly. No touch dataset is currently available, so this phase begins with a human decision gate and then follows **Path A** (a touch dataset is obtained) or **Path B** (it is not).

### Decision gate

- [ ] **P8-01** `[HUMAN]` The human tries to obtain at least one candidate touch dataset (Section 5.5: HuMIdb, BioIdent, SU-AIS BB-MAS, H-MOG) and places it under the datasets root, or states that none could be obtained. The agent records the outcome in `docs/decision_log.md` and `config/datasets.local.yaml` (`mobile_touch: available | none`), then follows Path A or Path B. Do not wait for this gate to complete other phases.

### Path A — a human touch dataset is available

- [ ] **P8-02A** Inventory and dataset card for the obtained dataset (same safe procedure as Phase 1). Respect size limits (H-MOG is about 6 GB compressed: never extract everything).
- [ ] **P8-03A** Loader producing canonical `touch_events` shards (Section 4.3), with gesture segmentation (tap, swipe, drag), device metadata where available, `--max-users` sampling, resumable shards.
- [ ] **P8-04A** Touch features (Appendix A.4) with unit tests and property tests.
- [ ] **P8-05A** Synthetic touch bot generators T1-T4 (Appendix D.2) with tests; hold out T3.
- [ ] **P8-06A** Train and evaluate with the Phase 2 protocol: grouped by user, held-out generator, per-gesture-type results, human-FPR report. Calibrate and export ONNX to `backend/models/touch-<version>/`.
- [ ] **P8-07A** Extend fusion: touch replaces mouse on touch devices (device class from environment signals and observed events), same missing-modality policy; update the fusion metadata.
- [ ] **P8-08A** Backend: extend schemas and scoring for the touch payload; update the contract test and fixtures.
- [ ] **P8-09A** Update `docs/model_card.md` and `results/touch/` with limitations (authentication datasets used for bot detection, synthetic bots, device variety).

### Path B — no touch dataset (mobile readiness without a trained touch model)

- [ ] **P8-02B** SDK `collectors/touch.ts`: capture `touchstart/move/end` (position, time, radius/force when exposed), bounded buffers, no content capture. Update the payload schema (Appendix B.3, `behaviour.touch`) and the contract test.
- [ ] **P8-03B** Backend: accept the touch payload and set `device_class`; compute touch features with the unit-tested Appendix A.4 code **only for logging and future use**, not for the decision.
- [ ] **P8-04B** Policy for touch sessions without a trained model: decision uses the rule layer, rate limits and a conservative step-up policy; logs record `model_coverage: {touch: none}` and `degraded_modality: true`; the exact policy is written to `docs/decision_log.md` and `docs/architecture.md`.
- [ ] **P8-05B** Verify the fairness rule: a touch session with no mouse events is **not** penalised for missing mouse input (test).
- [ ] **P8-06B** Mobile-friendly step-up (large tap/press-and-hold target, no hover dependence) and responsive portal layout; test with browser device emulation.
- [ ] **P8-07B** Simulator tier "mobile emulation" (Playwright device emulation with scripted taps/swipes) for the demo only.
- [ ] **P8-08B** State the limitation prominently in README, model card and presentation: "touch behaviour is not modelled; mobile protection relies on rules, rate limits and step-up". Optionally run the mouse model on CaptchaSolve30k `touchscreen=true` sessions as an informal sanity check and report it as such (not as touch validation).

### Acceptance criteria

- [ ] The gate outcome is recorded in `docs/decision_log.md`.
- [ ] **Path A:** `python scripts/tasks.py train-touch` reproduces results; held-out generator and per-gesture results reported; touch payload passes the contract test; touch sessions are not penalised for missing mouse input.
- [ ] **Path B:** touch payload accepted and logged; touch sessions follow the documented conservative policy; limitation stated in README and model card; fairness test passes.
- [ ] `[HUMAN]` checked the mobile demo (emulated or on a real phone).

**Milestone M3 reached** when this phase passes (either path).

---

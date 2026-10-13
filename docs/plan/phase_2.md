## Phase 2 — Mouse model

**Goal:** A calibrated mouse-behaviour classifier with honest in-distribution, cross-phase, cross-dataset and held-out-bot-type results, plus a human-FPR stress test, exported to ONNX.

### Tasks

- [ ] **P2-01** Implement segmentation inside each window (`features/mouse.py: segment_trajectory`, Appendix A.1) with unit tests (pause splitting, minimum points).
- [x] **P2-02** Implement the mouse features of Appendix A.2 (per segment) and the window-level aggregation (mean, std, max over segments plus window-level timing stats). Every feature has a docstring (formula, units) and a unit test with a hand-computed example (straight line has straightness 1.0; constant speed has zero acceleration). Add `hypothesis` property tests (finite outputs; straightness in [0, 1]; translation invariance).
- [x] **P2-03** Build window feature shards from the canonical data (`python scripts/tasks.py train-mouse --stage features --max-sessions N`). Resumable per shard; write `data/processed/mouse_features/` plus `mouse_features.schema.json`. Include `dataset`, `domain`, `session_id`, `subject_id`, `split_group`, `label`, `bot_type`.
- [x] **P2-04** Implement `splits.py`: `grouped_split`, `cross_phase_split` (Bournemouth part 1 vs part 2), `cross_dataset_split` (train datasets, test dataset), `leave_one_bot_type_out`. Add a test asserting that no `split_group` appears in two splits.
- [x] **P2-05** Baselines on identical splits: majority class, Logistic Regression (scaled), Random Forest, LightGBM. Save `results/mouse/baselines.csv`.
- [x] **P2-06** Hyperparameter search for LightGBM (Optuna; default 30 trials, time-boxed) with **grouped** CV on training data only. Save `results/mouse/hparams.json`.
- [x] **P2-07** Session-level aggregation: define how window scores combine into a session or request score (mean, mean of top-k, max, small learned aggregator). Choose using validation data only; save the comparison.
- [ ] **P2-08** Calibration (isotonic or Platt) on a separate calibration split; reliability curve and Brier score.
- [ ] **P2-09** Evaluation (Appendix E): in-distribution, cross-phase, cross-dataset (Bournemouth -> IEEE), held-out bot types, plus the **human-FPR stress test on CaptchaSolve30k** (share of windows/sessions flagged at the chosen thresholds, by game type). Group bootstrap CIs. Save tables and figures under `results/mouse/`.
- [ ] **P2-10** Ablations: feature groups (kinematics, geometry, timing, click); with/without shortcut features (`n_points`, `duration_ms`, `dt_mean`, `dt_mode_fraction`).
- [ ] **P2-11** SHAP summary and a function returning top-3 contributing features per scored window.
- [ ] **P2-12** Export ONNX to `backend/models/mouse-<version>/model.onnx` and `metadata.json` (feature order, version, data manifest hash, metrics, calibration parameters, git commit). Add the ONNX-vs-native parity test (tolerance 1e-4).
- [ ] **P2-13** Write the mouse section of `docs/model_card.md`, including limitations: small sample sizes, bots created by dataset authors, game-task domain for CaptchaSolve30k, no live human validation.

### Acceptance criteria

- [ ] `python scripts/tasks.py train-mouse` reproduces features, model and results with fixed seeds from the canonical data.
- [ ] Leakage test passes.
- [ ] Cross-phase, cross-dataset, held-out-bot-type and human-FPR results are reported **even if poor**.
- [ ] ONNX parity test passes.
- [ ] If any in-distribution AUC exceeds 0.99, the cause is investigated and documented before reporting.
- [ ] `[HUMAN]` reviewed the results and the written interpretation.

### Pitfalls

- Dataset fingerprinting (the model separates datasets, not humans from bots). Use P1-11 results; normalise timing features per window if needed and re-test.
- Shortcut features (window length, event count, regular timestamps).
- Very small test sets (IEEE): always show confidence intervals and the number of groups.

---

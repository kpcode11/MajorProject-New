## Phase 3 — Keyboard model and desktop fusion

**Goal:** A keystroke-timing model trained on Aalto human typing plus documented synthetic bots, and a score-level fusion with the mouse model.

### Tasks

- [ ] **P3-01** Inventory `Keystrokes` with `scripts/inventory.py` (zip or extracted? number of files? metadata file?). Read `readme.txt`. Write `docs/datasets/aalto_keystrokes.md`. Note the size situation (16 GB unzipped) and the chosen access method (zip streaming vs extracted files).
- [ ] **P3-02** Implement `loaders/aalto_keystrokes.py`: iterate participant files lazily, sample `--max-participants` (default 1,000; seeded), treat each typed sentence as a typing window with at least 10 key events, convert timestamps to the canonical `down_ms`/`up_ms`, **map key identity to `key_class` in memory and drop it**, write sharded `key_events` Parquet with a progress file. Participants whose files are malformed are skipped and counted. Unit tests with a hand-made fixture file in the observed format.
- [ ] **P3-03** Add a test that scans every produced keyboard shard and fails if any column contains key identities, typed text or sentences.
- [ ] **P3-04** Implement text-agnostic keyboard features (Appendix A.3) with unit tests (for example constant-interval input gives `dwell_cv` near 0).
- [ ] **P3-05** Implement synthetic bot generators K1, K2, K3, K4 (Appendix D.1) in `synthetic/keyboard.py`, parameters fitted on **training participants only**, deterministic by seed, with statistical tests.
- [ ] **P3-06** Build keyboard feature shards: human windows plus synthetic bot windows at configurable prevalence. Splits grouped by participant (humans) and by generator + seed block (bots); hold out K3 entirely.
- [ ] **P3-07** Train and evaluate with the Phase 2 protocol (baselines, tuning, calibration, bootstrap CIs). Report **per-generator** recall incl. K3, results by typist speed tercile, and the human FPR at the chosen thresholds.
- [ ] **P3-08** Optional second human source for FPR: if the human obtains SU-AIS BB-MAS (Section 5.5) or if the `ul_keystroke_repo` contains usable data, add a loader and report human FPR on it. Otherwise record "single human source" as a limitation.
- [ ] **P3-09** Export ONNX plus metadata to `backend/models/keyboard-<version>/`; add the parity test.
- [ ] **P3-10** Fusion (`fuse.py`): build **pseudo-sessions** by pairing a mouse window set with a keyboard window set of the **same class** (human with human, bot with bot) using a fixed seed. Compare mouse-only, keyboard-only, average of calibrated probabilities, noisy-OR, and a logistic-regression stacker trained on a validation split. Implement the missing-modality policy (only available modalities are fused; absent is never treated as bot) with tests for: mouse only, keyboard only, both, neither. Save `backend/models/fusion-<version>/metadata.json`. Label all fusion results "pseudo-session evaluation (simulated pairing)".
- [ ] **P3-11** Update `docs/model_card.md` with keyboard and fusion sections and the limitations: human data come from a typing test with prescribed sentences; bots are synthetic; fusion is evaluated on simulated pairings.

### Acceptance criteria

- [ ] `python scripts/tasks.py train-keyboard` reproduces results with small defaults (1,000 participants) in a reasonable time on the laptop; larger runs only after human approval.
- [ ] Loader never loads the whole dataset; memory stays within limits (measured and recorded).
- [ ] The no-key-identity scan test passes.
- [ ] Held-out generator results are reported.
- [ ] Fusion handles all four modality-availability cases.
- [ ] `[HUMAN]` reviewed the limitations text.

**Milestone M1 reached** when Phases 2 and 3 pass.

---

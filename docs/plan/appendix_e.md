## Appendix E — Evaluation protocol

### E.1 Splitting

- `split_group` = `subject_id` for humans; `generator_run_id` for bots. All segments from one group stay together.
- Hold-out structure (mouse):
  1. **In-distribution:** grouped train/validation/calibration/test (for example 60/10/10/20 by group) on Bournemouth.
  2. **Cross-phase:** train on Bournemouth part 1, test on part 2, and the reverse.
  3. **Cross-dataset:** train on Bournemouth (plus DELBOT if obtained), test on the IEEE blog dataset. The IEEE test set is small: report CIs and group counts.
  4. **Leave-one-bot-type-out:** train without one bot class (Bournemouth moderate/advanced; IEEE mimic/fallible), test on it.
  5. **Human FPR stress test:** apply the final model to CaptchaSolve30k (human-only) and report the flagged share by game type. This set is never used for training.
- Hold-out structure (keyboard): participant-grouped splits on Aalto samples; held-out generator K3; optional second human source for FPR.
- Hold-out structure (touch, Path A only): user-grouped splits; held-out generator T3.
- Thresholds are selected on the validation split only. The test split is used once for reporting.

### E.2 Metrics

ROC-AUC; PR-AUC; recall (bot detection rate) at 1% and 5% human false-positive rate; Equal Error Rate; confusion matrix at the chosen threshold; Brier score and reliability curve (calibration); for session-level results, also the share of **human sessions that would be challenged** under the policy bands.

### E.3 Uncertainty

Bootstrap by group (at least 1,000 resamples; seeded) for 95% confidence intervals on every headline metric. Report the number of groups in each test split.

### E.4 Prevalence

Report PR-AUC and precision at operating points under bot prevalence of 1%, 5% and 20% (reweighting or resampling the test set).

### E.5 Required result tables (save as CSV and Markdown in `results/`)

1. Dataset summary (counts per dataset, label, bot type).
2. Baseline comparison per modality (majority, LR, RF, LightGBM).
3. Cross-dataset results (rows: held-out dataset; columns: metrics with CIs).
4. Held-out bot type / generator results.
5. Feature-group ablation and shortcut-feature ablation.
6. Fusion comparison on pseudo-sessions (mouse only, keyboard only, average, noisy-OR, stacker) — labelled as simulated pairing.
7. Threshold trade-off: human challenge rate vs bot pass-through.
8. System results: simulator outcomes per tier, latency percentiles, load-test summary.

### E.5.1 Required figures

ROC and PR curves; reliability diagram; SHAP summary; example trajectories (human vs bot types); ablation bar chart; threshold trade-off curve; latency histogram.

### E.6 Failure analysis

For each modality, list the 10 highest-scoring humans (false positives) and 10 lowest-scoring bots (false negatives) with their key features and a short written explanation. Save as `results/<modality>/failure_analysis.md`.

### E.7 Honesty checklist (must be included in the final report)

- Results are on public benchmarks; no live human validation was done.
- Keyboard and touch bot classes are synthetic.
- Fusion was evaluated on simulated pseudo-sessions.
- Performance may differ on other sites, devices and bot generators.
- Client-side signals can be spoofed; the system raises cost, it does not guarantee prevention.

---

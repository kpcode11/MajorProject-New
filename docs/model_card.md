# BotGuard model card

## Mouse behaviour model

### Model summary

This component estimates whether a browser mouse-trajectory window resembles
the bot or human classes represented in the training data. It is intended as a
passive signal for a mock portal and as one input to a broader risk policy. It
is not an identity, biometric, or employment decision system, and it must not
be used as the sole basis for denying access.

The reference model is a tuned LightGBM binary classifier (`n_estimators=203`,
`learning_rate=0.1406`, `num_leaves=17`, `min_child_samples=27`,
`subsample=0.8790`, `colsample_bytree=0.7921`) selected via Optuna over 5-fold
`StratifiedGroupKFold` (`inner-CV ROC-AUC = 0.9998`). The training pipeline
uses median imputation (`keep_empty_features=True`), isotonic probability
calibration, and a fixed 120-feature schema order, and exports an ONNX model
(`backend/models/mouse-v1/model.onnx`) verified for native-vs-ONNX numerical
parity (`max_abs_diff = 7.52e-08 < 1e-4` across 500 held-out test windows). The
default training seed is `42`. The exported model is only valid when the
consumer supplies the same feature order and preprocessing described in
`metadata.json`.

### Inputs and feature construction

Input events are canonical mouse events containing timestamps and coordinates,
plus session and dataset metadata used only for grouping and evaluation.
Windows are 10 seconds long with a 5-second hop (`O(N)` two-pointer sliding
window). Exact timestamp/coordinate duplicates are removed, chunk-boundary
truncated timestamps in raw Bournemouth Phase 2 exports are repaired before
sorting, and windows with fewer than 20 move events are excluded.

Trajectories are segmented at pauses of at least 100 ms and at click boundary
events. Segments must contain at least 8 points and at least 20 pixels of
path. The 120 features cover:

- kinematics (54 features): speed, acceleration, jerk, angular velocity, and curvature;
- geometry (21 features): path length, displacement, straightness, direction changes,
  bounding-box normalization, and tail reversal;
- timing (38 features): duration, sampling intervals, pauses, peak-speed position, and
  acceleration phase;
- click behaviour (9 features): dwell and pre-click slowdown.

Feature-group ablations and multi-split evaluations also explicitly measure and
remove event-count and timing shortcuts (`n_points`, `duration_ms`, `dt_mean`,
`dt_mode_fraction`, and `window_*` aggregate counts).

### Training and evaluation protocol & empirical results

The pipeline uses deterministic grouped splits (`StratifiedGroupKFold` /
group-preserving train-test partitions) across **28,397 windows from 4,068
sessions** spanning three primary datasets:

- **Bournemouth (`web_bot_detection`)**: Phase 1 (`150` sessions, `7,574` windows) and
  Phase 2 (`299` sessions, `15,277` windows);
- **IEEE Blog Bots (`ieee_blog_bots`)**: `126` sessions (`1,114` windows across
  human, `fallible`, `humanish`, and `mimic` bots);
- **DELBOT-Mouse (`delbot_mouse`)**: `3,493` sessions (`4,432` windows across
  human, `gan`, `naturalmousemotion`, `pyhm`, and `pynput` bots);
- **CaptchaSolve30k (`captchasolve30k`, human-FPR stress test only)**: `300`
  human game sessions (`662` windows across `polygon-stacking`,
  `sheep-herding`, and `thread-the-needle`).

Windows from the same `split_group` never appear in both training and test
partitions (`0` overlapping groups). Full tables with 200-iteration
group-bootstrap 95% confidence intervals are saved under `results/mouse/`:

1. **In-Distribution Baselines & Tuned Models (`results/mouse/baselines.csv`, `evaluation_splits.csv`, 814 test groups / 5,252 windows)**:
   - `majority`: ROC-AUC `0.5000`, PR-AUC `0.6340`, Balanced Accuracy `0.5000`
   - `logistic_regression` (scaled): ROC-AUC `0.9902`, PR-AUC `0.9942`, Balanced Accuracy `0.9554`
   - `random_forest`: ROC-AUC `0.9997`, PR-AUC `0.9998`, Balanced Accuracy `0.9938`
   - `lightgbm` (default): ROC-AUC `0.9997`, PR-AUC `0.9998`, Balanced Accuracy `0.9932`
   - `lightgbm_tuned` (all 120 features): **ROC-AUC `0.9999` `[0.9999, 1.0000]`**, PR-AUC `1.0000`, Recall@1%FPR `0.9994`, Balanced Accuracy `0.9956`
   - `lightgbm_no_shortcuts` (100 non-shortcut features): **ROC-AUC `0.9990` `[0.9982, 0.9996]`**, PR-AUC `0.9991`, Recall@1%FPR `0.9904`, Balanced Accuracy `0.9866`

2. **Cross-Phase & Cross-Dataset Generalization (`results/mouse/evaluation_splits.csv`)**:
   - **Cross-Phase P1 -> P2**: With shortcut features, ROC-AUC is `0.8297` (`[0.7779, 0.8701]`, Balanced Accuracy `0.7426`, Recall@1%FPR `0.0066`) due to sampling-rate shift between Phase 1 and Phase 2. Removing shortcut features (`no_shortcuts`) increases **ROC-AUC to `0.9785` `[0.9715, 0.9846]`**, Balanced Accuracy to `0.9238`, and Recall@1%FPR to `0.6100` (`0.8517` at 5% FPR).
   - **Cross-Phase P2 -> P1**: Removing shortcut features increases **ROC-AUC from `0.9746` to `0.9970` `[0.9959, 0.9980]`**, Balanced Accuracy from `0.8272` to `0.9774`, and Recall@1%FPR from `0.8497` to `0.9690`.
   - **Cross-Dataset (`Bournemouth + DELBOT -> IEEE Blog Bots`, `no_shortcuts`)**: Achieves **ROC-AUC `0.9305` `[0.9006, 0.9551]`** and PR-AUC `0.8977` `[0.8351, 0.9452]` on unseen blog interaction tasks and unseen bot generators (`fallible`, `humanish`, `mimic`).

3. **Leave-One-Bot-Type-Out (`results/mouse/lobo_evaluation.csv`, trained without shortcuts)**:
   - Strong zero-shot detection on unseen heuristic/stochastic bots: `ieee_blog_bots:mimic` (`0.9950` AUC, `0.9762` Recall@1%FPR), `ieee_blog_bots:fallible` (`0.9947` AUC, `0.9603` Recall@1%FPR), `ieee_blog_bots:humanish` (`0.9927` AUC, `0.8983` Recall@1%FPR), `web_bot_detection:advanced` (`0.9710` AUC, `0.9026` Recall@5%FPR), `delbot_mouse:pyhm` (`0.9490` AUC, `0.6909` Recall@5%FPR), `web_bot_detection:moderate` (`0.9195` AUC), `delbot_mouse:naturalmousemotion` (`0.8365` AUC, `0.7640` Recall@5%FPR), and `delbot_mouse:pynput` (`0.8202` AUC).
   - Known failure mode: `delbot_mouse:gan` (`0.4872` AUC when completely held out), demonstrating that adversarial GAN trajectories trained specifically on circle-task human data require in-domain representation or complementary signals.

4. **Human-FPR Stress Test on `CaptchaSolve30k` (`results/mouse/human_fpr_captchasolve30k.csv`)**:
   - Because `CaptchaSolve30k` records fast dragging/aiming gameplay on a 200x200 logical canvas at a fixed 240 Hz tick (`dt_mode_fraction = 1.0`), the all-feature model flags `76.7%`–`95.9%` of game windows at the 5% browsing-human FPR threshold. Removing timing shortcuts reduces false-positive rates to **`31.9%` (`sheep-herding`), `31.7%` (`thread-the-needle`), and `57.2%` (`polygon-stacking`)**, confirming that game-like dragging tasks require domain-specific calibration.

5. **Session Aggregation, Calibration & Ablations (`results/mouse/aggregation.csv`, `calibration.json`, `ablations.csv`)**:
   - Best session-level score aggregator on validation groups: `mean` (session-level test ROC-AUC `1.0000`, Brier `0.0020`).
   - Isotonic calibration on validation groups improves test Brier score from `0.0023` (raw) to **`0.0018`** (vs `0.0035` for Platt scaling).
   - Feature-group ablations (`logistic_regression` reference): `all_with_shortcuts` (`0.9902` AUC), `all_without_shortcuts` (`0.9862` AUC), `group_timing` (`0.9687` AUC), `group_kinematics` (`0.9648` AUC), `group_geometry` (`0.8890` AUC), `group_click` (`0.5330` AUC).

### Intended use

- Combine the mouse score with other privacy-reviewed signals and an explicit
  risk policy.
- Use calibrated scores to select a step-up action, not to identify a person.
- Monitor false-positive rates separately for humans and for each available
  source or task domain.
- Re-evaluate after changes to the feature schema, model, calibration, or
  source datasets.

### Limitations and risks

- Bots were created by dataset authors and may not represent all current
  automated tooling or unseen adversarial generators (for example, held-out
  `delbot_mouse:gan` achieves `0.4872` LOBO ROC-AUC when no GAN examples are in
  the training set).
- CaptchaSolve30k is a 240 Hz game-task domain on a 200x200 logical grid; its
  human false-positive behaviour (`31.7%`–`57.2%` without shortcuts at browsing
  thresholds) does not represent ordinary web browsing.
- Dataset, phase, browser, screen-size, sampling, and task differences can
  create spurious signal (`dataset_fingerprint_accuracy = 0.9985` across raw
  sources). Excluding shortcut features (`n_points`, `duration_ms`, `dt_mean`,
  `dt_mode_fraction`) is essential when transferring across phases (`+0.1488`
  ROC-AUC on `P1 -> P2`).
- Mouse trajectories can be missing, noisy, or affected by accessibility
  devices and assistive technology. Missing data must follow the documented
  failure policy rather than silently becoming a bot decision.

### Privacy and deployment boundaries

The feature pipeline stores movement timing and coordinate-derived statistics,
not typed characters or key identities. Raw trajectories should be retained
only when necessary for an approved local experiment and must follow the
project's dataset licence and privacy rules. CaptchaSolve30k must not be used
for re-identification or biometric profiling.

The target is a mock local portal. The model and bot simulator must not be
presented as a general anti-fraud service, and no deployment decision should
be made from an uncalibrated or unsupported dataset split. The ONNX artifact
must be accompanied by its metadata, feature order, manifest hash, and
evaluation record.

### Status

The mouse behaviour pipeline is trained, calibrated, explained via TreeSHAP,
evaluated across in-distribution, cross-phase, cross-dataset, LOBO, and
`CaptchaSolve30k` stress-test splits, and exported to ONNX with verified
numerical parity (`max_abs_diff = 7.52e-08`). Production deployment in the mock
portal should pair calibrated mouse probabilities with the keyboard/touch
modalities and the backend risk policy.

## Keyboard behaviour model

The keyboard component estimates whether a privacy-safe typing-timing window
resembles the human or synthetic bot classes used in the research pipeline.
It uses Logistic Regression with median imputation and standard scaling, and
exports an ONNX artifact with an explicit feature order and metadata. The
pipeline stores coarse key classes and timing-derived features only; typed
sentences, user input, key identities, and keystroke identifiers are not
persisted.

Aalto provides the current human source. It is a prescribed typing test, not
ordinary browsing behaviour, and no second human keyboard source is configured
locally. K1-K4 are documented synthetic timing generators; K3 is held out
from training and used only for evaluation. Keyboard results must include
grouped splits, per-generator recall, speed-tercile results, human
false-positive rates, and uncertainty intervals.

## Desktop score fusion

Fusion is evaluated as a pseudo-session experiment: mouse and keyboard
windows are paired within the same class using a fixed seed. These pairings
are simulated, not observations from the same real session. The comparison
includes mouse-only, keyboard-only, the average of calibrated probabilities,
noisy-OR, and a Logistic Regression stacker trained on a validation split.
Missing modalities are omitted from the fusion calculation; absence is never
treated as evidence of bot activity. Fusion metadata labels results as
`pseudo-session evaluation (simulated pairing)`.

The keyboard and fusion components remain research-stage. Human review,
complete source-data evaluation, calibration checks, privacy review, and the
later backend risk policy are required before any deployment decision.

# BotGuard Model Card (`v1.0.0`)

**Project:** Passive Behaviour-Based Bot Detection to Replace CAPTCHA (SIH1672)
**Models covered:** `mouse-v1` (Tuned LightGBM ONNX), `keyboard-v1` (Calibrated Scaled Logistic Regression ONNX, plus `keyboard-lgbm-v1` comparison), `fusion-v1` (Score-Level Combiner), and `R01`–`R13` Deterministic Environment Rules.
**Mobile touch status (Phase 8):** **Skipped (`touch: null`)** per human decision (`docs/decision_log.md`, 2026-11-14). Desktop (mouse + keyboard + environment rules) is the sole trained scope of `v1.0.0`.

## Executive Summary & Intended Use

### Intended Use
- Provide passive, low-friction bot-risk scoring for a **local mock resident portal** (`DEMO — not a government portal`) so low-risk human sessions proceed without visual or audio CAPTCHA puzzles.
- Map calibrated risk probabilities combined with deterministic environment rules (`max(model_score, rule_score)`) into action-specific policy verdicts (`allow`, `challenge`, `deny`), returning only coarse bands (`low`, `medium`, `high`) to untrusted clients.
- Support optional client-side local feature extraction (`sendRawTrace=false`, verified to `< 1e-9` parity in `results/system/local_features_parity.json`) so raw coordinates never leave the browser when privacy-maximising mode is enabled.

### Out-of-Scope & Prohibited Uses
- **Not a biometric authentication or user-identification system:** Models must never be used to identify, track, or profile individuals (explicitly forbidden by `CaptchaSolve30k` terms and project privacy invariants).
- **Not a production government portal or WAF replacement:** The target is a mock local portal only; volumetric L3/L4 DDoS mitigation and defeating human-operated CAPTCHA farms are explicit non-goals.
- **Not a sole automated denial authority for assistive-technology users:** Missing mouse telemetry must never be treated as evidence of automation.

### Dataset Availability & Scope Disclosure
- **Used public datasets:** Bournemouth `web_bot_detection` (mouse, Phase 1 & Phase 2), IEEE DataPort `ieee_blog_bots` (mouse external test domain), `delbot_mouse` (mouse supplemental/LOBO), `CaptchaSolve30k` (human-only mouse FPR stress test, never trained on), and Aalto 136M `aalto_keystrokes` (human keyboard data, sampled `997` participants, paired with synthetic keyboard bot generators `K1`–`K4`).
- **Unavailable datasets (no workarounds attempted):** `BeCAPTCHA-Mouse` (unavailable), `CMU Keystroke` (unavailable), `UL-Keystroke` (`repo_only`, no usable dataset).
- **Omitted modality:** Mobile touch (`Phase 8`) was skipped per human decision (`P8-*` marked `SKIPPED`); `touch: null` is reported in all health and metadata payloads.

---

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
   - `majority`: ROC-AUC `0.5000`, Accuracy `0.6340`, Balanced Accuracy `0.5000`
   - `logistic_regression` (scaled): ROC-AUC `0.9902`, Accuracy `0.9596`, Balanced Accuracy `0.9554`
   - `random_forest`: ROC-AUC `0.9997`, Accuracy `0.9939`, Balanced Accuracy `0.9938`
   - `lightgbm` (default): ROC-AUC `0.9997`, Accuracy `0.9930`, Balanced Accuracy `0.9932`
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
  `dt_mode_fraction`) is essential when transferring across phases (lifting
  `P1 -> P2` ROC-AUC from `0.8297` to `0.9785`).
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

### Model summary & privacy guarantees

The keyboard component estimates whether a privacy-safe typing-timing window
resembles the human or synthetic bot classes used in the research pipeline.
The pipeline stores coarse key classes (`letter`, `digit`, `space`, `backspace`,
`punctuation`, `modifier`, `navigation`, `other`) and timing-derived features
only; typed sentences, user input, raw keycodes, and keystroke identifiers are
dropped inside the parser and verified absent via an automated privacy scan
(`results/keyboard/privacy_scan.json`: `997` participant shards, `725,436` key
events, `0` prohibited columns).

Two keyboard models are trained and exported to ONNX:

1. **Primary reference (`backend/models/keyboard-v1/model.onnx`)**: Scaled
   Logistic Regression (`C = 0.1`, selected via 5-fold `StratifiedGroupKFold`
   on training groups, `CV ROC-AUC = 1.0000`) with median imputation and
   standard scaling over 31 timing/rhythm features (`max_abs_diff = 8.04e-08 < 1e-4`
   native-vs-ONNX parity across 500 held-out test windows).
2. **Non-linear comparison (`backend/models/keyboard-lgbm-v1/model.onnx`)**:
   Tuned LightGBM (`n_estimators = 242`, `learning_rate = 0.0806`,
   `num_leaves = 21`, `min_child_samples = 33`, `subsample = 0.8219`,
   `colsample_bytree = 0.8716`).

### Dataset, generators & evaluation results

- **Human source (`aalto_keystrokes`)**: `997` valid participants (`14,941`
  sentence windows, `725,436` key events) streamed from the Aalto 136M
  Keystrokes benchmark (`--max-participants 1000`, `seed = 0`).
- **Synthetic bot generators (`synthetic_keyboard`)**:
  - `K1` (Constant-interval typing with tiny Gaussian jitter, in-distribution);
  - `K2` (Uniform-random dwell/flight intervals, in-distribution);
  - `K3` (**Held-out log-normal human-distribution mimic**, fitted strictly on
    positive dwell/flight intervals of training-split human windows and
    **completely excluded from training**, `4,980` evaluation windows);
  - `K4` (Superhuman copy-paste burst with mid-form pause, in-distribution).

Full evaluation tables with 200-resample group-bootstrap 95% CIs are saved
under `results/keyboard/`:

1. **In-Distribution vs. Overall With Held-Out `K3` (`results/keyboard/evaluation_splits.csv`)**:
   - `logistic_regression` (`in_dist_K1_K2_K4`, `5,778` test windows): **ROC-AUC `1.0000` `[1.0000, 1.0000]`**, PR-AUC `1.0000`, Recall@1%FPR `1.0000`, Balanced Accuracy `0.9989`, Brier `0.0007` (`0.0003` after isotonic calibration).
   - `logistic_regression` (`overall_with_K3`, `10,758` test windows): **ROC-AUC `0.9011` `[0.8880, 0.9138]`**, PR-AUC `0.9611` `[0.9540, 0.9683]`, Recall@1%FPR `0.3982`, Recall@5%FPR `0.5316`.
   - `lightgbm_tuned` (`in_dist_K1_K2_K4`): **ROC-AUC `1.0000` `[1.0000, 1.0000]`**, PR-AUC `1.0000`, Recall@1%FPR `1.0000`, Balanced Accuracy `1.0000`.
   - `lightgbm_tuned` (`overall_with_K3`): **ROC-AUC `0.9969` `[0.9935, 0.9993]`**, PR-AUC `0.9986` `[0.9968, 0.9997]`, Recall@1%FPR `0.9907`, Recall@5%FPR `0.9992`.

2. **Per-Generator Recall & Zero-Shot `K3` Generalization (`results/keyboard/per_generator.csv`)**:
   - `K1`, `K2`, `K4` (in-distribution): Both `logistic_regression` and `lightgbm_tuned` achieve **ROC-AUC `1.0000`** and **Recall@1%FPR `1.0000`**.
   - `K3` (held-out log-normal mimicry): `logistic_regression` achieves **ROC-AUC `0.8415` `[0.8191, 0.8640]`** (`Recall@5%FPR = 0.2492`), whereas **`lightgbm_tuned` achieves ROC-AUC `0.9951` `[0.9884, 0.9988]` and Recall@1%FPR `0.9851` (`0.9988` at 5% FPR)** by capturing higher-order structure absent from independent log-normal draws (`rollover_ratio = 0`, `backspace_ratio = 0`, and missing digram autocorrelation).

3. **Typing-Speed Tercile Fairness (`results/keyboard/speed_terciles.csv`)**:
   - `tercile_1_slow` (`0.51`–`3.36 cps`, `632` humans / `2,954` bots): LR ROC-AUC `0.8813` (human FPR `0.16%` at 1%-FPR threshold), LightGBM ROC-AUC `0.9842`.
   - `tercile_2_medium` (`3.36`–`4.28 cps`, `539` humans / `3,047` bots): LR ROC-AUC `0.9551` (human FPR `0.93%`), LightGBM ROC-AUC `0.9971`.
   - `tercile_3_fast` (`4.28`–`77.18 cps`, `1,604` humans / `1,982` bots): LR ROC-AUC `0.9971` (human FPR `1.37%`), LightGBM ROC-AUC `0.9999`.

## Desktop score fusion

Fusion is evaluated as a pseudo-session experiment (`results/fusion/fusion_comparison.csv`,
`2,462` held-out test pseudo-sessions: `969` human, `1,493` bot): mouse and
keyboard windows from the held-out test partitions are paired within the same
class using a fixed seed (`seed = 42`). These pairings are simulated, not
observations from the same real session, and are explicitly labelled in
`backend/models/fusion-v1/metadata.json` as
`pseudo-session evaluation (simulated pairing)`:

- `mouse_only`: ROC-AUC `1.0000`, PR-AUC `1.0000`, Recall@1%FPR `0.9993`, Balanced Accuracy `0.9974`, Brier `0.0021`
- `keyboard_only`: ROC-AUC `1.0000`, PR-AUC `1.0000`, Recall@1%FPR `1.0000`, Balanced Accuracy `1.0000`, Brier `0.0000`
- `average`: ROC-AUC `1.0000`, PR-AUC `1.0000`, Recall@1%FPR `1.0000`, Balanced Accuracy `1.0000`, Brier `0.0005`
- `noisy_or`: ROC-AUC `1.0000`, PR-AUC `1.0000`, Recall@1%FPR `1.0000`, Balanced Accuracy `0.9985`, Brier `0.0011`
- `stacker` (Logistic Regression on validation scores): **ROC-AUC `1.0000`, PR-AUC `1.0000`, Recall@1%FPR `1.0000`, Balanced Accuracy `1.0000`, Brier `0.0001`**

All four modality-availability regimes (`both_available`, `mouse_only_available`,
`keyboard_only_available`, `neither_available`) are verified in
`results/fusion/modality_availability.csv`: missing modalities are omitted from
the fusion calculation, and absence is never treated as evidence of bot
activity (`treated_as_bot_on_missing = False`).

---

## Prevalence, Threshold Trade-Offs & System Serving Performance

- **Prevalence reweighting (`results/mouse/prevalence_evaluation.csv`, `results/keyboard/prevalence_evaluation.csv`):** Reweighted PR-AUC and precision at 1% and 5% human FPR operating points are reported under `1%`, `5%`, and `20%` bot prevalence per Appendix E.4. At low bot prevalence (`1%`), even a `1%` human FPR bounds raw precision around `~0.50` unless a medium-band step-up challenge absorbs borderline sessions.
- **Threshold trade-off curves (`results/fusion/threshold_tradeoff.csv`, `docs/report_assets/fig6_threshold_tradeoff_curve.png`):** Sweeping challenge-band width (`deny_at_or_above - allow_below` from `0.00` to `0.90`) on held-out cross-phase (`P1 -> P2`), cross-dataset (`Bournemouth -> IEEE`), and keyboard+`K3` splits confirms that widening the challenge band reduces bot pass-through FNR while keeping direct human deny FPR near zero at the cost of a higher step-up challenge rate.
- **Serving latency & throughput (`results/system/scoring_latency.json`, `results/system/system_results.md`):** Over `1,000` alternating multimodal ONNX + rule scoring calls on local Windows CPU hardware, server scoring achieves `p50 = 1.65 ms`, `mean = 3.07 ms`, **`p95 = 15.16 ms`** (well under the `200 ms` target), `p99 = 22.07 ms`, and single-worker throughput of **`325.58 req/s`**.
- **Local feature extraction parity (`results/system/local_features_parity.json`):** TypeScript in-browser extraction (`sendRawTrace=false`) matches Python feature extraction within `1e-9` tolerance across golden mouse and keyboard fixtures, producing identical ONNX risk scores and decisions.
- **End-to-end simulator & load-test verification (`results/system/sim_summary.csv`, `results/system/rule_layer_ablation.csv`, `results/system/loadtest_summary.md`):** Under `protection_mode=passive` (frozen models, never tuned on the simulator), Tiers 1–3 achieve `100.0%` caught/blocked rate (`25/25` each) and Tier 4 (Bezier + randomised typing) achieves `92.0%` (`23/25`). Across `630` load-test requests (`1,155.42 req/s` overall), `0 / 460` malicious requests reached protected `/portal-api/*` routes with `0` `5xx` errors.

---

## Fairness & Accessibility

- **Missing-modality fairness (`P9-12`, `backend/app/scoring.py`):** Sessions with `0` mouse movement events and valid keyboard navigation (including short `<10`-key `Tab`+`Enter`/PIN flows and slow assistive typing with natural variance) are never auto-denied (`MISSING_MOUSE_VALID_KB_MAX_SCORE = 0.50`, capped in the `medium` challenge band), while synthetic constant-interval keyboard bots (`K1`, `identical_interval_fraction >= 0.80`) remain denied.
- **Accessible step-up & WCAG audit (`P9-09`–`P9-13`, `docs/accessibility.md`):** `axe-core` (`4.13.0`) and WCAG 2.1 AA contrast checks report `0` violations across `11` portal and step-up modal states (`results/system/axe_audit.json`), and keyboard-only E2E tests pass for both physical `Space` hold and single-press keyboard verification (`portal/test/keyboard_e2e.test.tsx`).
- **Known accessibility limitations:** Public training datasets contain no documented assistive-technology cohort (head-tracking pointers, switch scanning, or voice dictation), so atypical assistive input may trigger the step-up challenge more frequently; see `docs/accessibility.md` Section 4 for all six documented limitations.

---

## Honesty Checklist (Appendix E.7)

- All model metrics are measured on **public benchmarks**; no live human validation study was performed.
- Keyboard bot classes (`K1`–`K4`) are **synthetic**; no public labelled human-vs-bot web keystroke dataset was available.
- Multimodal fusion is evaluated on **simulated pseudo-sessions** (same-class window pairing), not naturally co-occurring mouse+keyboard sessions.
- Mobile touch modelling (`Phase 8`) was **skipped**; `touch` is `null` in serving metadata.
- Cross-domain performance degrades under domain/sampling shifts (e.g., `CaptchaSolve30k` 240 Hz game tasks and held-out `delbot_mouse:gan`).
- Client-side signals can be spoofed by determined adversaries; passive behavioural scoring **raises attacker cost** and does not guarantee prevention.

---

## Model Update, Monitoring & Governance Policy

1. **No automated online retraining / feedback poisoning guard:** Analyst `fp` / `fn` markings submitted via `POST /admin/feedback` are stored strictly for offline review (`training_policy = "stored_only_never_auto_trained"`) and are **never** automatically ingested into model training.
2. **Retraining gate:** Any model update must:
   - Maintain participant-grouped (human) and generator/run-grouped (bot) splits with `0` group leakage (`ml/tests/test_splits.py`).
   - Report all Appendix E splits (in-distribution, cross-phase, cross-dataset, LOBO / held-out `K3`, and `CaptchaSolve30k` human-FPR stress test) with group-bootstrap 95% CIs via `python scripts/tasks.py eval-all`.
   - Pass ONNX-vs-native parity (`max_abs_diff < 1e-4`), latency (`p95 < 200 ms`), privacy scan (`backend/tests/test_privacy_scan.py`), and claims consistency (`scripts/check_claims.py`) before human sign-off.
3. **Retention & auditability:** Derived feature blobs in SQLite/PostgreSQL expire automatically via `backend/app/retention.py` (default `7` days; assessments `30` days), and model versions are recorded on every assessment row and exposed in `/v1/health` and `/admin/overview`.

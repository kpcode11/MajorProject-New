# BotGuard model card

## Mouse behaviour model

### Model summary

This component estimates whether a browser mouse-trajectory window resembles
the bot or human classes represented in the training data. It is intended as a
passive signal for a mock portal and as one input to a broader risk policy. It
is not an identity, biometric, or employment decision system, and it must not
be used as the sole basis for denying access.

The current reference model is a LightGBM binary classifier. The training
pipeline uses median imputation and a fixed feature order, and can export an
ONNX model for backend inference. The default training seed is `42`. The
exported model is only valid when the consumer supplies the same feature order
and preprocessing described in `metadata.json`.

### Inputs and feature construction

Input events are canonical mouse events containing timestamps and coordinates,
plus session and dataset metadata used only for grouping and evaluation.
Windows are 10 seconds long with a 5-second hop. Exact timestamp/coordinate
duplicates are removed, events are sorted, and windows with fewer than 20
move events are excluded.

Trajectories are segmented at pauses of at least 100 ms and at click boundary
events. Segments must contain at least 8 points and at least 20 pixels of
path. Features cover:

- kinematics: speed, acceleration, jerk, angular velocity, and curvature;
- geometry: path length, displacement, straightness, direction changes,
  bounding-box normalization, and tail reversal;
- timing: duration, sampling intervals, pauses, peak-speed position, and
  acceleration phase;
- click behaviour: dwell and pre-click slowdown.

Feature-group ablations also measure the effect of event-count and timing
shortcuts such as `n_points`, `duration_ms`, `dt_mean`, and
`dt_mode_fraction`.

### Training and evaluation protocol

The pipeline uses deterministic grouped splits. Windows from the same
`split_group` never appear in both training and test partitions. Additional
protocols cover cross-phase, cross-dataset, leave-one-bot-type-out, calibration,
session aggregation, reliability, and group-bootstrap confidence intervals.
Headline metrics include ROC-AUC, PR-AUC, Brier score, confusion counts, and
the recall at a 1% human false-positive operating point.

The repository currently contains only a bounded Bournemouth smoke shard for
the end-to-end feature path. Full feature shards for IEEE Blog Bots,
CaptchaSolve30k, and DELBOT-Mouse were not available when this card was
written. Therefore this card intentionally reports no final model metric:
running the evaluation code without the required data produces an explicit
`insufficient_data` result rather than an invented score.

No claim is made that this model generalizes across datasets, phases, devices,
operating systems, browsers, or real-world bot traffic until those evaluations
are completed.

### Intended use

- Combine the mouse score with other privacy-reviewed signals and an explicit
  risk policy.
- Use calibrated scores to select a step-up action, not to identify a person.
- Monitor false-positive rates separately for humans and for each available
  source or task domain.
- Re-evaluate after changes to the feature schema, model, calibration, or
  source datasets.

### Limitations and risks

- The available sample is small and incomplete, so uncertainty is substantial.
- Bots were created by dataset authors and may not represent current automated
  tooling or adversarial behaviour.
- CaptchaSolve30k is a game-task domain; its human false-positive behaviour
  cannot be assumed to represent ordinary browsing.
- There has been no live human validation in the target portal.
- Dataset, phase, browser, screen-size, sampling, and task differences can
  create spurious signal. In particular, timing and event-count shortcuts can
  make a model separate sources rather than behaviour.
- Mouse trajectories can be missing, noisy, or affected by accessibility
  devices and assistive technology. Missing data must follow the documented
  failure policy rather than silently becoming a bot decision.
- A high in-distribution AUC would not establish safety or generalization.
  Any AUC above 0.99 requires investigation for leakage, dataset fingerprints,
  and shortcut features before it is reported as a success.

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

This is a research-stage component. The implementation includes feature
generation, grouped evaluation, calibration, SHAP explanation, ONNX export,
and parity tests. Production deployment remains blocked on complete source
data, real evaluation results, human review, and the later backend risk-policy
and privacy work.

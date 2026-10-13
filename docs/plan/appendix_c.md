## Appendix C — Config files

### C.1 `backend/config/policy.yaml`

```yaml
# Thresholds are placeholders. Choose final values from validation data
# (Appendix E) and record the choice in docs/decision_log.md.
action_classes:
  low:    { allow_below: 0.50, deny_at_or_above: 0.90 }   # read-only pages
  medium: { allow_below: 0.30, deny_at_or_above: 0.80 }   # login, search
  high:   { allow_below: 0.15, deny_at_or_above: 0.70 }   # OTP request, updates
actions:
  page_view: low
  centre_search: medium
  login: medium
  otp_request: high
  details_update: high
fail_safe:
  redis_down: deny_high_allow_low
  model_error: rules_only
  db_down: continue_and_buffer
band_cutoffs: { low: 0.30, medium: 0.70 }   # for client-visible bands
```

### C.2 `backend/config/rules.yaml`

```yaml
rules:
  R02_WEBDRIVER:        { weight: 0.60, enabled: true }
  R03_UA_PLATFORM_MISMATCH: { weight: 0.30, enabled: true }
  R04_UA_HINTS_MISMATCH:    { weight: 0.30, enabled: true }
  R05_TZ_LANG_MISMATCH:     { weight: 0.10, enabled: true }
  R06_SOFTWARE_RENDERER:    { weight: 0.15, enabled: true }
  R07_ZERO_PLUGINS_DESKTOP: { weight: 0.10, enabled: true }
  R08_VIEWPORT_ANOMALY:     { weight: 0.30, enabled: true }
  R09_TOUCH_INCONSISTENT:   { weight: 0.10, enabled: true }
  R10_NATIVE_FUNCTION_TAMPER: { weight: 0.30, enabled: true }
  R11_UNTRUSTED_EVENTS:     { weight: 0.60, enabled: true }
  R12_TOO_FAST:             { weight: 0.30, enabled: true }
combine: noisy_or            # rule_score = 1 - prod(1 - weight_i for fired rules)
final_score: max_of_model_and_rules   # decision documented and ablated in Phase 10
```

### C.3 `ml/configs/train.yaml` (example)

```yaml
seed: 42
mouse:
  train_datasets: [web_bot_detection]          # add delbot_mouse if obtained
  external_test_datasets: [ieee_blog_bots]
  human_only_stress_test: [captchasolve30k]
  window_s: 10
  hop_s: 5
  features_config: configs/mouse_features.yaml
  include_shortcut_features: false
  cv: { type: grouped_kfold, n_splits: 5 }
  model: { family: lightgbm, search: optuna, n_trials: 50 }
  calibration: { method: isotonic, holdout_fraction: 0.15 }
keyboard:
  datasets: [aalto_keystrokes]
  max_participants: 1000
  synthetic_generators: [K1_constant, K2_uniform, K4_burst]   # K3_mimic held out
  held_out_generator: K3_mimic
  bot_prevalence_eval: [0.01, 0.05, 0.20]
```

---

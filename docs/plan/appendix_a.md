## Appendix A — Feature specifications

All features are computed per **segment** (mouse, touch) or per **typing window** (keyboard), then optionally aggregated per session. Use these exact snake_case names in feature tables. Implement in `ml/src/botguard_ml/features/` and reuse in the backend.

### A.1 Windowing and segmentation

**Unit of classification = window.** Cut each session into windows of `window_s` (default **10 s**) with hop `hop_s` (default **5 s**). Keep windows with at least `min_moves` (default **20**) move events. All windows of a session share the session's `split_group` and label. The SDK sends the most recent window (bounded to 600 points), so training and serving see the same unit. Window-level features are the mean, std and max over the segment features below plus window-level timing statistics.

**Segmentation inside a window:**

- Sort events by `t_ms`; drop exact duplicate timestamps with identical coordinates.
- A new **segment** starts after a pause with no `move` events for `pause_ms` (default **100 ms**) or at a `down`/`up`/`click` boundary.
- Keep segments with at least `min_points` (default **8**) points and path length at least `min_path_px` (default **20 px**).
- Parameters live in `ml/configs/mouse_features.yaml`; changing them requires re-running training.

### A.2 Mouse features (per segment)

Kinematics (using finite differences on `(x, y, t)`; skip zero or negative `dt`):
`speed_mean`, `speed_std`, `speed_max`, `speed_p25`, `speed_p50`, `speed_p75`, `speed_p95`, `acc_mean`, `acc_std`, `acc_max_abs`, `acc_sign_change_rate`, `jerk_mean_abs`, `jerk_std`, `ang_vel_mean_abs`, `ang_vel_std`, `curvature_mean_abs`, `curvature_std`.

Geometry:
`path_length`, `displacement`, `straightness` (displacement / path_length, in [0, 1]), `n_direction_changes` (sign changes of heading beyond a small angle threshold), `direction_change_rate` (per 100 px), `bbox_area_norm` (bounding-box area / screen area when screen size known else NaN), `tail_reversal_ratio` (path length after the point closest to the endpoint / total path length).

Timing:
`duration_ms`, `n_points`, `dt_mean`, `dt_std`, `dt_cv`, `dt_mode_fraction` (share of intervals equal to the most common rounded interval; high values indicate synthetic timing), `pause_count`, `pause_total_ms`, `speed_peak_position` (time of peak speed / duration), `accel_phase_ratio` (time to peak speed / time from peak to end).

Click-related (when events exist): `click_dwell_mean`, `click_dwell_std`, `pre_click_slowdown` (mean speed in the last 100 ms divided by segment mean speed).

**Shortcut-risk features** (`n_points`, `duration_ms`, `dt_mean`, `dt_mode_fraction`): keep in the feature table but make inclusion configurable; always run the ablation with and without them and report both.

**SDK-only integrity features** (not available in datasets, used by rules only): `frac_untrusted_events`, `teleport_count`.

### A.3 Keyboard features (per typing window)

A typing window is a run of at least **10** key events within one field/session; define the rule in config. Text-agnostic only.

`n_keys`, `typing_speed_cps`,
`dwell_mean`, `dwell_std`, `dwell_median`, `dwell_mad`, `dwell_cv`, `dwell_skew`, `dwell_kurt`,
`flight_mean`, `flight_std`, `flight_median`, `flight_mad`, `flight_cv`, `flight_skew`, `flight_kurt`, `flight_min`, `flight_p5`, `flight_p95`,
`dd_mean`, `dd_std` (down-to-down interval),
`rollover_ratio` (fraction of key pairs with negative flight time),
`burst_count`, `burst_len_mean` (bursts split by flights over 300 ms),
`pause_count`, `pause_mean` (flights over 500 ms),
`lag1_autocorr_flight`, `dwell_flight_corr`,
`identical_interval_fraction` (share of intervals equal at 1 ms rounding),
`backspace_ratio`, `paste_events` (SDK/backend only; NaN in datasets that lack it).

### A.4 Touch features (per gesture) — Phase 8

Common: `duration_ms`, `n_points`, `path_length`, `displacement`, `straightness`, `speed_mean`, `speed_std`, `speed_max`, `acc_mean`, `acc_std`, `jerk_mean_abs`, `curvature_mean_abs`, `curvature_std`, `heading_angle`, `start_end_speed_ratio`, `dt_cv`, `dt_mode_fraction`.
Pressure/size (NaN allowed): `pressure_mean`, `pressure_std`, `pressure_min`, `pressure_max`, `pressure_slope`, `size_mean`, `size_std`.
Tap sequences (session): `tap_dwell_mean`, `tap_dwell_std`, `inter_tap_mean`, `inter_tap_cv`, `tap_position_dispersion`.
Stretch (if sensor data used): `acc_xyz_var_during_gesture`, `gyro_var_during_gesture`.

---

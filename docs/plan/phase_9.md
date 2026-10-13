## Phase 9 — Dashboard, privacy, accessibility

**Goal:** Operational visibility, enforced privacy behaviour, and verified accessibility.

### Admin API and dashboard tasks

- [ ] **P9-01** Admin endpoints (API-key protected for the student project; note in docs that production needs SSO/RBAC): `/admin/overview`, `/admin/scores`, `/admin/assessments`, `/admin/assessments/{id}`, `/admin/feedback`, `/admin/sim-results`, `/admin/privacy`.
- [ ] **P9-02** Dashboard (React + Recharts) views:
  1. Overview: requests per minute, allow/challenge/deny split, latency, model versions.
  2. Score distribution histogram with threshold lines.
  3. Session detail: decision, band, rules fired, top contributing features (derived values only, no raw traces).
  4. Simulator results per tier (from `sim_runs.jsonl` ingestion endpoint).
  5. Feedback queue: mark "false positive / false negative" (stored, never auto-used for training).
  6. Privacy panel: retention settings, record counts, last purge.
- [ ] **P9-03** Dashboard component tests and one E2E smoke test.

### Privacy tasks

- [ ] **P9-04** `retention.py`: scheduled purge (cron-like background task or CLI) that deletes stored feature JSON older than the configured TTL (default 7 days) and anonymises or deletes assessments older than the configured long-term TTL; unit-tested with a fake clock.
- [ ] **P9-05** Session identifiers: random per page load, rotating; no cross-day linkage; IP stored only as a coarse bucket (or not at all) in logs.
- [ ] **P9-06** Verify with tests that: no table column or log line contains typed characters, form values, full IPs or persistent device identifiers (scan test over a run of the E2E suite).
- [ ] **P9-07** Write `docs/privacy_impact.md`: for each signal group — purpose, necessity, less-invasive alternative considered, retention. State assumptions about UIDAI/DPDP-style requirements explicitly and that formal compliance needs legal review.
- [ ] **P9-08** **Stretch:** local feature extraction mode in the SDK (`sendRawTrace=false`). Requires a TypeScript port of the mouse/keyboard features and **golden tests**: a set of fixture traces processed by Python and TypeScript must give features within a stated tolerance. Only enable by default if parity tests pass and the model results with local features are reported.

### Accessibility tasks

- [ ] **P9-09** Run axe-core on portal and challenge pages; fix issues.
- [ ] **P9-10** Keyboard-only E2E test: complete login/OTP flow with keyboard only.
- [ ] **P9-11** Screen-reader smoke test notes (manual, `[HUMAN]` with NVDA/VoiceOver if available).
- [ ] **P9-12** Verify the missing-modality policy end-to-end: a session with no mouse events and valid keyboard navigation is not auto-denied.
- [ ] **P9-13** Document known accessibility limitations in `docs/accessibility.md`.

### Optional model upgrades (only if time remains after M3)

- [ ] **P9-14** 1D-CNN or small GRU on raw mouse trajectories (fixed-length resampling, mask for padding); compare against LightGBM with the same splits and cross-dataset protocol; export to ONNX only if it beats the baseline on cross-dataset results and meets latency.
- [ ] **P9-15** Add as an additional model in fusion with metadata.

### Acceptance criteria

- [ ] Retention tests pass.
- [ ] Privacy scan test passes in CI.
- [ ] axe-core run has no critical violations on portal pages.
- [ ] Keyboard-only E2E passes.
- [ ] Dashboard loads data from the running backend.

---

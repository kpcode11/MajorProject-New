# Decision log

This log records project decisions, their rationale, and required human approval.
Do not alter an existing decision; add a dated entry instead.

## Entries

### 2026-10-13 — Phase-1 dataset availability

- **Decision:** Use DELBOT-Mouse as an optional supplemental source; keep
  BeCAPTCHA-Mouse and CMU unavailable, and do not treat the UL-Keystroke
  repository-only entry as an available dataset.
- **Evidence:** The configured dataset root has no BeCAPTCHA-Mouse or CMU
  dataset. The UL-Keystroke configuration has only a placeholder folder and
  `repo_only` status. A shallow clone of DELBOT-Mouse succeeded; its
  `python/dataset.tar.gz` is 4,623,382 bytes compressed and contains 3,551
  trajectories. The archive is streamed directly and only two small samples
  were extracted for inspection.
- **Scope:** DELBOT-Mouse may support supplemental experiments, but the
  primary mouse training source remains Bournemouth. No unavailable source
  workaround or re-identification attempt was made.

### 2026-10-13 — LightGBM ONNX conversion path

- **Decision:** Use `onnxmltools` as the LightGBM-to-ONNX conversion package.
- **Rationale:** It provides the LightGBM-specific converter required by P2-12;
  `skl2onnx` alone does not provide that converter.
- **Scope:** The converter will be validated with an ONNX-vs-native parity test
  before any exported model is used by the backend.

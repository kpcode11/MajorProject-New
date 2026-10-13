# Decision log

This log records project decisions, their rationale, and required human approval.
Do not alter an existing decision; add a dated entry instead.

## Entries

### 2026-10-13 — LightGBM ONNX conversion path

- **Decision:** Use `onnxmltools` as the LightGBM-to-ONNX conversion package.
- **Rationale:** It provides the LightGBM-specific converter required by P2-12;
  `skl2onnx` alone does not provide that converter.
- **Scope:** The converter will be validated with an ONNX-vs-native parity test
  before any exported model is used by the backend.

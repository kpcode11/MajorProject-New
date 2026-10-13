# Handoff

**Updated:** 2026-10-13  |  **By:** Copilot  |  **Branch:** phase-2-mouse-model  |  **Last commit:** ac133fe

## Current task

- ID: P2-13 — mouse model card
- State: ready to start.

## Done in the previous task

- Added LightGBM ONNX export in `ml/src/botguard_ml/export_onnx.py`.
- Added model metadata containing feature order, version, manifest hash,
  imputation strategy, seed, and Git commit.
- Added ONNX Runtime prediction helper.
- Added `scripts/export_mouse_onnx.py`.
- Added `train-mouse --stage onnx`.
- Added native-vs-ONNX parity testing at `1e-4` tolerance.

## Exact next step

- Write the mouse section of `docs/model_card.md`, including limitations,
  dataset constraints, evaluation status, and deployment boundaries.

## Files touched in P2-12

- `ml/src/botguard_ml/export_onnx.py`
- `ml/tests/test_export_onnx.py`
- `scripts/export_mouse_onnx.py`
- `scripts/tasks.py`
- `docs/plan/phase_2.md`
- `PROGRESS.md`

## Validation

- `python scripts/tasks.py test-fast`
- `python scripts/tasks.py lint`
- Focused ONNX parity test

All passed. Windows pytest cache warnings are pre-existing and harmless.

## Known problems / gotchas

- Full feature shards are not currently present, so no production ONNX
  artifact was generated or committed.
- Run `python scripts/tasks.py train-mouse --stage onnx` after feature shards
  exist to generate `backend/models/mouse-v1/model.onnx`.
- The exporter stores median imputation as metadata; consumers must apply the
  same feature order and imputation before ONNX inference.
- Work is on `phase-2-mouse-model`.

## Questions for the human (P2-13)

- None.

"""Export the mouse LightGBM model to ONNX."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from botguard_ml.baselines import _feature_columns, load_feature_rows
from botguard_ml.export_onnx import export_mouse_onnx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/processed/mouse_features"))
    parser.add_argument("--output-dir", type=Path, default=Path("backend/models/mouse-v1"))
    parser.add_argument("--hparams", type=Path, default=Path("results/mouse/hparams.json"))
    parser.add_argument("--version", default="v1")
    parser.add_argument("--manifest-hash", default="unknown")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rows = load_feature_rows(args.input_root)
    hyperparameters: dict[str, Any] | None = None
    if args.hparams.is_file():
        payload = json.loads(args.hparams.read_text(encoding="utf-8"))
        if isinstance(payload.get("best_params"), dict):
            hyperparameters = payload["best_params"]
    metadata = export_mouse_onnx(
        rows,
        args.output_dir,
        feature_columns=_feature_columns(rows),
        version=args.version,
        data_manifest_hash=args.manifest_hash,
        seed=args.seed,
        hyperparameters=hyperparameters,
    )
    print(f"wrote {args.output_dir / 'model.onnx'} ({metadata['version']})")


if __name__ == "__main__":
    main()

"""Export the fixed keyboard Logistic Regression model to ONNX."""

from __future__ import annotations

import argparse
from pathlib import Path

from botguard_ml.baselines import _feature_columns, load_feature_rows
from botguard_ml.export_onnx import export_keyboard_onnx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/keyboard_features/features.parquet"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("backend/models/keyboard-v1"))
    parser.add_argument("--version", default="v1")
    parser.add_argument("--manifest-hash", default="unknown")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rows = load_feature_rows(args.input)
    metadata = export_keyboard_onnx(
        rows,
        args.output_dir,
        feature_columns=_feature_columns(rows),
        version=args.version,
        data_manifest_hash=args.manifest_hash,
        seed=args.seed,
    )
    print(f"wrote {args.output_dir / 'model.onnx'} ({metadata['version']})")


if __name__ == "__main__":
    main()

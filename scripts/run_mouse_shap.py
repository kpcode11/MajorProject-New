"""Generate SHAP summary and per-window top-contributor reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from botguard_ml.baselines import _feature_columns, load_feature_rows
from botguard_ml.explanations import explain_lightgbm
from botguard_ml.splits import grouped_split


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/processed/mouse_features"))
    parser.add_argument("--output-root", type=Path, default=Path("results/mouse"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rows = load_feature_rows(args.input_root)
    metadata = rows.to_dict("records")
    train_indices, test_indices = grouped_split(metadata, test_size=args.test_size, seed=args.seed)
    features = _feature_columns(rows)
    y_train = rows.iloc[train_indices]["label"].to_numpy(dtype=int)
    summary, top = explain_lightgbm(
        rows.iloc[train_indices][features],
        rows.iloc[test_indices][features],
        y_train,
        seed=args.seed,
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_root / "shap_summary.csv", index=False)
    (args.output_root / "shap_top_features.json").write_text(
        json.dumps(top, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote SHAP summary and {len(top)} per-window explanations")


if __name__ == "__main__":
    main()

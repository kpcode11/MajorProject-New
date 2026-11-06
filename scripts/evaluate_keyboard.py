"""Train and evaluate the keyboard baseline with subgroup reports."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from botguard_ml.keyboard_eval import evaluate_keyboard


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/keyboard_features/features.parquet"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results/keyboard/evaluation.csv")
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rows = pq.read_table(args.input).to_pandas()
    k3_path = args.input.parent / "k3_holdout.parquet"
    if k3_path.exists() and "K3" not in set(rows["bot_type"]):
        k3_rows = pq.read_table(k3_path).to_pandas()
        rows = pd.concat([rows, k3_rows], ignore_index=True)
    result = evaluate_keyboard(rows, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote {len(result)} keyboard evaluation rows to {args.output}")


if __name__ == "__main__":
    main()

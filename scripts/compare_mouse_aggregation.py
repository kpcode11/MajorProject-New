"""Compare session-level mouse score aggregation methods."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from botguard_ml.aggregation import compare_aggregators


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/mouse/aggregation.csv"))
    parser.add_argument("--score-column", default="score")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result, selected = compare_aggregators(
        pd.read_parquet(args.input),
        score_column=args.score_column,
        test_size=args.test_size,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"selected {selected}; wrote comparison to {args.output}")


if __name__ == "__main__":
    main()

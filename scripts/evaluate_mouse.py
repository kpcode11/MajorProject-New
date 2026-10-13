"""Evaluate precomputed mouse scores and write a CSV report."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from botguard_ml.eval import evaluate_scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/mouse/evaluation.csv"))
    parser.add_argument(
        "--split",
        choices=("in_distribution", "cross_phase", "cross_dataset", "leave_one_bot_type_out"),
        default="in_distribution",
    )
    parser.add_argument("--test-phase", default="wiki_part2")
    parser.add_argument("--test-dataset")
    parser.add_argument("--test-bot-type")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = evaluate_scores(
        pd.read_parquet(args.input),
        split=args.split,
        test_phase=args.test_phase,
        test_dataset=args.test_dataset,
        test_bot_type=args.test_bot_type,
        n_bootstrap=args.bootstrap,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote evaluation report to {args.output}")


if __name__ == "__main__":
    main()

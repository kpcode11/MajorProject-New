"""Calibrate mouse scores on a separate grouped calibration split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]

from botguard_ml.calibrate import calibrate_scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/mouse/calibration.json"))
    parser.add_argument("--score-column", default="score")
    parser.add_argument("--method", choices=("isotonic", "platt"), default="isotonic")
    parser.add_argument("--calibration-size", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = calibrate_scores(
        pd.read_parquet(args.input),
        score_column=args.score_column,
        method=args.method,
        calibration_size=args.calibration_size,
        test_size=args.test_size,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote calibration report to {args.output}")


if __name__ == "__main__":
    main()

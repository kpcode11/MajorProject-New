"""Train mouse baselines on an identical grouped split."""

from __future__ import annotations

import argparse
from pathlib import Path

from botguard_ml.baselines import load_feature_rows, run_baselines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/processed/mouse_features"))
    parser.add_argument("--output", type=Path, default=Path("results/mouse/baselines.csv"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = run_baselines(load_feature_rows(args.input_root), test_size=args.test_size, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"wrote {len(result)} baseline results to {args.output}")


if __name__ == "__main__":
    main()

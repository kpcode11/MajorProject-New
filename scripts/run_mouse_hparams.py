"""Run grouped Optuna optimisation for the mouse LightGBM model."""

from __future__ import annotations

import argparse
from pathlib import Path

from botguard_ml.hparams import optimise_feature_shards


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/processed/mouse_features"))
    parser.add_argument("--output", type=Path, default=Path("results/mouse/hparams.json"))
    parser.add_argument("--n-trials", type=int, default=30)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = optimise_feature_shards(
        args.input_root,
        args.output,
        test_size=args.test_size,
        n_trials=args.n_trials,
        timeout_seconds=args.timeout_seconds,
        seed=args.seed,
    )
    print(f"wrote {result['n_trials_completed']} trials to {args.output}")


if __name__ == "__main__":
    main()

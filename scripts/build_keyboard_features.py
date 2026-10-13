"""Build human and synthetic keyboard feature shards."""

from __future__ import annotations

import argparse
from pathlib import Path

from botguard_ml.features.keyboard_shards import build_keyboard_feature_shards


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/interim/aalto_keystrokes"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/keyboard_features/features.parquet"))
    parser.add_argument("--bot-prevalence", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    print(
        build_keyboard_feature_shards(
            args.input_root,
            args.output,
            bot_prevalence=args.bot_prevalence,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()

"""Build privacy-safe Aalto keyboard event shards."""

from __future__ import annotations

import argparse
from pathlib import Path

from botguard_ml.loaders.aalto_keystrokes import load


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path(r"C:\Users\KESHAV\Downloads\datasets\Keystrokes"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("data/interim/aalto_keystrokes"))
    parser.add_argument("--max-participants", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    print(
        load(
            args.input_root,
            args.output_root,
            max_participants=args.max_participants,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()

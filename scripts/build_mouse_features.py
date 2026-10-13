"""CLI for creating resumable mouse feature shards."""

from __future__ import annotations

import argparse
from pathlib import Path

from botguard_ml.features.shards import build_feature_shards


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/interim"))
    parser.add_argument("--output-root", type=Path, default=Path("data/processed/mouse_features"))
    parser.add_argument("--max-sessions", type=int, default=None)
    args = parser.parse_args()
    print(build_feature_shards(args.input_root, args.output_root, max_sessions=args.max_sessions))


if __name__ == "__main__":
    main()

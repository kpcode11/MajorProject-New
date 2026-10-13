"""Scan canonical keyboard shards for prohibited content columns."""

from __future__ import annotations

import argparse
from pathlib import Path

from botguard_ml.privacy import scan_keyboard_shards


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("data/interim/aalto_keystrokes"),
    )
    args = parser.parse_args()
    print(scan_keyboard_shards(args.input_root))


if __name__ == "__main__":
    main()

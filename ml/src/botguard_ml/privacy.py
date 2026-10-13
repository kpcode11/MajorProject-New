"""Privacy checks for canonical keyboard event shards."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]

PROHIBITED_COLUMNS = {
    "sentence",
    "user_input",
    "letter",
    "keycode",
    "keystroke_id",
    "typed_text",
    "text",
}


def scan_keyboard_shards(input_root: Path) -> dict[str, int]:
    """Scan every Parquet shard without loading the complete dataset."""
    paths = sorted(input_root.glob("*.parquet"))
    if not paths:
        raise ValueError(f"no keyboard Parquet shards found under {input_root}")
    scanned_shards = 0
    scanned_rows = 0
    for path in paths:
        parquet = pq.ParquetFile(path)
        columns = {name.lower() for name in parquet.schema.names}
        prohibited = sorted(columns.intersection(PROHIBITED_COLUMNS))
        if prohibited:
            raise ValueError(f"{path}: prohibited columns: {', '.join(prohibited)}")
        for batch in parquet.iter_batches():
            scanned_rows += batch.num_rows
        scanned_shards += 1
    return {"shards": scanned_shards, "rows": scanned_rows}

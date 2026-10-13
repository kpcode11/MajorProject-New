"""Streaming loader for the human-only CaptchaSolve30k dataset."""

from __future__ import annotations

import argparse
import base64
import json
import random
import struct
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

DATASET = "captchasolve30k"
SPLITS = ("train", "validation", "test")
SAMPLE_SIZE = 9


def decode_input_stream(value: str) -> list[tuple[float, float, int]]:
    """Decode little-endian float32 x/y and one button byte per sample."""
    try:
        payload = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("inputStream is not valid base64") from exc
    if len(payload) % SAMPLE_SIZE:
        raise ValueError("inputStream length is not divisible by 9 bytes")
    return [
        struct.unpack_from("<ffB", payload, offset)
        for offset in range(0, len(payload), SAMPLE_SIZE)
    ]


def _tick_events(record: dict[str, Any]) -> list[tuple[float, float, int]]:
    """Use tickInputs when a record has no raw input stream."""
    samples: list[tuple[float, float, int]] = []
    for item in record.get("tickInputs", []):
        if not isinstance(item, dict):
            raise ValueError("tickInputs entries must be objects")
        samples.append((float(item["x"]), float(item["y"]), int(bool(item["isDown"]))))
    return samples


def canonical_events(
    record: dict[str, Any], *, session_id: str, source: Path
) -> list[dict[str, Any]]:
    """Convert one CaptchaSolve30k session into canonical mouse events."""
    game_type = record.get("gameType")
    if not isinstance(game_type, str) or not game_type:
        raise ValueError(f"{source}: gameType is required")
    touchscreen = bool(record.get("touchscreen", False))
    tick_inputs = record.get("tickInputs")
    raw_stream = record.get("inputStream")
    tick_based = isinstance(tick_inputs, list) and bool(tick_inputs)
    samples = (
        _tick_events(record)
        if tick_based
        else decode_input_stream(raw_stream)
        if isinstance(raw_stream, str) and raw_stream
        else []
    )
    sample_interval_ms = 1000.0 / 240.0 if tick_based else 1.0
    events: list[dict[str, Any]] = []
    for index, (x, y, button) in enumerate(samples):
        events.append(
            {
                "dataset": DATASET,
                "session_id": session_id,
                "subject_id": session_id,
                "label": 0,
                "bot_type": "human",
                "t_ms": index * sample_interval_ms,
                "x": x,
                "y": y,
                "coord_space": "grid200",
                "event": "click" if button else "move",
                "screen_w": float("nan"),
                "screen_h": float("nan"),
                "domain": "game_task",
                "touchscreen": touchscreen,
                "game_type": game_type,
            }
        )
    return events


def _records(root: Path) -> Iterator[tuple[Path, int, dict[str, Any]]]:
    """Yield JSONL records with their byte offsets, one record at a time."""
    for split in SPLITS:
        path = root / f"{split}.jsonl"
        if not path.is_file():
            continue
        with path.open("rb") as handle:
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError(f"{path}: every JSONL line must be an object")
                yield path, offset, record


def _selected_offsets(root: Path, max_sessions: int | None, seed: int) -> list[tuple[Path, int]]:
    """Select a deterministic, game-type-stratified set using only offsets."""
    all_offsets: dict[str, list[tuple[Path, int]]] = {}
    for path, offset, record in _records(root):
        game_type = record.get("gameType")
        if not isinstance(game_type, str) or not game_type:
            raise ValueError(f"{path}: gameType is required")
        all_offsets.setdefault(game_type, []).append((path, offset))
    total = sum(len(items) for items in all_offsets.values())
    if max_sessions is None or max_sessions >= total:
        selected = [item for items in all_offsets.values() for item in items]
    else:
        rng = random.Random(seed)
        game_types = sorted(all_offsets)
        base, remainder = divmod(max_sessions, len(game_types))
        selected = []
        for position, game_type in enumerate(game_types):
            count = min(len(all_offsets[game_type]), base + (position < remainder))
            selected.extend(rng.sample(all_offsets[game_type], count))
    return sorted(selected, key=lambda item: (str(item[0]), item[1]))


def session_records(
    root: Path, max_sessions: int = 3000, seed: int = 0
) -> Iterator[list[dict[str, Any]]]:
    """Yield a seeded, game-type-stratified sample of canonical sessions."""
    for path, offset in _selected_offsets(root, max_sessions, seed):
        with path.open("rb") as handle:
            handle.seek(offset)
            record = json.loads(handle.readline())
        session_id = f"{path.stem}/{record.get('index', offset)}"
        events = canonical_events(record, session_id=session_id, source=path)
        if events:
            yield events


def load(root: Path, output: Path, max_sessions: int = 3000, seed: int = 0) -> int:
    """Write one canonical Parquet shard from selected JSONL sessions."""
    event_count = 0
    writer: pq.ParquetWriter | None = None
    output.parent.mkdir(parents=True, exist_ok=True)
    for batch in session_records(root, max_sessions, seed):
        table = pa.Table.from_pylist(batch)
        if writer is None:
            writer = pq.ParquetWriter(output, table.schema)
        writer.write_table(table)
        event_count += len(batch)
    if writer is None:
        raise ValueError("no events were produced")
    writer.close()
    return event_count


def main() -> None:
    """Run the loader with bounded, seeded sampling."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-sessions", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    print(f"wrote {load(args.source, args.output, args.max_sessions, args.seed)} events")


if __name__ == "__main__":
    main()

"""Streaming loader for the observed Bournemouth Web Bot Detection Dataset."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

DATASET = "web_bot_detection"
PAIR_PATTERN = re.compile(r"\[\s*(?:m\()?\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)?\s*\]")


def parse_pairs(value: str) -> list[tuple[float, float]]:
    """Parse the dataset's concatenated ``[x,y]`` coordinate representation."""
    return [(float(x), float(y)) for x, y in PAIR_PATTERN.findall(value)]


def parse_times(value: str) -> list[float]:
    """Parse the observed comma-separated movement timestamps into milliseconds."""
    return [float(item) for item in value.split(",") if item.strip()]


def canonical_events(
    record: dict[str, Any], *, label: int, bot_type: str, domain: str
) -> list[dict[str, Any]]:
    """Convert one source session's aligned movement series into canonical move events."""
    points = parse_pairs(str(record.get("mousemove_total_behaviour", "")))
    times = parse_times(str(record.get("mousemove_times", "")))
    count = min(len(points), len(times))
    if count == 0:
        return []
    start = times[0]
    session_id = str(record["session_id"])
    subject_id = session_id if label == 0 else f"{bot_type}:{session_id}"
    return [
        {
            "dataset": DATASET,
            "session_id": session_id,
            "subject_id": subject_id,
            "label": label,
            "bot_type": bot_type,
            "t_ms": times[index] - start,
            "x": points[index][0],
            "y": points[index][1],
            "coord_space": "pixels",
            "event": "move",
            "screen_w": float("nan"),
            "screen_h": float("nan"),
            "domain": domain,
            "touchscreen": False,
        }
        for index in range(count)
    ]


def read_annotations(path: Path) -> dict[str, str]:
    """Read a small observed ``session_id label`` annotation file."""
    labels: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            labels[parts[0]] = parts[1].lower()
    return labels


def concatenated_objects(path: Path, chunk_size: int = 64 * 1024) -> Iterator[dict[str, Any]]:
    """Yield concatenated MongoDB-export JSON objects without loading a file whole."""
    decoder = json.JSONDecoder()
    buffer = ""
    with path.open(encoding="utf-8") as handle:
        while chunk := handle.read(chunk_size):
            buffer += chunk
            position = 0
            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if position >= len(buffer):
                    buffer = ""
                    break
                try:
                    value, end = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError:
                    buffer = buffer[position:]
                    break
                if not isinstance(value, dict):
                    raise ValueError(f"expected object in {path}")
                yield value
                position = end
    if buffer.strip():
        raise ValueError(f"incomplete JSON object in {path}")


def phase1_records(root: Path, max_sessions: int | None) -> Iterator[list[dict[str, Any]]]:
    """Stream phase-1 session files, deduplicating human sessions across label groups."""
    phase = root / "phase1"
    seen_humans: set[str] = set()
    emitted = 0
    for group in ("humans_and_moderate_bots", "humans_and_advanced_bots"):
        label_map: dict[str, str] = {}
        for split in ("train", "test"):
            label_map.update(read_annotations(phase / "annotations" / group / split))
        for session_dir in (phase / "data" / "mouse_movements" / group).iterdir():
            if max_sessions is not None and emitted >= max_sessions:
                return
            source = session_dir / "mouse_movements.json"
            if not source.is_file():
                continue
            record = json.loads(source.read_text(encoding="utf-8"))
            session_id = str(record["session_id"])
            label_name = label_map.get(session_id)
            if label_name is None:
                continue
            if label_name == "human":
                if session_id in seen_humans:
                    continue
                seen_humans.add(session_id)
            events = canonical_events(
                record,
                label=0 if label_name == "human" else 1,
                bot_type=label_name,
                domain="wiki_part1",
            )
            if events:
                emitted += 1
                yield events


def phase2_records(root: Path, max_sessions: int | None) -> Iterator[list[dict[str, Any]]]:
    """Stream phase-2 MongoDB exports, assigning labels from their observed filenames."""
    files = (
        ("humans", "mouse_movements_humans.json", "human", 0),
        ("bots", "mouse_movements_moderate_bots.json", "moderate", 1),
        ("bots", "mouse_movements_advanced_bots.json", "advanced", 1),
    )
    emitted = 0
    for directory, filename, bot_type, label in files:
        path = root / "phase2" / "data" / "mouse_movements" / directory / filename
        for record in concatenated_objects(path):
            if max_sessions is not None and emitted >= max_sessions:
                return
            events = canonical_events(record, label=label, bot_type=bot_type, domain="wiki_part2")
            if events:
                emitted += 1
                yield events


def load(root: Path, output: Path, max_sessions: int | None = None) -> int:
    """Write one canonical Parquet shard from streamed phase-1 and phase-2 sessions."""
    event_count = 0
    session_count = 0
    writer: pq.ParquetWriter | None = None
    output.parent.mkdir(parents=True, exist_ok=True)
    for producer in (phase1_records, phase2_records):
        remaining = None if max_sessions is None else max_sessions - session_count
        if remaining == 0:
            break
        for batch in producer(root, remaining):
            table = pa.Table.from_pylist(batch)
            if writer is None:
                writer = pq.ParquetWriter(output, table.schema)
            writer.write_table(table)
            event_count += len(batch)
            session_count += 1
            if max_sessions is not None and session_count >= max_sessions:
                break
    if writer is None:
        raise ValueError("no events were produced")
    writer.close()
    return event_count


def main() -> None:
    """Run the loader with an explicit source root and bounded session sample."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-sessions", type=int, default=None)
    args = parser.parse_args()
    print(f"wrote {load(args.source, args.output, args.max_sessions)} events")


if __name__ == "__main__":
    main()

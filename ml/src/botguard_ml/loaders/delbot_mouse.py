"""Streaming loader for the optional DELBOT-Mouse trajectory archive."""

from __future__ import annotations

import argparse
import math
import tarfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

DATASET = "delbot_mouse"
EVENT_TYPES = {
    "Move": ("move", False),
    "MoveTouch": ("move", True),
    "Pressed": ("down", False),
    "PressedTouch": ("down", True),
    "Released": ("up", False),
    "ReleasedTouch": ("up", True),
}


def _number(value: str, *, field: str, source: str) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"{source}: invalid {field}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{source}: invalid {field}")
    return result


def canonical_events(lines: Iterator[str], *, session_id: str, source: str) -> list[dict[str, Any]]:
    """Convert one DELBOT text trajectory into canonical mouse events."""
    header = next(lines, "").strip()
    if not header.startswith("resolution:"):
        raise ValueError(f"{source}: missing resolution header")
    try:
        screen_w, screen_h = (float(value) for value in header.split(":", 1)[1].split(","))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{source}: invalid resolution header") from exc

    parts = source.replace("\\", "/").split("/")
    category = next((part for part in parts if part.startswith("circles_")), "")
    label = 0 if "human" in category else 1
    bot_type = "human" if label == 0 else category.removeprefix("circles_bot_")
    subject_id = session_id if label == 0 else f"{bot_type}:{session_id}"

    rows: list[tuple[float, dict[str, Any]]] = []
    for line_number, line in enumerate(lines, start=2):
        fields = line.strip().split(",")
        if len(fields) < 4:
            raise ValueError(f"{source}:{line_number}: expected four fields")
        event_type = fields[1]
        if event_type not in EVENT_TYPES:
            raise ValueError(f"{source}:{line_number}: unsupported event {event_type!r}")
        event, touchscreen = EVENT_TYPES[event_type]
        timestamp = _number(fields[0], field="timestamp", source=source)
        row = {
            "dataset": DATASET,
            "session_id": session_id,
            "subject_id": subject_id,
            "label": label,
            "bot_type": bot_type,
            "t_ms": timestamp,
            "x": _number(fields[2], field="x", source=source),
            "y": _number(fields[3], field="y", source=source),
            "coord_space": "pixels",
            "event": event,
            "screen_w": screen_w,
            "screen_h": screen_h,
            "domain": "circle_task",
            "touchscreen": touchscreen,
        }
        rows.append((timestamp, row))
    if not rows:
        return []
    start = rows[0][0]
    for timestamp, row in rows:
        row["t_ms"] = timestamp - start
    return [row for _, row in rows]


def session_records(
    archive: Path, max_sessions: int | None = None
) -> Iterator[list[dict[str, Any]]]:
    """Yield canonical sessions from text members without extracting the archive."""
    emitted = 0
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".txt"):
                continue
            if max_sessions is not None and emitted >= max_sessions:
                return
            handle = tar.extractfile(member)
            if handle is None:
                continue
            with handle:
                text = (line.decode("utf-8", "replace") for line in handle)
                session_id = Path(member.name).stem
                events = canonical_events(text, session_id=session_id, source=member.name)
            if events:
                emitted += 1
                yield events


def load(archive: Path, output: Path, max_sessions: int | None = None) -> int:
    """Write one canonical Parquet shard from the DELBOT archive."""
    event_count = 0
    writer: pq.ParquetWriter | None = None
    output.parent.mkdir(parents=True, exist_ok=True)
    for batch in session_records(archive, max_sessions):
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
    """Run the loader with an optional session limit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-sessions", type=int, default=None)
    args = parser.parse_args()
    print(f"wrote {load(args.source, args.output, args.max_sessions)} events")


if __name__ == "__main__":
    main()

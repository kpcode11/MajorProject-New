"""Streaming loader for the IEEE blog-platform human-vs-bot dataset."""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

DATASET = "ieee_blog_bots"
BOT_TYPES = {"naive", "humanish", "mimic", "fallible"}


def _number(value: Any, *, field: str, source: Path) -> float:
    """Convert a required numeric source value and reject malformed records."""
    if isinstance(value, bool):
        raise ValueError(f"{source}: {field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source}: {field} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{source}: {field} must be finite")
    return result


def _event(
    *,
    session_id: str,
    subject_id: str,
    label: int,
    bot_type: str,
    event_type: str,
    item: dict[str, Any],
    start_ms: float,
    source: Path,
) -> dict[str, Any]:
    timestamp = _number(item.get("timestamp"), field="timestamp", source=source)
    return {
        "dataset": DATASET,
        "session_id": session_id,
        "subject_id": subject_id,
        "label": label,
        "bot_type": bot_type,
        "t_ms": timestamp - start_ms,
        "x": _number(item["x"], field="x", source=source) if "x" in item else float("nan"),
        "y": _number(item["y"], field="y", source=source) if "y" in item else float("nan"),
        "coord_space": "pixels",
        "event": event_type,
        "screen_w": float("nan"),
        "screen_h": float("nan"),
        "domain": "blog_platform",
        "touchscreen": False,
    }


def canonical_events(
    record: dict[str, Any], *, session_id: str, source: Path
) -> list[dict[str, Any]]:
    """Convert one observed IEEE JSON session to canonical mouse events."""
    bot_info = record.get("bot_info")
    if bot_info is None:
        label, bot_type = 0, "human"
    else:
        raw_name = str(bot_info.get("bot_name", "")).removesuffix("Bot").lower()
        if raw_name not in BOT_TYPES:
            raise ValueError(f"{source}: unsupported bot type {raw_name!r}")
        label, bot_type = 1, raw_name

    timestamps = record.get("timestamps") or {}
    if "start" in timestamps:
        start_ms = _number(timestamps["start"], field="timestamps.start", source=source)
    else:
        all_timestamps = [
            item.get("timestamp")
            for key in ("mouse_movements", "clicks", "scrolls")
            for item in record.get(key, [])
            if isinstance(item, dict) and "timestamp" in item
        ]
        if not all_timestamps:
            return []
        start_ms = min(_number(value, field="timestamp", source=source) for value in all_timestamps)

    subject_id = session_id if label == 0 else f"{bot_type}:{session_id}"
    events: list[dict[str, Any]] = []
    for key, event_type in (
        ("mouse_movements", "move"),
        ("clicks", "click"),
        ("scrolls", "scroll"),
    ):
        for item in record.get(key, []):
            if not isinstance(item, dict):
                raise ValueError(f"{source}: {key} entries must be objects")
            events.append(
                _event(
                    session_id=session_id,
                    subject_id=subject_id,
                    label=label,
                    bot_type=bot_type,
                    event_type=event_type,
                    item=item,
                    start_ms=start_ms,
                    source=source,
                )
            )
    events.sort(key=lambda item: item["t_ms"])
    return events


def session_records(root: Path, max_sessions: int | None = None) -> Iterator[list[dict[str, Any]]]:
    """Yield canonical events from train/test JSON files without loading the dataset."""
    emitted = 0
    for split in ("train", "test"):
        for source in sorted((root / split).glob("*.json")):
            if max_sessions is not None and emitted >= max_sessions:
                return
            record = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise ValueError(f"{source}: expected a JSON object")
            session_id = f"{split}/{source.stem}"
            events = canonical_events(record, session_id=session_id, source=source)
            if events:
                emitted += 1
                yield events


def load(root: Path, output: Path, max_sessions: int | None = None) -> int:
    """Write one canonical Parquet shard from streamed IEEE sessions."""
    event_count = 0
    writer: pq.ParquetWriter | None = None
    output.parent.mkdir(parents=True, exist_ok=True)
    for batch in session_records(root, max_sessions):
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
    """Run the loader with an explicit source root and bounded session sample."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-sessions", type=int, default=None)
    args = parser.parse_args()
    print(f"wrote {load(args.source, args.output, args.max_sessions)} events")


if __name__ == "__main__":
    main()

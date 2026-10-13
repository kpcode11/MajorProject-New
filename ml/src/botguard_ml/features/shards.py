"""Build resumable mouse feature shards from canonical Parquet events."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from botguard_ml.features.mouse import SEGMENT_FEATURE_NAMES, extract_window_features
from botguard_ml.features.windowing import window_events

REQUIRED_METADATA = (
    "dataset",
    "domain",
    "session_id",
    "subject_id",
    "split_group",
    "label",
    "bot_type",
)
DEFAULT_COLUMNS = [
    *REQUIRED_METADATA[:4],
    "label",
    "bot_type",
    "t_ms",
    "x",
    "y",
    "event",
    "screen_w",
    "screen_h",
]


def _safe_name(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem)


def _split_group(dataset: str, session_id: str, domain: str) -> str:
    return f"{dataset}:{domain}:{session_id}"


def _sessions(path: Path) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Yield sessions from a canonical Parquet file without loading other files."""
    parquet = pq.ParquetFile(path)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for batch in parquet.iter_batches(batch_size=4096, columns=DEFAULT_COLUMNS):
        data = batch.to_pydict()
        for index, session_value in enumerate(data["session_id"]):
            session_id = str(session_value)
            event = {
                column: data[column][index]
                for column in DEFAULT_COLUMNS
                if column not in REQUIRED_METADATA
            }
            event.update(
                {
                    "dataset": str(data["dataset"][index]),
                    "domain": str(data["domain"][index]),
                    "session_id": session_id,
                    "subject_id": str(data["subject_id"][index]),
                    "label": int(data["label"][index]),
                    "bot_type": str(data["bot_type"][index]),
                }
            )
            grouped[session_id].append(event)
    for session_id in sorted(grouped):
        yield session_id, grouped[session_id]


def _feature_row(
    window: list[dict[str, Any]], *, session_id: str, session_index: int, window_index: int
) -> dict[str, Any]:
    first = window[0]
    dataset = str(first["dataset"])
    domain = str(first["domain"])
    features = extract_window_features(window)
    row: dict[str, Any] = {name: float(value) for name, value in features.items()}
    row.update(
        {
            "dataset": dataset,
            "domain": domain,
            "session_id": session_id,
            "subject_id": str(first["subject_id"]),
            "split_group": _split_group(dataset, session_id, domain),
            "label": int(first["label"]),
            "bot_type": str(first["bot_type"]),
            "window_index": window_index,
            "session_index": session_index,
        }
    )
    return row


def build_feature_shard(
    source: Path,
    output: Path,
    *,
    max_sessions: int | None = None,
) -> tuple[int, int]:
    """Write one feature Parquet shard and return ``(sessions, windows)``."""
    rows: list[dict[str, Any]] = []
    sessions = 0
    for session_id, events in _sessions(source):
        if max_sessions is not None and sessions >= max_sessions:
            break
        windows = window_events(events)
        rows.extend(
            _feature_row(
                window,
                session_id=session_id,
                session_index=sessions,
                window_index=window_index,
            )
            for window_index, window in enumerate(windows)
        )
        sessions += 1
    if not rows:
        raise ValueError(f"no qualifying windows found in {source}")
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), output)
    return sessions, len(rows)


def schema_payload() -> dict[str, Any]:
    """Return the stable feature-shard schema description."""
    return {
        "version": 1,
        "metadata_columns": [*REQUIRED_METADATA, "window_index", "session_index"],
        "feature_columns": [
            f"{name}_{stat}" for name in SEGMENT_FEATURE_NAMES for stat in ("mean", "std", "max")
        ]
        + [
            "window_duration_ms",
            "window_n_points",
            "window_dt_mean",
            "window_dt_std",
            "window_dt_cv",
            "window_dt_mode_fraction",
            "window_pause_count",
            "window_pause_total_ms",
            "n_segments",
        ],
    }


def build_feature_shards(
    input_root: Path,
    output_root: Path,
    *,
    max_sessions: int | None = None,
) -> dict[str, Any]:
    """Build all canonical feature shards, skipping completed source shards."""
    if max_sessions is not None and max_sessions < 1:
        raise ValueError("max_sessions must be positive")
    sources = sorted(input_root.rglob("*.parquet"))
    if not sources:
        raise ValueError(f"no canonical Parquet files found under {input_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    schema_path = output_root / "mouse_features.schema.json"
    schema_path.write_text(json.dumps(schema_payload(), indent=2) + "\n", encoding="utf-8")
    state_path = output_root / "_state.json"
    state: dict[str, Any] = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path.is_file()
        else {"version": 1, "completed": {}}
    )
    completed: dict[str, Any] = state.setdefault("completed", {})
    built = 0
    skipped = 0
    for source in sources:
        key = str(source.relative_to(input_root))
        relative_source = source.relative_to(input_root)
        output_name = f"{_safe_name(relative_source.with_suffix(''))}.parquet"
        output = output_root / output_name
        if key in completed and output.is_file():
            skipped += 1
            continue
        sessions, windows = build_feature_shard(source, output, max_sessions=max_sessions)
        completed[key] = {"output": output.name, "sessions": sessions, "windows": windows}
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        built += 1
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return {"sources": len(sources), "built": built, "skipped": skipped}

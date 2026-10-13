"""Tests for resumable mouse feature shard creation."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from botguard_ml.features.shards import build_feature_shard, build_feature_shards


def _write_events(path: Path) -> None:
    rows = []
    for session_id, offset in (("s1", 0.0), ("s2", 1000.0)):
        for index in range(25):
            rows.append(
                {
                    "dataset": "fixture",
                    "session_id": session_id,
                    "subject_id": session_id,
                    "label": 0,
                    "bot_type": "human",
                    "t_ms": offset + index * 100.0,
                    "x": float(index * 5),
                    "y": 0.0,
                    "coord_space": "pixels",
                    "event": "move",
                    "screen_w": 1000.0,
                    "screen_h": 800.0,
                    "domain": "test",
                    "touchscreen": False,
                }
            )
    pq.write_table(pa.Table.from_pylist(rows), path)


def test_build_feature_shard_contains_metadata_and_features(tmp_path: Path) -> None:
    source = tmp_path / "events.parquet"
    output = tmp_path / "features.parquet"
    _write_events(source)

    sessions, windows = build_feature_shard(source, output)

    assert sessions == 2
    assert windows == 2
    table = pq.read_table(output)
    metadata = {"dataset", "domain", "session_id", "subject_id", "split_group", "label", "bot_type"}
    assert metadata <= set(table.column_names)
    assert "straightness_mean" in table.column_names
    assert table.column("split_group").to_pylist() == ["fixture:test:s1", "fixture:test:s2"]


def test_build_feature_shards_skips_completed_sources(tmp_path: Path) -> None:
    input_root = tmp_path / "interim" / "fixture"
    output_root = tmp_path / "processed"
    input_root.mkdir(parents=True)
    _write_events(input_root / "events.parquet")

    first = build_feature_shards(tmp_path / "interim", output_root)
    second = build_feature_shards(tmp_path / "interim", output_root)

    assert first == {"sources": 1, "built": 1, "skipped": 0}
    assert second == {"sources": 1, "built": 0, "skipped": 1}
    assert json.loads((output_root / "mouse_features.schema.json").read_text())["version"] == 1
    assert (output_root / "_state.json").is_file()

"""Tests for keyboard feature shard construction."""

from __future__ import annotations

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from botguard_ml.features.keyboard_shards import build_keyboard_feature_shards


def test_feature_shards_include_humans_and_hold_out_k3(tmp_path) -> None:
    events = []
    for session_index in range(2):
        for key_index in range(10):
            events.append(
                {
                    "dataset": "aalto_keystrokes",
                    "domain": "typing_test",
                    "session_id": f"p{session_index}/s",
                    "subject_id": f"p{session_index}",
                    "split_group": f"p{session_index}",
                    "label": 0,
                    "bot_type": "human",
                    "down_ms": key_index * 120.0,
                    "up_ms": key_index * 120.0 + 40.0,
                    "key_class": "letter",
                }
            )
    source = tmp_path / "events.parquet"
    output = tmp_path / "features.parquet"
    pq.write_table(pa.Table.from_pylist(events), source)

    result = build_keyboard_feature_shards(tmp_path, output, bot_prevalence=1.0, seed=4)
    table = pq.read_table(output)

    assert result == {"human_windows": 2, "bot_windows": 2}
    assert set(table.column("bot_type").to_pylist()) == {"human", "K1", "K2"}
    assert "K3" not in table.column("bot_type").to_pylist()
    assert "sentence" not in table.column_names

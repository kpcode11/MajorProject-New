"""Focused tests for the canonical mouse audit helper."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from data_audit import audit_file


def test_audits_counts_windows_and_missing_values(tmp_path: Path) -> None:
    rows = []
    for index in range(20):
        rows.append(
            {
                "dataset": "fixture",
                "session_id": "s1",
                "subject_id": "human-1",
                "label": 0,
                "bot_type": "human",
                "t_ms": float(index * 100),
                "x": float(index),
                "y": 2.0,
                "coord_space": "pixels",
                "event": "move",
                "screen_w": float("nan"),
                "screen_h": float("nan"),
                "domain": "test",
                "touchscreen": False,
            }
        )
    rows.append({**rows[0], "session_id": "s2", "subject_id": "bot-1", "label": 1, "bot_type": "naive", "event": "click"})
    path = tmp_path / "fixture.parquet"
    pq.write_table(pa.Table.from_pylist(rows), path)

    report = audit_file(path)

    assert report["rows"] == 21
    assert report["sessions"] == 2
    assert report["counts"]["label"] == {"0": 20, "1": 1}
    assert report["windows"]["count"] == 1
    assert report["missing_values"]["screen_w"]["rate"] == 1.0

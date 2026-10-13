"""Tests for keyboard shard privacy scanning."""

from __future__ import annotations

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from botguard_ml.privacy import scan_keyboard_shards


def test_privacy_scan_accepts_canonical_shard(tmp_path) -> None:
    pq.write_table(
        pa.table({"key_class": ["letter"], "down_ms": [1.0]}),
        tmp_path / "safe.parquet",
    )

    assert scan_keyboard_shards(tmp_path) == {"shards": 1, "rows": 1}


def test_privacy_scan_rejects_typed_content_column(tmp_path) -> None:
    pq.write_table(
        pa.table({"sentence": ["secret"], "key_class": ["letter"]}),
        tmp_path / "unsafe.parquet",
    )

    with pytest.raises(ValueError, match="prohibited columns"):
        scan_keyboard_shards(tmp_path)

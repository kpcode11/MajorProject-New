"""Tests for the streaming Aalto keyboard loader."""

from __future__ import annotations

import json

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from botguard_ml.loaders.aalto_keystrokes import load


def test_loader_streams_sentence_windows_without_sensitive_columns(tmp_path) -> None:
    source = tmp_path / "Keystrokes" / "files"
    source.mkdir(parents=True)
    path = source / "123_keystrokes.txt"
    header = (
        "PARTICIPANT_ID\tTEST_SECTION_ID\tSENTENCE\tUSER_INPUT\tKEYSTROKE_ID\t"
        "PRESS_TIME\tRELEASE_TIME\tLETTER\tKEYCODE\n"
    )
    rows = "".join(
        f"123\tsection\tsecret\tsecret\t{i}\t{1000 + i * 10}\t{1005 + i * 10}\t"
        f"{'A' if i % 2 else 'SHIFT'}\t{65 if i % 2 else 16}\n"
        for i in range(10)
    )
    path.write_text(header + rows, encoding="utf-8")

    stats = load(tmp_path / "Keystrokes", tmp_path / "out", max_participants=1)

    assert stats["windows"] == 1
    table = pq.read_table(tmp_path / "out" / "123.parquet")
    assert set(table.column_names) == {
        "dataset",
        "session_id",
        "subject_id",
        "split_group",
        "label",
        "bot_type",
        "down_ms",
        "up_ms",
        "key_class",
        "domain",
    }
    assert "secret" not in table.to_pandas().to_string()
    assert json.loads((tmp_path / "out" / "_state.json").read_text())["completed"] == ["123"]

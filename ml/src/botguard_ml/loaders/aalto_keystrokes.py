"""Streaming, privacy-safe loader for the Aalto 136M Keystrokes dataset."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

DATASET = "aalto_keystrokes"
MIN_EVENTS = 10
REQUIRED_COLUMNS = {
    "PARTICIPANT_ID",
    "TEST_SECTION_ID",
    "PRESS_TIME",
    "RELEASE_TIME",
    "LETTER",
    "KEYCODE",
}


def key_class(letter: str | None, keycode: str | None) -> str:
    """Map a source key identity to a coarse class without retaining identity."""
    value = (letter or "").strip().upper()
    try:
        code = int(keycode or "")
    except (TypeError, ValueError):
        code = -1
    if value in {"SHIFT", "CTRL", "CONTROL", "ALT", "META", "CAPSLOCK"} or code in {
        16,
        17,
        18,
        20,
        91,
        92,
    }:
        return "modifier"
    if value in {"SPACE", "SPACEBAR"} or code == 32:
        return "whitespace"
    if value in {"BACKSPACE", "DELETE", "DEL", "TAB", "ENTER", "RETURN", "ESCAPE"} or code in {
        8,
        9,
        13,
        27,
        46,
    }:
        return "control"
    if len(value) == 1 and value.isalpha():
        return "letter"
    if len(value) == 1 and value.isdigit():
        return "digit"
    if len(value) == 1 and not value.isalnum():
        return "punctuation"
    if 48 <= code <= 57:
        return "digit"
    if 65 <= code <= 90:
        return "letter"
    return "other"


def _number(value: str, *, field: str, source: Path) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"{source}: {field} must be numeric") from exc
    if not result >= 0:
        raise ValueError(f"{source}: {field} must be non-negative")
    return result


def _window(
    rows: list[dict[str, str]], *, participant_id: str, source: Path
) -> list[dict[str, Any]]:
    if len(rows) < MIN_EVENTS:
        return []
    events: list[dict[str, Any]] = []
    for row in rows:
        down_ms = _number(row["PRESS_TIME"], field="PRESS_TIME", source=source)
        up_ms = _number(row["RELEASE_TIME"], field="RELEASE_TIME", source=source)
        if up_ms < down_ms:
            raise ValueError(f"{source}: RELEASE_TIME precedes PRESS_TIME")
        events.append(
            {
                "dataset": DATASET,
                "session_id": f"{participant_id}/{row['TEST_SECTION_ID']}",
                "subject_id": participant_id,
                "split_group": participant_id,
                "label": 0,
                "bot_type": "human",
                "down_ms": down_ms,
                "up_ms": up_ms,
                "key_class": key_class(row["LETTER"], row["KEYCODE"]),
                "domain": "typing_test",
            }
        )
    return events


def participant_windows(
    source: Path, *, max_windows: int | None = None
) -> Iterator[list[dict[str, Any]]]:
    """Yield sentence windows from one participant file without retaining text."""
    with source.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"{source}: missing required columns")
        current_section: str | None = None
        rows: list[dict[str, str]] = []
        emitted = 0
        for row in reader:
            section = row.get("TEST_SECTION_ID", "")
            if not section:
                raise ValueError(f"{source}: TEST_SECTION_ID is required")
            if current_section is not None and section != current_section:
                window = _window(rows, participant_id=source.stem.split("_", 1)[0], source=source)
                if window:
                    yield window
                    emitted += 1
                    if max_windows is not None and emitted >= max_windows:
                        return
                rows = []
            current_section = section
            rows.append(row)
        if rows:
            window = _window(rows, participant_id=source.stem.split("_", 1)[0], source=source)
            if window:
                yield window


def _participant_paths(root: Path, max_participants: int | None, seed: int) -> list[Path]:
    files_root = root / "files"
    if not files_root.is_dir():
        files_root = root / "Keystrokes" / "files"
    paths = sorted(files_root.glob("*_keystrokes.txt"))
    if max_participants is None or max_participants >= len(paths):
        return paths
    return sorted(random.Random(seed).sample(paths, max_participants))


def load(
    root: Path,
    output_root: Path,
    *,
    max_participants: int | None = 1000,
    seed: int = 0,
    resume: bool = True,
) -> dict[str, int]:
    """Write per-participant Parquet shards with resumable progress."""
    output_root.mkdir(parents=True, exist_ok=True)
    state_path = output_root / "_state.json"
    state: dict[str, Any] = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if resume and state_path.exists()
        else {"completed": [], "malformed": 0, "windows": 0, "events": 0}
    )
    completed = set(state.get("completed", []))
    stats = {
        "participants": 0,
        "malformed": int(state.get("malformed", 0)),
        "windows": int(state.get("windows", 0)),
        "events": int(state.get("events", 0)),
    }
    for source in _participant_paths(root, max_participants, seed):
        participant_id = source.stem.split("_", 1)[0]
        if participant_id in completed:
            continue
        try:
            windows = list(participant_windows(source))
            rows = [event for window in windows for event in window]
            if rows:
                pq.write_table(
                    pa.Table.from_pylist(rows),
                    output_root / f"{participant_id}.parquet",
                )
            stats["participants"] += 1
            stats["windows"] += len(windows)
            stats["events"] += len(rows)
            completed.add(participant_id)
        except (OSError, UnicodeError, ValueError):
            stats["malformed"] += 1
            completed.add(participant_id)
        state = {**stats, "completed": sorted(completed)}
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return stats


def main() -> None:
    """Run the bounded Aalto keyboard loader."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-participants", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    print(load(args.source, args.output, max_participants=args.max_participants, seed=args.seed))


if __name__ == "__main__":
    main()

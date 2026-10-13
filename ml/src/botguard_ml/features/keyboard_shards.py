"""Build keyboard feature shards from human and synthetic event windows."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from botguard_ml.features.keyboard import keyboard_features, validate_keyboard_features
from botguard_ml.synthetic.keyboard import fit_human_timing, generate_keyboard

METADATA_COLUMNS = (
    "dataset",
    "domain",
    "session_id",
    "subject_id",
    "split_group",
    "label",
    "bot_type",
)


def _event_windows(input_root: Path) -> list[list[dict[str, Any]]]:
    windows: list[list[dict[str, Any]]] = []
    for path in sorted(input_root.glob("*.parquet")):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for batch in pq.ParquetFile(path).iter_batches(batch_size=4096):
            data = batch.to_pydict()
            for index, session_id in enumerate(data["session_id"]):
                grouped[str(session_id)].append({column: data[column][index] for column in data})
        windows.extend(grouped[session] for session in sorted(grouped))
    return windows


def _feature_row(events: list[dict[str, Any]]) -> dict[str, Any]:
    first = events[0]
    features = keyboard_features(events)
    validate_keyboard_features(features)
    return {
        **{name: float(value) for name, value in features.items()},
        **{name: first[name] for name in METADATA_COLUMNS},
    }


def build_keyboard_feature_shards(
    input_root: Path,
    output: Path,
    *,
    bot_prevalence: float = 1.0,
    seed: int = 0,
    bot_types: tuple[str, ...] = ("K1", "K2", "K4"),
) -> dict[str, int]:
    """Build human features and synthetic training-bot features.

    K3 is excluded by default and must be generated separately for held-out
    evaluation so its timing distribution cannot enter training.
    """
    if bot_prevalence < 0:
        raise ValueError("bot_prevalence must not be negative")
    human_windows = _event_windows(input_root)
    if not human_windows:
        raise ValueError(f"no keyboard event shards found under {input_root}")
    if any(bot_type == "K3" for bot_type in bot_types):
        raise ValueError("K3 is held out and cannot be included in training shards")
    human_rows = [_feature_row(window) for window in human_windows]
    profile = fit_human_timing(human_windows)
    target_bots = int(round(len(human_rows) * bot_prevalence))
    bot_rows: list[dict[str, Any]] = []
    for index in range(target_bots):
        bot_type = bot_types[index % len(bot_types)]
        n_keys = len(human_windows[index % len(human_windows)])
        events = generate_keyboard(
            bot_type,
            n_keys=n_keys,
            seed=seed + index,
            profile=profile,
            slow=bot_type == "K1" and index % 5 == 0,
        )
        bot_rows.append(_feature_row(events))
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(human_rows + bot_rows), output)
    (output.parent / "keyboard_features.schema.json").write_text(
        json.dumps(
            {
                "version": 1,
                "metadata_columns": list(METADATA_COLUMNS),
                "feature_columns": list(human_rows[0].keys() - set(METADATA_COLUMNS)),
                "held_out_bot_types": ["K3"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"human_windows": len(human_rows), "bot_windows": len(bot_rows)}

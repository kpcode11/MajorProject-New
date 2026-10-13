"""Measure whether human-only mouse windows reveal their source dataset."""

from __future__ import annotations

import argparse
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from botguard_ml.features.windowing import window_events

FEATURE_NAMES = (
    "n_moves",
    "duration_s",
    "path_over_bbox",
    "displacement_over_bbox",
    "straightness",
    "dt_mean_ms",
    "dt_std_ms",
    "dt_mode_fraction",
)


def _finite(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def window_features(events: list[dict[str, Any]]) -> list[float] | None:
    """Return features invariant to translation and global coordinate scale."""
    moves = [event for event in events if event.get("event") == "move"]
    if len(moves) < 2:
        return None
    points = [
        (x, y, t)
        for event in moves
        if (x := _finite(event.get("x"))) is not None
        and (y := _finite(event.get("y"))) is not None
        and (t := _finite(event.get("t_ms"))) is not None
    ]
    if len(points) < 2:
        return None
    xs = np.asarray([point[0] for point in points])
    ys = np.asarray([point[1] for point in points])
    times = np.asarray([point[2] for point in points])
    distances = np.hypot(np.diff(xs), np.diff(ys))
    deltas = np.diff(times)
    valid = deltas > 0
    deltas = deltas[valid]
    distances = distances[valid]
    if len(deltas) == 0:
        return None
    bbox_diagonal = math.hypot(float(xs.max() - xs.min()), float(ys.max() - ys.min()))
    scale = bbox_diagonal if bbox_diagonal > 0 else 1.0
    path = float(distances.sum())
    displacement = math.hypot(float(xs[-1] - xs[0]), float(ys[-1] - ys[0]))
    rounded = np.round(deltas).astype(int)
    _, frequencies = np.unique(rounded, return_counts=True)
    return [
        float(len(points)),
        float((times[-1] - times[0]) / 1000.0),
        path / scale,
        displacement / scale,
        displacement / path if path > 0 else 0.0,
        float(deltas.mean()),
        float(deltas.std()),
        float(frequencies.max() / len(deltas)),
    ]


def _session_events(path: Path) -> dict[str, list[dict[str, Any]]]:
    sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    parquet = pq.ParquetFile(path)
    columns = [
        "session_id",
        "label",
        "dataset",
        "domain",
        "event",
        "t_ms",
        "x",
        "y",
    ]
    for batch in parquet.iter_batches(batch_size=4096, columns=columns):
        data = batch.to_pydict()
        for index, session_id in enumerate(data["session_id"]):
            if data["label"][index] != 0:
                continue
            sessions[str(session_id)].append(
                {
                    "event": data["event"][index],
                    "t_ms": data["t_ms"][index],
                    "x": data["x"][index],
                    "y": data["y"][index],
                }
            )
    return sessions


def collect_features(
    input_root: Path, max_sessions: int
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    features: list[list[float]] = []
    targets: list[str] = []
    groups: list[str] = []
    for dataset_root in sorted(path for path in input_root.iterdir() if path.is_dir()):
        sessions_seen = 0
        for shard in sorted(dataset_root.glob("*.parquet")):
            for session_id, events in _session_events(shard).items():
                if sessions_seen >= max_sessions:
                    break
                for window in window_events(events, min_moves=20):
                    vector = window_features(window)
                    if vector is not None:
                        features.append(vector)
                        targets.append(dataset_root.name)
                        groups.append(f"{dataset_root.name}:{session_id}")
                sessions_seen += 1
    return np.asarray(features, dtype=float), np.asarray(targets), groups


def pairwise_results(
    features: np.ndarray, targets: np.ndarray, groups: list[str], seed: int
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for left, right in itertools.combinations(sorted(set(targets.tolist())), 2):
        mask = np.isin(targets, [left, right])
        pair_features = features[mask]
        pair_targets = targets[mask]
        pair_groups = np.asarray(groups)[mask]
        unique_groups = sorted(set(pair_groups.tolist()))
        group_classes = {
            label: sum(group.startswith(f"{label}:") for group in unique_groups)
            for label in (left, right)
        }
        if (
            min(group_classes.values()) < 2
            or min(np.sum(pair_targets == label) for label in (left, right)) < 2
        ):
            results.append(
                {
                    "pair": [left, right],
                    "status": "insufficient_data",
                    "reason": "need at least two sessions and two windows per dataset",
                    "sessions_per_dataset": group_classes,
                    "windows": int(len(pair_targets)),
                }
            )
            continue
        rng = np.random.default_rng(seed)
        test_groups = {
            label: rng.choice(
                [group for group in unique_groups if group.startswith(f"{label}:")],
                size=1,
                replace=False,
            )[0]
            for label in (left, right)
        }
        test_mask = np.isin(pair_groups, list(test_groups.values()))
        train_mask = ~test_mask
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, random_state=seed),
        )
        model.fit(pair_features[train_mask], pair_targets[train_mask])
        predictions = model.predict(pair_features[test_mask])
        results.append(
            {
                "pair": [left, right],
                "status": "ok",
                "accuracy": float(accuracy_score(pair_targets[test_mask], predictions)),
                "train_windows": int(train_mask.sum()),
                "test_windows": int(test_mask.sum()),
                "test_sessions": sorted(set(pair_groups[test_mask].tolist())),
            }
        )
    return results


def run(input_root: Path, output: Path, max_sessions: int, seed: int) -> None:
    features, targets, groups = collect_features(input_root, max_sessions)
    report = {
        "feature_names": list(FEATURE_NAMES),
        "scale_invariance": "coordinates are normalized by each window bounding-box diagonal",
        "human_only": True,
        "windowing": {"window_s": 10, "hop_s": 5, "min_moves": 20},
        "datasets": sorted(set(targets.tolist())),
        "windows": int(len(targets)),
        "status": "ok" if len(targets) else "insufficient_data",
        "reason": (
            None
            if len(targets)
            else "No human-only windows with at least 20 move events were found."
        ),
        "results": pairwise_results(features, targets, groups, seed) if len(targets) else [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/interim"))
    parser.add_argument("--output", type=Path, default=Path("results/mouse/fingerprint.json"))
    parser.add_argument("--max-sessions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.max_sessions < 1:
        raise ValueError("max-sessions must be positive")
    run(args.input_root, args.output, args.max_sessions, args.seed)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()

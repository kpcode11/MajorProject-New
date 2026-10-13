"""Create bounded exploratory figures from canonical mouse Parquet shards."""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyarrow.parquet as pq


@dataclass
class Session:
    """Small in-memory representation of one sampled session."""

    label: str
    bot_type: str
    x: list[float] = field(default_factory=list)
    y: list[float] = field(default_factory=list)
    t_ms: list[float] = field(default_factory=list)


def collect_sessions(
    shard: Path, *, max_sessions: int, max_points: int
) -> list[Session]:
    """Read move events from a shard while retaining bounded session samples."""
    sessions: dict[str, Session] = {}
    parquet = pq.ParquetFile(shard)
    for batch in parquet.iter_batches(
        batch_size=4096,
        columns=["session_id", "label", "bot_type", "event", "x", "y", "t_ms"],
    ):
        columns = batch.to_pydict()
        for index, event in enumerate(columns["event"]):
            if event != "move":
                continue
            session_id = str(columns["session_id"][index])
            session = sessions.get(session_id)
            if session is None:
                if len(sessions) >= max_sessions:
                    continue
                session = Session(
                    label=str(columns["label"][index]),
                    bot_type=str(columns["bot_type"][index]),
                )
                sessions[session_id] = session
            if len(session.x) >= max_points:
                continue
            x = columns["x"][index]
            y = columns["y"][index]
            t_ms = columns["t_ms"][index]
            if x is None or y is None or t_ms is None:
                continue
            if any(
                isinstance(value, float) and not math.isfinite(value)
                for value in (x, y, t_ms)
            ):
                continue
            session.x.append(float(x))
            session.y.append(float(y))
            session.t_ms.append(float(t_ms))
    return list(sessions.values())


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value)


def _save_trajectory_figure(dataset: str, sessions: list[Session], output: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    grouped: dict[str, list[Session]] = defaultdict(list)
    for session in sessions:
        grouped[session.bot_type].append(session)
    for bot_type, group in sorted(grouped.items()):
        for session in group:
            axis.plot(session.x, session.y, alpha=0.7, linewidth=1, label=bot_type)
    handles, labels = axis.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    axis.legend(unique.values(), unique.keys(), loc="best")
    axis.set_title(f"{dataset}: sampled mouse trajectories")
    axis.set_xlabel("x (source coordinates)")
    axis.set_ylabel("y (source coordinates)")
    axis.invert_yaxis()
    figure.tight_layout()
    figure.savefig(output / f"{_safe_name(dataset)}_trajectories.png", dpi=140)
    plt.close(figure)


def _speed_values(session: Session) -> tuple[list[float], list[float]]:
    speeds: list[float] = []
    times: list[float] = []
    for index in range(1, len(session.x)):
        dt = session.t_ms[index] - session.t_ms[index - 1]
        if dt <= 0:
            continue
        distance = math.hypot(
            session.x[index] - session.x[index - 1],
            session.y[index] - session.y[index - 1],
        )
        speeds.append(distance / (dt / 1000.0))
        times.append(session.t_ms[index])
    return times, speeds


def _save_speed_figure(dataset: str, sessions: list[Session], output: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    for session in sessions:
        times, speeds = _speed_values(session)
        if times:
            relative = [(time - times[0]) / 1000.0 for time in times]
            axis.plot(relative, speeds, alpha=0.65, linewidth=1, label=session.bot_type)
    handles, labels = axis.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    if unique:
        axis.legend(unique.values(), unique.keys(), loc="best")
    axis.set_title(f"{dataset}: movement speed profiles")
    axis.set_xlabel("time (seconds)")
    axis.set_ylabel("speed (source units/second)")
    figure.tight_layout()
    figure.savefig(output / f"{_safe_name(dataset)}_speed.png", dpi=140)
    plt.close(figure)


def _save_interval_figure(dataset: str, sessions: list[Session], output: Path) -> None:
    intervals = [
        session.t_ms[index] - session.t_ms[index - 1]
        for session in sessions
        for index in range(1, len(session.t_ms))
        if session.t_ms[index] > session.t_ms[index - 1]
    ]
    figure, axis = plt.subplots(figsize=(8, 5))
    if intervals:
        axis.hist(np.asarray(intervals), bins=min(40, max(10, len(intervals) // 10)))
    axis.set_title(f"{dataset}: sampling-interval distribution")
    axis.set_xlabel("interval (milliseconds)")
    axis.set_ylabel("move-event count")
    figure.tight_layout()
    figure.savefig(output / f"{_safe_name(dataset)}_sampling_intervals.png", dpi=140)
    plt.close(figure)


def run(input_root: Path, output_root: Path, max_sessions: int, max_points: int) -> int:
    """Generate three figures for every canonical dataset shard directory."""
    output_root.mkdir(parents=True, exist_ok=True)
    dataset_count = 0
    for dataset_root in sorted(path for path in input_root.iterdir() if path.is_dir()):
        shards = sorted(dataset_root.glob("*.parquet"))
        if not shards:
            continue
        sessions: list[Session] = []
        for shard in shards:
            remaining = max_sessions - len(sessions)
            if remaining <= 0:
                break
            sessions.extend(
                collect_sessions(shard, max_sessions=remaining, max_points=max_points)
            )
        if not sessions:
            continue
        _save_trajectory_figure(dataset_root.name, sessions, output_root)
        _save_speed_figure(dataset_root.name, sessions, output_root)
        _save_interval_figure(dataset_root.name, sessions, output_root)
        dataset_count += 1
    return dataset_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("data/interim"))
    parser.add_argument("--output-root", type=Path, default=Path("results/mouse/eda"))
    parser.add_argument("--max-sessions", type=int, default=12)
    parser.add_argument("--max-points", type=int, default=2000)
    args = parser.parse_args()
    if args.max_sessions < 1 or args.max_points < 1:
        raise ValueError("max-sessions and max-points must be positive")
    print(
        f"wrote figures for {run(args.input_root, args.output_root, args.max_sessions, args.max_points)} datasets"
    )


if __name__ == "__main__":
    main()

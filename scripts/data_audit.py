"""Audit canonical mouse Parquet shards without loading a dataset into memory."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

WINDOW_MS = 10_000.0
HOP_MS = 5_000.0
MIN_MOVES = 20
RESERVOIR_LIMIT = 20_000


class NumericSummary:
    """Bounded online summary with a deterministic sample for percentiles."""

    def __init__(self) -> None:
        self.count = 0
        self.minimum = math.inf
        self.maximum = -math.inf
        self.total = 0.0
        self.sample: list[float] = []

    def add(self, value: Any) -> None:
        if value is None:
            return
        number = float(value)
        if not math.isfinite(number):
            return
        self.count += 1
        self.minimum = min(self.minimum, number)
        self.maximum = max(self.maximum, number)
        self.total += number
        if len(self.sample) < RESERVOIR_LIMIT:
            self.sample.append(number)

    def as_dict(self) -> dict[str, float | int | None]:
        if not self.count:
            return {"count": 0, "min": None, "max": None, "mean": None, "p50": None, "p95": None}
        ordered = sorted(self.sample)
        return {
            "count": self.count,
            "min": self.minimum,
            "max": self.maximum,
            "mean": self.total / self.count,
            "p50": _percentile(ordered, 0.50),
            "p95": _percentile(ordered, 0.95),
        }


def _percentile(values: list[float], fraction: float) -> float:
    index = min(len(values) - 1, int(round((len(values) - 1) * fraction)))
    return values[index]


def _inc(counter: Counter[str], value: Any) -> None:
    counter[str(value)] += 1


def _window_count(move_times: list[float]) -> int:
    if not move_times:
        return 0
    times = sorted(move_times)
    first = times[0]
    last = times[-1]
    n_times = len(times)
    count = 0
    step_idx = 0
    left = 0
    while True:
        start = first + step_idx * HOP_MS
        if start > last:
            break
        while left < n_times and times[left] < start:
            left += 1
        if left >= n_times:
            break
        end = start + WINDOW_MS
        if times[left] >= end:
            jump = math.floor((times[left] - first - WINDOW_MS) / HOP_MS) + 1
            step_idx = max(step_idx + 1, jump)
            continue
        right = left
        while right < n_times and times[right] < end:
            right += 1
        if right - left >= MIN_MOVES:
            count += 1
        step_idx += 1
    return count


def audit_file(path: Path) -> dict[str, Any]:
    """Audit one Parquet file using record batches and bounded summaries."""
    counts: dict[str, Counter[str]] = {
        "label": Counter(),
        "bot_type": Counter(),
        "domain": Counter(),
        "event": Counter(),
        "coord_space": Counter(),
        "touchscreen": Counter(),
    }
    subjects: set[str] = set()
    session_ids: set[str] = set()
    sessions: dict[str, list[float]] = defaultdict(list)
    numeric = {field: NumericSummary() for field in ("t_ms", "x", "y", "dt_ms", "events_per_second")}
    missing: Counter[str] = Counter()
    total_rows = 0
    previous_t: dict[str, float] = {}

    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=4096):
        columns = batch.to_pydict()
        row_count = batch.num_rows
        total_rows += row_count
        for index in range(row_count):
            session_id = str(columns["session_id"][index])
            session_ids.add(session_id)
            subjects.add(str(columns["subject_id"][index]))
            for field in counts:
                _inc(counts[field], columns[field][index])
            t_ms = columns["t_ms"][index]
            for field in ("t_ms", "x", "y"):
                value = columns[field][index]
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    missing[field] += 1
                numeric[field].add(value)
            if columns["event"][index] == "move" and t_ms is not None:
                sessions[session_id].append(float(t_ms))
                prior = previous_t.get(session_id)
                if prior is not None:
                    numeric["dt_ms"].add(float(t_ms) - prior)
                previous_t[session_id] = float(t_ms)
            else:
                previous_t.pop(session_id, None)
            for field in ("screen_w", "screen_h"):
                if columns[field][index] is None or (
                    isinstance(columns[field][index], float)
                    and math.isnan(columns[field][index])
                ):
                    missing[field] += 1

    for move_times in sessions.values():
        duration = max(move_times) - min(move_times) if len(move_times) > 1 else 0.0
        if duration > 0:
            numeric["events_per_second"].add(len(move_times) * 1000.0 / duration)
    windows = sum(_window_count(times) for times in sessions.values())
    return {
        "source": str(path),
        "rows": total_rows,
        "sessions": len(session_ids),
        "subjects": len(subjects),
        "counts": {name: dict(counter) for name, counter in counts.items()},
        "windows": {"window_s": 10, "hop_s": 5, "min_moves": MIN_MOVES, "count": windows},
        "numeric": {name: summary.as_dict() for name, summary in numeric.items()},
        "missing_values": {
            name: {"count": count, "rate": count / total_rows if total_rows else 0.0}
            for name, count in sorted(missing.items())
        },
    }


def write_markdown(report: dict[str, Any], destination: Path) -> None:
    counts = report["counts"]
    lines = [
        f"# Mouse audit: {report['dataset']}",
        "",
        f"- Source shards: {report['shards']}",
        f"- Rows: {report['rows']}",
        f"- Sessions: {report['sessions']}",
        f"- Subjects: {report['subjects']}",
        f"- Windows: {report['windows']['count']} (10 s, 5 s hop, at least 20 moves)",
        "",
        "## Counts",
        "",
        "| Dimension | Values |",
        "|---|---|",
    ]
    for name in ("label", "bot_type", "domain", "event", "coord_space", "touchscreen"):
        lines.append(f"| {name} | `{json.dumps(counts[name], sort_keys=True)}` |")
    lines.extend(["", "## Numeric summaries", "", "| Field | Summary |", "|---|---|"])
    for name, summary in report["numeric"].items():
        lines.append(f"| {name} | `{json.dumps(summary, sort_keys=True)}` |")
    lines.extend(["", "## Missing values", "", "| Field | Count | Rate |", "|---|---:|---:|"])
    for name, summary in report["missing_values"].items():
        lines.append(f"| {name} | {summary['count']} | {summary['rate']:.6f} |")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def audit_root(input_root: Path, output_root: Path) -> list[Path]:
    """Write one JSON and Markdown audit report per dataset directory."""
    output_root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for dataset_root in sorted(path for path in input_root.iterdir() if path.is_dir()):
        shards = sorted(dataset_root.glob("*.parquet"))
        if not shards:
            continue
        reports = [audit_file(shard) for shard in shards]
        combined = reports[0]
        for report in reports[1:]:
            combined["rows"] += report["rows"]
            combined["sessions"] += report["sessions"]
            combined["subjects"] += report["subjects"]
            combined["windows"]["count"] += report["windows"]["count"]
            for dimension, values in report["counts"].items():
                for key, value in values.items():
                    combined["counts"][dimension][key] = combined["counts"][dimension].get(key, 0) + value
        combined["dataset"] = dataset_root.name
        combined["shards"] = len(shards)
        output_json = output_root / f"audit_{dataset_root.name}.json"
        output_md = output_root / f"audit_{dataset_root.name}.md"
        output_json.write_text(json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_markdown(combined, output_md)
        outputs.extend((output_json, output_md))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    outputs = audit_root(args.input_root, args.output_root)
    print(f"wrote {len(outputs)} audit files")


if __name__ == "__main__":
    main()

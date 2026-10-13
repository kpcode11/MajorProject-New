"""Safely produce a shallow, read-only inventory for one configured dataset."""

from __future__ import annotations

import argparse
import collections
import os
import pathlib
import re
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".txt", ".csv", ".json", ".md", ".log"}


def human_size(size: int) -> str:
    """Format a byte count for a short inventory report."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1000 or unit == "TB":
            return f"{size:.1f} {unit}"
        size //= 1000
    raise AssertionError("unreachable")


def read_config(path: pathlib.Path) -> tuple[pathlib.Path, dict[str, str]]:
    """Read the small datasets YAML subset without requiring global dependencies."""
    root_match = re.search(r"^datasets_root:\s*['\"]?(.+?)['\"]?\s*$", path.read_text(encoding="utf-8"), re.M)
    if not root_match:
        raise ValueError("datasets_root is missing from configuration")
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^\s{2}([\w-]+):\s*\{\s*folder:\s*"([^"]+)"', line)
        if match:
            entries[match[1]] = match[2]
    return pathlib.Path(root_match[1]), entries


def inventory(key: str) -> str:
    """Return a depth-two report; file content reads are limited to small text files."""
    base_root, datasets = read_config(ROOT / "config" / "datasets.local.yaml")
    if key not in datasets:
        raise KeyError(f"unknown dataset key: {key}")
    base = base_root / datasets[key]
    lines = [f"dataset: {key}", f"path: {base}", f"exists: {base.exists()}"]
    tree_lines: list[str] = []
    stats: collections.defaultdict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    biggest: list[tuple[int, pathlib.Path]] = []
    samples: list[pathlib.Path] = []

    def walk(directory: pathlib.Path, depth: int) -> None:
        try:
            entries = list(os.scandir(directory))[:200]
        except OSError as error:
            tree_lines.append(f"cannot list {directory}: {error}")
            return
        for entry in entries:
            path = pathlib.Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                if len(tree_lines) < 80:
                    tree_lines.append(f"{'  ' * depth}[dir] {entry.name}")
                if depth < 2:
                    walk(path, depth + 1)
                continue
            size = entry.stat(follow_symlinks=False).st_size
            ext = path.suffix.lower()
            stats[ext][0] += 1
            stats[ext][1] += size
            biggest.append((size, path))
            if len(tree_lines) < 80:
                tree_lines.append(f"{'  ' * depth}{entry.name} ({human_size(size)})")
            if size < 5_000_000 and ext in TEXT_EXTENSIONS and len(samples) < 3:
                samples.append(path)

    walk(base, 0)
    lines.extend(tree_lines)
    if len(tree_lines) >= 80:
        lines.append("... tree output capped at 80 entries ...")
    lines.append("\nby extension:")
    lines.extend(f"{ext or '(none)'}: {count} files, {human_size(total)}" for ext, (count, total) in sorted(stats.items()))
    lines.append("\nlargest files:")
    lines.extend(f"{human_size(size)} {path.name}" for size, path in sorted(biggest, reverse=True)[:10])
    for path in samples:
        lines.append(f"\n--- first lines of {path.name} ---")
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            lines.extend(handle.readline()[:300].rstrip() for _ in range(5))
    for size, path in sorted(biggest, reverse=True)[:10]:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                lines.append(f"\nzip {path.name}: first members")
                lines.extend(f"  {item.filename} ({human_size(item.file_size)})" for item in archive.infolist()[:20])
    return "\n".join(lines[:120]) + "\n"


def main() -> None:
    """Write the requested inventory report below the documentation directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_key")
    key = parser.parse_args().dataset_key
    report = inventory(key)
    output = ROOT / "docs" / "datasets" / f"inventory_{key}.txt"
    output.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()

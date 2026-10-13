"""Print a concise repository status report for the next coding session."""

from __future__ import annotations

import pathlib
import re
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
TASK_PATTERN = re.compile(
    r"^\|\s*(P\d+-\d+[A-Z]?)\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*"
    r"(TODO|IN_PROGRESS|BLOCKED|DONE|SKIPPED)\s*\|"
)


def shell(*args: str) -> str:
    """Run a Git command and return stdout or stderr without raising."""
    result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, check=False)
    return (result.stdout or result.stderr).strip()


def task_rows() -> list[dict[str, object]]:
    """Parse task rows from the durable project-progress table."""
    rows: list[dict[str, object]] = []
    for line in (ROOT / "PROGRESS.md").read_text(encoding="utf-8").splitlines():
        match = TASK_PATTERN.match(line)
        if match:
            rows.append(
                {
                    "id": match[1],
                    "phase": int(match[2]),
                    "text": match[3],
                    "status": match[4],
                }
            )
    return rows


def main() -> None:
    """Print branch, task, handoff, working-tree, and recent-commit details."""
    rows = task_rows()
    print("branch:", shell("git", "branch", "--show-current"), "| last:", shell("git", "log", "-1", "--oneline"))
    counts: dict[str, int] = {}
    for row in rows:
        state = str(row["status"])
        counts[state] = counts.get(state, 0) + 1
    print("tasks:", counts)
    open_rows = [row for row in rows if row["status"] not in {"DONE", "SKIPPED"}]
    print("current phase:", open_rows[0]["phase"] if open_rows else "all done")
    for row in rows:
        if row["status"] in {"IN_PROGRESS", "BLOCKED"}:
            print(f"[{row['status']}] {row['id']} {row['text']}")
    next_task = next((row for row in rows if row["status"] == "TODO"), None)
    if next_task:
        print("next TODO:", next_task["id"], next_task["text"])
    print("\n--- HANDOFF.md (first 40 lines) ---")
    handoff = ROOT / "HANDOFF.md"
    print("\n".join(handoff.read_text(encoding="utf-8").splitlines()[:40]) if handoff.exists() else "(missing)")
    print("\n--- git status ---")
    print("\n".join(shell("git", "status", "--short").splitlines()[:20]) or "(clean)")
    print("\n--- recent commits ---")
    print(shell("git", "log", "-5", "--oneline"))


if __name__ == "__main__":
    main()

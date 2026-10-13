## Appendix G — Agent files and scripts

### G.1 `AGENTS.md`

The canonical file is delivered next to this plan as `AGENTS.md`. Copy it to the repository root unchanged (P0-02).

### G.2 `scripts/status.py` (specification and reference implementation)

Prints, in this order and with total output under about 80 lines: branch and last commit; counts of tasks per status; the current phase (phase of the first task that is not `DONE` or `SKIPPED`); any `IN_PROGRESS` or `BLOCKED` tasks; the next `TODO` task (ID and text); the first 40 lines of `HANDOFF.md`; `git status --short` (max 20 lines); the last 5 commits.

```python
import re, subprocess, pathlib

def sh(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()

root = pathlib.Path(__file__).resolve().parents[1]
rows = []
for line in (root / "PROGRESS.md").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^\|\s*(P\d+-\d+[A-Z]?)\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(TODO|IN_PROGRESS|BLOCKED|DONE|SKIPPED)\s*\|", line)
    if m:
        rows.append(dict(id=m[1], phase=int(m[2]), text=m[3], status=m[4]))

print("branch:", sh("git", "branch", "--show-current"), "| last:", sh("git", "log", "-1", "--oneline"))
counts = {}
for r in rows:
    counts[r["status"]] = counts.get(r["status"], 0) + 1
print("tasks:", counts)
open_rows = [r for r in rows if r["status"] not in ("DONE", "SKIPPED")]
print("current phase:", open_rows[0]["phase"] if open_rows else "all done")
for r in rows:
    if r["status"] in ("IN_PROGRESS", "BLOCKED"):
        print(f"[{r['status']}] {r['id']} {r['text']}")
nxt = next((r for r in rows if r["status"] == "TODO"), None)
if nxt:
    print("next TODO:", nxt["id"], nxt["text"])
print("\n--- HANDOFF.md (first 40 lines) ---")
h = root / "HANDOFF.md"
print("\n".join(h.read_text(encoding="utf-8").splitlines()[:40]) if h.exists() else "(missing)")
print("\n--- git status ---")
print("\n".join(sh("git", "status", "--short").splitlines()[:20]) or "(clean)")
print("\n--- recent commits ---")
print(sh("git", "log", "-5", "--oneline"))
```

### G.3 Thin pointer files for each tool (create in P0-02)

`.github/copilot-instructions.md` and `.cursor/rules/botguard.mdc` (add the `alwaysApply: true` front matter for Cursor) and any rules file your other tools support (for example for Antigravity or Codex, if they do not read `AGENTS.md` automatically; file names change between tool versions, so check each tool's current documentation):

```markdown
Follow AGENTS.md in the repository root. Before doing anything, run `python scripts/status.py`
and read HANDOFF.md. The full plan is docs/MASTER_PLAN.md (per-phase files in docs/plan/).
Work on one task ID at a time and update PROGRESS.md and HANDOFF.md after every task.
```

### G.4 `scripts/split_plan.py`

Splits `docs/MASTER_PLAN.md` into small files so low-budget agents read only what they need.

```python
import re, pathlib

root = pathlib.Path(__file__).resolve().parents[1]
text = (root / "docs" / "MASTER_PLAN.md").read_text(encoding="utf-8")
out = root / "docs" / "plan"
out.mkdir(parents=True, exist_ok=True)
sections = re.split(r"(?m)^(?=## )", text)
index = []
for i, sec in enumerate(sections):
    first = sec.split("\n", 1)[0]
    m_phase = re.match(r"## Phase (\d+)", first)
    m_app = re.match(r"## Appendix ([A-G])", first)
    m_num = re.match(r"## (\d+)\.", first)
    if m_phase:
        name = f"phase_{m_phase.group(1)}.md"
    elif m_app:
        name = f"appendix_{m_app.group(1).lower()}.md"
    elif m_num:
        name = f"section_{m_num.group(1)}.md"
    elif i == 0:
        name = "header.md"
    else:
        name = f"misc_{i}.md"
    (out / name).write_text(sec, encoding="utf-8")
    index.append(f"- {name}: {first.strip('# ').strip()}")
(out / "INDEX.md").write_text("# Plan index\n\n" + "\n".join(index) + "\n", encoding="utf-8")
print("wrote", len(index), "files to", out)
```

### G.5 `scripts/inventory.py` (safe dataset inventory)

Usage: `python scripts/inventory.py <dataset_key>`. Reads `config/datasets.local.yaml`; resolves `datasets_root/folder`; prints (never more than about 120 lines): a depth-2 tree via `os.scandir`, file counts and total size per extension, the 10 largest files, and for up to 3 **small** text files (under 5 MB) the first 5 lines truncated to 300 characters. For files over 200 MB it must read at most the first 50 KB. It must never recurse deeper than 2 levels and never read file contents of `.zip` members except listing the first 20 member names with sizes (`zipfile.ZipFile.infolist()`).

```python
import os, sys, zipfile, pathlib, yaml, collections

def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024: return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

def main(key):
    root = pathlib.Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / "config" / "datasets.local.yaml").read_text(encoding="utf-8"))
    base = pathlib.Path(cfg["datasets_root"]) / cfg["datasets"][key]["folder"]
    print("path:", base, "exists:", base.exists())
    stats = collections.defaultdict(lambda: [0, 0]); biggest = []; small_text = []
    def walk(p, depth):
        try:
            entries = list(os.scandir(p))
        except OSError as e:
            print("cannot list", p, e); return
        for e in entries[:200]:
            if e.is_dir(follow_symlinks=False):
                print("  " * depth + f"[dir] {e.name}")
                if depth < 2: walk(e.path, depth + 1)
            else:
                size = e.stat().st_size; ext = pathlib.Path(e.name).suffix.lower()
                stats[ext][0] += 1; stats[ext][1] += size; biggest.append((size, e.path))
                if depth < 2: print("  " * depth + f"{e.name}  ({human(size)})")
                if size < 5_000_000 and ext in (".txt", ".csv", ".json", ".md", ".log") and len(small_text) < 3:
                    small_text.append(e.path)
    walk(base, 0)
    print("\nby extension:", {k: (v[0], human(v[1])) for k, v in stats.items()})
    print("largest:", [(human(s), pathlib.Path(p).name) for s, p in sorted(biggest, reverse=True)[:10]])
    for p in small_text:
        print(f"\n--- first lines of {pathlib.Path(p).name} ---")
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(5): print(f.readline()[:300].rstrip())
    for s, p in sorted(biggest, reverse=True)[:10]:
        if p.lower().endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                print(f"\nzip {pathlib.Path(p).name}: first members")
                for info in z.infolist()[:20]: print(" ", info.filename, human(info.file_size))

if __name__ == "__main__":
    main(sys.argv[1])
```

### G.6 Human checklist when switching tools

1. Ask the current tool: "Update HANDOFF.md and PROGRESS.md, run the fast tests and commit." (If it already ran out, skip this step.)
2. Close the old tool's agent session. Make sure only one tool touches the repository.
3. Open the next tool in the same repository folder and branch.
4. Paste resume prompt 1 or 2 from Appendix F.4.
5. After the first reply, check that the agent ran `python scripts/status.py` and named the correct task ID.

---

*End of master plan v2. This file is the single source of truth; record every deviation in `docs/decision_log.md`.*

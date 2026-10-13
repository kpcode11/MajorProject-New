## 0. Agent operating manual

### 0.1 The situation you are working in

- Several different AI tools will work on this repository **in turns**. You may be cut off mid-task when your free-tier tokens run out, and a different tool continues after you.
- Therefore **the repository is the only memory**. Nothing important may live only in chat. Everything needed to continue must be in `PROGRESS.md`, `HANDOFF.md`, `docs/decision_log.md`, committed code and committed notes.
- Never assume the next agent saw your conversation. Never assume you saw the previous one.

### 0.2 Session start protocol (every session, no exceptions)

1. Read `AGENTS.md` (short rules).
2. Run `python scripts/status.py` (Appendix G.2). It prints the current phase, the in-progress or next task, `HANDOFF.md`, the git status and recent commits.
3. Read `HANDOFF.md` fully. Read only the plan section for the current phase plus the appendices that section references.
4. Check the working tree: if there are uncommitted changes, run the quick tests (`python scripts/tasks.py test-fast`). Keep the changes if tests pass or the changes clearly belong to the in-progress task; otherwise `git stash` them with a message and note it in `HANDOFF.md`.
5. Continue the **in-progress task**; if none, take the first `TODO` task of the current phase whose prerequisites are done.

### 0.3 Task protocol

- Work on **one task at a time**, identified by its ID (for example `P2-04`). Tasks are deliberately small (target: a diff of roughly 50-200 lines plus tests).
- Task statuses in `PROGRESS.md`: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `SKIPPED` (with reason).
- Set `IN_PROGRESS` and write the task ID into `HANDOFF.md` **before** starting.
- On completion: tests pass, lint passes, `PROGRESS.md` updated with the commit hash, `HANDOFF.md` rewritten for the *next* task, commit.
- Commit message format: `P2-04: add mouse segmentation (tests pass)`. Work-in-progress commits use `wip(P2-04): ...` and keep the task `IN_PROGRESS`.
- Do not start a new task if you suspect you have little budget left (see 0.4).

### 0.4 When you are running low on tokens

Signs: the tool warns about limits, replies get truncated, or the context is very large.

1. **Stop starting new work.**
2. Make the code consistent: finish the current small step or revert the half-edited file (`git restore <file>`) so nothing is syntactically broken.
3. Rewrite `HANDOFF.md` using the template in Appendix F.2: task ID, what is done, the exact next step, files touched, commands to run, known problems.
4. Run `python scripts/tasks.py test-fast`; record the result in `HANDOFF.md`.
5. Commit (`wip(...)` is fine).
6. End your last message with the **resume prompt** (Appendix F.4). The human pastes it into the next tool.

If you are cut off without warning, the next agent relies on the last commit, `PROGRESS.md`, `HANDOFF.md` (possibly stale) and `git diff`. This is why you must update `HANDOFF.md` at **every task boundary**, not only when low on tokens.

### 0.5 Rules for working across several tools

- **One tool at a time on the working tree.** Never run two agents simultaneously.
- Prefer **small targeted edits** over rewriting whole files (smaller diffs, fewer conflicts between tools).
- Work on a branch per phase (`phase-2-mouse-model`). Merge to `main` only after the phase acceptance checklist passes and a human has reviewed.
- Keep tool-specific files thin. `AGENTS.md` is canonical; `.github/copilot-instructions.md`, `.cursor/rules/botguard.mdc` and similar files only point to it (contents in Appendix G.3). If a tool does not load them automatically, the human pastes the resume prompt.
- Do not reformat or reorganise code that you are not changing.
- Never "improve" decisions already recorded in `docs/decision_log.md` without adding a new entry and asking the human.

### 0.6 Token hygiene (important on free tiers)

- Never `cat` or print large files. Use `head -n 30`, `tail -n 30`, `Select-Object -First 30`, or small Python snippets that print summaries.
- Cap any printed output at about 100 lines. Redirect long outputs to `logs/<name>.log` (git-ignored) and read only the tail.
- Run tests quietly: `pytest -q -x --maxfail=3`. Print only failures.
- Do not paste whole files back into the chat when a path and a line range suffices.
- Read plan sections selectively. Use `docs/plan/phase_N.md` (created in P0-02) rather than this entire file.
- Prefer deterministic scripts over long reasoning: if a task is mechanical (conversion, tables), write a script and run it.
- Do not re-run expensive jobs. Use cached outputs (0.7).

### 0.7 Safe handling of large datasets (hard rules)

Some dataset files are very large (the Aalto keystroke data is about 16 GB unzipped; CaptchaSolve30k is about 4.8 GB). The laptop's RAM and disk are limited.

- **Never read a whole dataset into memory.** Process in chunks or per file: `pandas.read_csv(..., chunksize=...)`, `pyarrow` row groups, line-by-line iteration, or per-participant files.
- **Never copy, move, unzip-in-place or modify raw dataset folders.** They are read-only inputs. If a dataset is still a `.zip`, read members through `zipfile` without extracting everything. If extraction is truly needed, extract only the needed members to `data/raw_cache/` (git-ignored) and ask the human first if it exceeds 2 GB.
- **Do not run recursive searches over the dataset root** (`grep -r`, `find`, `Get-ChildItem -Recurse` with content filters). List directories shallowly with `os.scandir`, report counts and sizes, and open only a few small files.
- Before opening a file larger than 200 MB, check its size and open only the first 50 KB to learn the format (`open(...).read(50_000)`).
- **Sample, do not exhaust.** All loaders accept `--max-sessions` / `--max-participants` and a seed. Default to small samples during development (for example 500 sessions, 1,000 participants) and increase only for final training runs, with the human's approval.
- **Make every long job resumable and idempotent.** Write outputs in shards (`data/interim/<dataset>/part-0007.parquet`) plus a `_progress.json`. On restart, skip shards that already exist. This is essential because a tool may be cut off mid-job.
- **Check disk space** (`shutil.disk_usage`) before writing; stop and ask the human if free space is under 10 GB or if a job would write more than 5 GB.
- Keep memory bounded: record a configurable `limits.max_ram_gb` (default 6) and design chunk sizes accordingly.
- Never commit data. `data/`, `logs/`, `*.parquet`, `*.zip`, `*.onnx` above 50 MB, `.env` are git-ignored.
- Hash large files cheaply: record size, modified time and a SHA-256 of the first 1 MB, not of the full file.
- Respect licences and terms (listed in Section 5). The CaptchaSolve30k terms forbid re-identification and biometric profiling; this project uses it only for bot-detection research and must not build user-identification features.

### 0.8 Hard rules (carried over)

- **Never invent results.** Every metric, figure and table must come from a script and be saved under `results/`. If it was not run, say so.
- **Never assume a dataset's file format.** Inspect, then write the loader. Record findings in `docs/datasets/<name>.md`. The format hints in Section 5 come from public documentation and must be verified against the real files.
- **No leakage.** Split by participant (human) and by generator/run (bot). Fit scalers/encoders on training data only.
- **Typed characters are never stored.** Keyboard data contains timing and key **class** only. Loaders convert key identity to a class in memory and discard it.
- **The target is a mock portal.** Do not target or imitate real UIDAI or any third-party site. The bot simulator refuses non-local hosts.
- **Stay in scope.** Record deviations in `docs/decision_log.md`.
- **When blocked or a human action is needed** (`[HUMAN]`), set the task `BLOCKED`, write the question and two options in `HANDOFF.md`, and stop.

### 0.9 Definition of done for any task

Code implemented; tests added and passing; lint passes; docs updated if behaviour changed; `PROGRESS.md` updated; `HANDOFF.md` rewritten; committed.

---

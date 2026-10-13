# AGENTS.md — rules for any AI coding agent working in this repository

Project: passive bot detection to replace CAPTCHA (SIH1672). Windows laptop. Several AI tools work here in turns on free tiers and may be cut off at any time, so **the repository is the only memory**.

## Start of every session
1. Run: python scripts/status.py
2. Read HANDOFF.md fully.
3. Read only the current phase file: docs/plan/phase_N.md (the full plan is docs/MASTER_PLAN.md; do not read all of it).
4. If there are uncommitted changes, run: python scripts/tasks.py test-fast. Keep changes if tests pass or they clearly belong to the in-progress task; otherwise git stash with a message and note it in HANDOFF.md.
5. Continue the IN_PROGRESS task, otherwise take the first TODO task of the current phase.

## While working
- One task at a time, identified by its ID (for example P2-04). Set it IN_PROGRESS in PROGRESS.md and name it in HANDOFF.md before starting.
- Small targeted edits only. Do not reformat or reorganise code you are not changing.
- After each task: tests and lint pass, PROGRESS.md updated (status and commit hash), HANDOFF.md rewritten for the next task, then commit as "P2-04: short description". Work in progress: "wip(P2-04): ...".
- Never run two agents at the same time. Work on the phase branch, not main.

## If you are running low on tokens
Stop starting new work. Make the code consistent (finish the step or git restore the half-edited file). Rewrite HANDOFF.md (task ID, what is done, exact next step, files touched, commands, problems). Run python scripts/tasks.py test-fast. Commit. End your last message with the resume prompt from docs/MASTER_PLAN.md Appendix F.4.

## Token hygiene
- Never cat or print large files. Cap printed output at about 100 lines; send long output to logs/ and read the tail.
- Run tests quietly: pytest -q -x --maxfail=3.
- Prefer small scripts to long reasoning for mechanical work. Do not re-run expensive jobs; use cached shards.

## Large datasets (hard rules)
- Datasets are read-only inputs in C:\Users\KESHAV\Downloads\datasets (paths come from config/datasets.local.yaml). Never copy, move, modify or commit them.
- Some files are huge (Aalto keystrokes about 16 GB unzipped; CaptchaSolve30k about 4.8 GB). Never load a whole dataset into memory. Process in chunks or per file; sample with a seed; write resumable shards with a progress file.
- Do not run recursive content searches over the datasets root. Do not open files over 200 MB beyond the first 50 KB. Do not fully extract zip files; read members with zipfile. Ask the human before any extraction over 2 GB or any job writing over 5 GB.
- Stop and ask if free disk space is under 10 GB.

## Non-negotiable rules
- Never invent results. Every number comes from a script and is saved under results/.
- Never assume a dataset file format. Inspect first, then write the loader.
- No leakage: split by participant (humans) and by generator or run (bots).
- Never store typed characters or key identities. Keyboard data is timing plus key class only.
- The target is a mock portal only. The bot simulator must refuse non-local hosts.
- Respect dataset licences and terms (CaptchaSolve30k forbids re-identification and biometric profiling).
- Do not change decisions in docs/decision_log.md without a new entry and human approval.
- When a human action is needed or you are blocked: set the task BLOCKED, write the question and two options in HANDOFF.md, and stop.

## Useful commands
    python scripts/status.py
    python scripts/tasks.py setup | lint | test | test-fast | data-audit | train-mouse | train-keyboard | train-touch | eval-all | serve | demo | loadtest

# AI Agent Master Plan v2 — Passive Bot Detection (SIH1672)

**Project:** Passive, behaviour-based bot detection that replaces CAPTCHA (SIH1672, UIDAI, Smart India Hackathon 2024)
**Audience:** AI coding agents (Cursor, Antigravity, GitHub Copilot, Codex, or similar), used **one at a time and in turns** because each is on a free tier and may run out of tokens at any moment.
**Developer machine:** Windows laptop. Datasets live in `C:\Users\KESHAV\Downloads\datasets` (outside the repository).
**Scope decision:** Public datasets only; no team-collected human data. Desktop (mouse + keyboard) first; mobile touch only if a usable public touch dataset is obtained (see Phase 8 decision gate).

> **Place this file in the repository at `docs/MASTER_PLAN.md`.** Every agent session starts with `AGENTS.md` (Appendix G has its content), then `HANDOFF.md`, then only the phase section it needs. Do not read this whole file in every session.

---

## Table of contents

- [0. Agent operating manual](#0-agent-operating-manual) — handoff protocol, token hygiene, safe handling of large data
- [1. Project summary and fixed decisions](#1-project-summary-and-fixed-decisions)
- [2. Repository layout](#2-repository-layout)
- [3. Conventions, tooling and Windows environment](#3-conventions-tooling-and-windows-environment)
- [4. Canonical data schemas](#4-canonical-data-schemas)
- [5. Dataset inventory and data strategy](#5-dataset-inventory-and-data-strategy)
- [6. Phase overview and milestones](#6-phase-overview-and-milestones)
- Phases: [0](#phase-0--scaffolding-and-handoff-system) · [1](#phase-1--dataset-access-inventory-and-audit-mouse) · [2](#phase-2--mouse-model) · [3](#phase-3--keyboard-model-and-desktop-fusion) · [4](#phase-4--environment-rule-layer) · [5](#phase-5--scoring-backend) · [6](#phase-6--browser-sdk) · [7](#phase-7--mock-portal-step-up-challenge-bot-simulator-desktop-end-to-end) · [8](#phase-8--mobile-extension-decision-gate) · [9](#phase-9--dashboard-privacy-accessibility) · [10](#phase-10--final-evaluation-documentation-release)
- Appendices: [A Features](#appendix-a--feature-specifications) · [B API](#appendix-b--api-contract) · [C Configs](#appendix-c--config-files) · [D Synthetic bots](#appendix-d--synthetic-bot-generator-specifications) · [E Evaluation](#appendix-e--evaluation-protocol) · [F Templates](#appendix-f--templates) · [G Agent files and scripts](#appendix-g--agent-files-and-scripts)

---

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

## 1. Project summary and fixed decisions

### 1.1 What is being built

A risk-scoring system that decides, without a puzzle, whether a web session looks human or automated:

```
browser signals -> features -> ML + rules -> risk score -> allow / step-up / deny -> signed token -> protected API
```

### 1.2 Fixed decisions (do not change without human approval)

| Topic | Decision |
|-------|----------|
| Data | Public datasets only. Missing bot classes (keyboard, touch) are generated by documented synthetic generators (Appendix D). No team-collected data. |
| Order | Mouse -> keyboard -> rules -> backend -> SDK -> portal/end-to-end (desktop MVP) -> mobile (gated) -> dashboard/privacy -> final evaluation |
| Modelling | Per-modality models (mouse, keyboard, later touch) because public datasets do not contain the same session in several modalities. Fuse at score level. |
| Unit of classification | A **time window** (default 10 seconds) of behaviour, matching what the SDK can send (bounded trace). |
| Model family | LightGBM primary; Logistic Regression and Random Forest baselines. Optional 1D-CNN only after the desktop MVP. |
| Serving | ONNX Runtime inside FastAPI. |
| SDK data | SDK sends a bounded, downsampled raw trace and key timing events; backend extracts features in Python (avoids Python/TypeScript parity bugs). In-browser feature extraction is an optional stretch. |
| Dev-friendly infrastructure | Store backend abstraction: in-memory store (default for dev and tests) or Redis; database default SQLite, optional PostgreSQL. Docker is optional, not required. |
| Honesty | Reports state: public-data results; cross-dataset generalisation; synthetic keyboard/touch bots; pseudo-session fusion; no live human validation; mobile model only if data was obtained. |

### 1.3 Non-goals

Defeating human-operated CAPTCHA farms; network-level volumetric DDoS mitigation; integration with real UIDAI systems; identifying individuals; replacing a production WAF.

### 1.4 Success criteria (report, do not fake)

| Area | Criterion |
|------|-----------|
| Mouse model | In-distribution, cross-phase, cross-dataset and held-out-bot-type ROC-AUC, PR-AUC, recall at fixed FPR, with group-bootstrap confidence intervals; human FPR on CaptchaSolve30k |
| Keyboard model | Per-generator results incl. held-out generator; human FPR on a second human source if obtained |
| Fusion | Fused vs single-modality, labelled "pseudo-session evaluation" |
| Latency | p95 server scoring time under 200 ms in a local benchmark |
| End-to-end | Demo: unprotected portal abused by simulator bots; protected portal rejects them; scripted human-like session passes |
| Privacy | No characters, no form values, no persistent identifiers; retention purge implemented and tested |
| Reproducibility | Fresh clone plus documented commands reproduces reported tables (given the datasets) |

---

## 2. Repository layout

```
passive-bot-guard/
├── AGENTS.md                      # canonical agent rules (Appendix G.1)
├── HANDOFF.md                     # rewritten at every task boundary (Appendix F.2)
├── PROGRESS.md                    # task table with IDs and statuses (Appendix F.1)
├── README.md
├── .env.example
├── .gitignore  .gitattributes
├── .github/copilot-instructions.md        # thin pointer to AGENTS.md
├── .cursor/rules/botguard.mdc             # thin pointer to AGENTS.md
├── config/
│   ├── datasets.example.yaml              # committed
│   └── datasets.local.yaml                # git-ignored; real Windows paths
├── docs/
│   ├── MASTER_PLAN.md                     # this file
│   ├── plan/                              # per-phase files created by scripts/split_plan.py
│   ├── decision_log.md  architecture.md  api.md  signals.md
│   ├── privacy_impact.md  threat_model.md  model_card.md  env.md  accessibility.md
│   ├── datasets/                          # one card per dataset + inventory outputs
│   └── report_assets/
├── scripts/
│   ├── tasks.py                           # cross-platform task runner (replaces make)
│   ├── status.py                          # session-start status report
│   ├── inventory.py                       # safe dataset inventory
│   ├── split_plan.py                      # splits MASTER_PLAN into docs/plan/phase_N.md
│   └── check_claims.py
├── data/                                  # git-ignored except README and fixtures
│   ├── README.md  raw_cache/  interim/  processed/  fixtures/
├── logs/                                  # git-ignored; long outputs
├── ml/        (pyproject.toml, src/botguard_ml/{schemas,loaders,synthetic,features,splits,train,calibrate,fuse,export_onnx,eval}, configs/, notebooks/, tests/)
├── backend/   (pyproject.toml, app/{main,config,schemas,store,nonce,rules,scoring,policy,tokens,ratelimit,db,retention}.py, config/, models/, tests/)
├── sdk/       (TypeScript; src/, test/)
├── portal/    (React mock portal)
├── dashboard/ (React admin UI)
├── simulator/ (bot tiers; localhost only)
├── loadtest/
├── results/   (mouse/ keyboard/ touch/ fusion/ system/)
└── .github/workflows/ci.yml
```

---

## 3. Conventions, tooling and Windows environment

### 3.1 Windows specifics

- Use PowerShell commands in documentation. Activate venvs with `.venv\Scripts\Activate.ps1`.
- Use `pathlib.Path` everywhere; never hard-code backslashes in code. Dataset paths come from `config/datasets.local.yaml`.
- `make` is not assumed. Use `python scripts/tasks.py <command>` (same commands as the Makefile targets: `setup`, `lint`, `test`, `test-fast`, `data-audit`, `train-mouse`, `train-keyboard`, `train-touch`, `eval-all`, `serve`, `demo`, `loadtest`, `status`).
- Long paths: the IEEE dataset folder name is long. If a path that exists raises `FileNotFoundError`, retry with the extended-length prefix (`\\?\C:\...`) or ask the human to enable Windows long paths.
- Add `.gitattributes` with `* text=auto` to avoid line-ending churn between tools.
- Do not place the repository inside OneDrive-synced folders.
- Docker is **optional**. Default dev runs use the in-memory store and SQLite. Redis/PostgreSQL via Docker Desktop or WSL2 are used only when the human asks for the production-like profile.
- Ask the human once (P0-03) for RAM, free disk, CPU cores, Python/Node versions and record them in `docs/env.md`.

### 3.2 Python

- Python 3.11+ (use what is installed if 3.10+ and note it). `pyproject.toml` per package (`ml`, `backend`). `ruff` for lint and format; `mypy` on library code.
- Type hints and docstrings with units (milliseconds, pixels).
- Single seed constant (`SEED = 42`) passed explicitly to splitters, models and generators.
- Config in YAML (`ml/configs/`, `backend/config/`); secrets only through environment variables.
- Use `logging`, not `print`, in library code.

### 3.3 TypeScript

`strict: true`, ESLint, Prettier, vitest. Build with Vite/Rollup to ES module and UMD. No runtime dependencies in the SDK core.

### 3.4 Git

Branch per phase; Conventional commit prefixes plus task ID (`feat:` etc. optional, the task ID is mandatory); small commits; never force-push.

### 3.5 Units

Time in **milliseconds** (float). Coordinates in pixels where real, and flagged `coord_space` when normalised (`pixels`, `norm01`, `grid200`). Missing values are `NaN`; each modality has a `has_<modality>` flag.

---
## 4. Canonical data schemas

All dataset loaders convert to these formats and write Parquet to `data/interim/`.

### 4.1 Mouse events table (`mouse_events.parquet`)

| Column | Type | Notes |
|--------|------|-------|
| `dataset` | str | e.g. `becaptcha_mouse` |
| `session_id` | str | unique within dataset |
| `subject_id` | str | participant id for humans; generator/run id for bots; never reused across classes |
| `label` | int | 0 = human, 1 = bot |
| `bot_type` | str | `human`, or dataset-specific bot class name |
| `t_ms` | float | milliseconds since session start |
| `x`, `y` | float | coordinates in the space named by `coord_space`; NaN-free after loader cleaning |
| `coord_space` | str | `pixels`, `norm01` or `grid200` (CaptchaSolve30k uses a 200x200 logical grid) |
| `event` | str | `move`, `down`, `up`, `click`, `scroll`, `other` |
| `screen_w`, `screen_h` | float | if available, else NaN |
| `domain` | str | task/site domain, e.g. `wiki_browsing`, `blog_platform`, `game_task` (used for domain-shift analysis) |
| `touchscreen` | bool | true if the source says input was from a touchscreen, else false/NaN |

### 4.2 Keystroke events table (`key_events.parquet`)

| Column | Type | Notes |
|--------|------|-------|
| `dataset`, `session_id`, `subject_id`, `label`, `bot_type` | as above | |
| `key_class` | str | `letter`, `digit`, `space`, `punct`, `modifier`, `enter`, `backspace`, `other` — **not** the key itself |
| `down_ms`, `up_ms` | float | key press/release times; if a dataset gives only hold/flight values, reconstruct timestamps and note it in the dataset card |

### 4.3 Touch events table (`touch_events.parquet`) — Phase 8

| Column | Type | Notes |
|--------|------|-------|
| `dataset`, `session_id`, `subject_id`, `label`, `bot_type` | as above | |
| `gesture` | str | `tap`, `swipe`, `drag`, `other` |
| `t_ms`, `x`, `y` | float | |
| `pressure`, `size` | float | NaN if unavailable |

### 4.4 Feature tables

`data/processed/<modality>_features.parquet`: one row per **segment or session** (define per modality), columns = `dataset`, `session_id`, `subject_id`, `label`, `bot_type`, `split_group`, then feature columns named exactly as in Appendix A. A matching `data/processed/<modality>_features.schema.json` lists feature names, dtypes and descriptions.

### 4.5 Dataset manifest

`data/manifest.json` records for each file: dataset name, source URL, access date, file size and modified time, SHA-256 of the **first 1 MB** for large files (full SHA-256 only for files under 100 MB), licence/terms note, loader version. The agent updates it whenever data changes.

---


## 5. Dataset inventory and data strategy

### 5.1 Where the data is

Root folder: `C:\Users\KESHAV\Downloads\datasets` (read-only inputs; see Section 0.7).

```yaml
# config/datasets.local.yaml (git-ignored)  — copy to config/datasets.example.yaml with a placeholder root
datasets_root: 'C:\Users\KESHAV\Downloads\datasets'
datasets:
  web_bot_detection:  { folder: "web_bot_detection_dataset", status: available }
  ieee_blog_bots:     { folder: "Comparative Activity Patterns of Human Users and Hierarchical Bots on a Blog Platform", status: available }
  captchasolve30k:    { folder: "CaptchaSolve30k", status: available }
  aalto_keystrokes:   { folder: "Keystrokes", status: available }
  delbot_mouse:       { folder: "DELBOT-Mouse", status: to_clone }        # not downloaded yet; see P1-07
  ul_keystroke_repo:  { folder: "FILL_IN_FOLDER_NAME", status: repo_only } # GitHub repo aronlo98/tesis; human fills in the local folder name
  becaptcha_mouse:    { status: unavailable }
  cmu_keystroke:      { status: unavailable }
  mobile_touch:       { status: none_yet }
limits: { max_ram_gb: 6, max_interim_gb: 5, default_max_sessions: 500, default_max_participants: 1000 }
```

### 5.2 Inventory table

| Key | Modality | Status | Labels | Size / notes | Role in this project |
|-----|----------|--------|--------|--------------|----------------------|
| `web_bot_detection` (Bournemouth Web Bot Detection Dataset) | Mouse + web logs | **Available** | Humans, moderate bots, advanced (human-like) bots | Two parts: part 1 has 50 human sessions plus equal numbers of moderate and advanced bot sessions; part 2 has 56 human sessions (28 users x 2, about 15-20 minutes each) plus equal bot sessions. Built on Wikipedia-derived pages. Includes a README describing the structure | **Primary labelled mouse dataset.** Treat part 1 and part 2 as two domains for cross-phase evaluation |
| `ieee_blog_bots` (IEEE DataPort, DOI 10.21227/z1tf-1v33) | Mouse + clicks + scrolls | **Available** | Humans plus 4 bot types: naive, humanish, mimic, fallible | Very small (about 0.5 MB zip; CSV/JSON; the authors cut it into 10-second samples giving about 567 samples in total). Includes `readme.md` | **External test domain and held-out-bot-type experiments.** Too small to be the main training source; report wide confidence intervals |
| `captchasolve30k` (Hugging Face `T40/CaptchaSolve30k`, also listed as `Capycap-AI/CaptchaSolve30k`) | Mouse (game tasks) | **Available** | **Humans only** | About 4.8 GB; 30,000 sessions in 3 game types; coordinates normalised to a 200x200 logical grid; 240 Hz physics ticks plus raw 1000 Hz samples stored as a base64 stream (9 bytes per sample: float32 x, float32 y, 1 byte button state); a `touchscreen` flag per session | **Human-only false-positive stress test** and source for fitting human distributions. **Not** a main training source (see 5.3) |
| `aalto_keystrokes` (Aalto 136M Keystrokes, CHI 2018) | Keyboard | **Available** (folder `Keystrokes`) | **Humans only** | 168,000 participants; about 1.4 GB zipped and 16 GB unzipped; keystroke-by-keystroke text files plus a metadata file and `readme.txt` | **Primary keyboard human data.** Sample participants; never load everything |
| `delbot_mouse` | Mouse | **Not downloaded**; public GitHub repo `chrisgdt/DELBOT-Mouse` | Human and bot (per repo) | Repository includes a dataset archive per its README (verify) | Second labelled mouse dataset for cross-dataset evaluation, if it can be obtained (P1-07) |
| `ul_keystroke_repo` | Keyboard | **Repo only** (`github.com/aronlo98/tesis`); dataset not obtained | Unknown | Contents unknown; inspect only | Low priority; may contain code or data for a web keystroke collector; use only if it holds usable data |
| `becaptcha_mouse` | Mouse | **Unavailable** | - | - | Record in decision log; do not attempt workarounds |
| `cmu_keystroke` | Keyboard | **Unavailable** | - | - | Record in decision log |
| `mobile_touch` | Touch | **None yet** | - | - | See Phase 8 decision gate and candidate sources in 5.5 |

### 5.3 Handling notes and risks per dataset

**Bournemouth (primary mouse).**
- Verify structure from its README before writing the loader. Expect separate mouse-movement data and web logs; the model uses mouse data; web logs are optional context only.
- Both bot classes were produced by the dataset authors; in-dataset scores will be optimistic. Always report cross-phase and cross-dataset results.
- Human participants were mostly researchers/volunteers in a research setting; say so in the model card.

**IEEE blog bots (external domain).**
- Tiny. Use as a **test domain** (train on Bournemouth, test on IEEE) and for **held-out bot-type** tests (for example hold out `mimic`). The small size means confidence intervals will be wide; report them.
- DataPort normally requires a login/subscription to download; the human already has the files. Cite the DOI.

**CaptchaSolve30k (human-only, different domain).**
- It contains humans only, so it must **not** be mixed in as the human class against bots from other datasets: the model could learn "game-task style means human" instead of human vs bot (a dataset confound).
- Use it for: (a) **human false-positive stress test** (what fraction of these humans does the model flag?), (b) fitting human movement statistics for synthetic generators, (c) a dataset-fingerprint check in Phase 1.
- Coordinates are normalised to a 200x200 grid and render size was randomised, so absolute pixel features are meaningless there. Compare only **scale-invariant** features across datasets, or normalise per window.
- Terms of use (from its dataset card): no re-identification; no biometric profiling or behavioural authentication; permitted for bot-detection and ML research; redistribution of derivatives must carry the same restrictions; the author asks to be told if used in a paper. This project only does bot detection and never builds user-identification features.
- Some sessions have `touchscreen = true`. These can serve only as a weak sanity check for touch-like behaviour, not as a touch training set (no pressure/size, normalised coordinates).

**Aalto keystrokes (primary keyboard human data).**
- Free for research and non-commercial use with attribution. Cite Dhakal et al., CHI 2018, DOI 10.1145/3173574.3174220.
- Check whether the folder holds the `.zip` or the extracted text files. Do not extract the zip fully. Process participant files one at a time.
- From the dataset's publication and readme (verify against the real files): one text file per participant with per-keystroke rows including press time, release time, the displayed sentence, the typed input and a key identity/keycode column. **Map the key identity to a `key_class` in memory and drop it immediately.** Treat each typed sentence (test section) as one typing window, keeping windows with at least 10 key events.
- Browser keycode hints (verify with the readme): letters 65-90, digits 48-57 and numpad 96-105, space 32, Enter 13, Backspace 8, Shift/Ctrl/Alt 16/17/18, Tab 9, punctuation roughly 186-192 and 219-222.
- Participants vary a lot in speed and style; use participant-grouped splits and report results by speed tercile.
- Human-only: all bot data is synthetic (Appendix D.1).

**DELBOT-Mouse.** `git clone --depth 1 https://github.com/chrisgdt/DELBOT-Mouse "<datasets_root>/DELBOT-Mouse"`. Check the size of any dataset archive before extracting (see 0.7). If cloning is not possible in the agent's environment, mark `[HUMAN]` and continue with the other datasets.

### 5.4 Cross-dataset design with the data that exists

| Experiment | Train on | Test on | Notes |
|------------|----------|---------|-------|
| In-distribution | Bournemouth (grouped split) | Bournemouth held-out groups | Optimistic; report but do not headline |
| Cross-phase | Bournemouth part 1 | Bournemouth part 2 (and reverse) | Different participants and a larger site version |
| Cross-dataset | Bournemouth (+ DELBOT if obtained) | IEEE blog bots | Test set is small; wide CIs |
| Reverse cross-dataset (optional) | IEEE | Bournemouth | Small training set; treat as exploratory |
| Held-out bot type | Bournemouth minus one bot class; IEEE minus `mimic`/`fallible` | The held-out class | Shows generalisation to unseen bots |
| Human FPR stress test | Final mouse model | CaptchaSolve30k (human only) | Report share of humans flagged at the chosen thresholds, by game type |
| Keyboard | Aalto participants (grouped) + synthetic bots | Held-out participants; held-out generator K3 | Optional second human source for FPR (see Phase 3) |

### 5.5 Mobile touch: situation and candidate sources

No touch dataset is available yet. All known candidates are **human-only** (built for authentication research), so touch bots would be synthetic. Candidates to try (verify availability and terms; all are optional):

| Candidate | Where | Notes |
|-----------|-------|-------|
| HuMIdb | `github.com/BiDAlab/HuMIdb` | 600 users, many sensors; may require an access request |
| BioIdent | `ms.sapientia.ro/~manyi/bioident.html` | 71 subjects, 8 Android devices, raw stroke data download listed on the page |
| SU-AIS BB-MAS | IEEE DataPort, DOI 10.21227/rpaz-0h66 (free IEEE account) | 117 participants; swipes plus desktop/phone keystrokes; also a possible **second human keyboard source** for cross-dataset FPR checks |
| H-MOG | `cs.wm.edu/~qyang/hmog.html` | 100 volunteers, about 6 GB compressed, download needs agreeing to terms |

Phase 8 defines a decision gate: with at least one candidate obtained, train a touch model (Path A); otherwise deliver **mobile readiness without a trained touch model** (Path B) and say so clearly in the report and presentation.

---

## 6. Phase overview and milestones

| Phase | Name | Needs datasets? | Can an agent start without human help? |
|-------|------|-----------------|----------------------------------------|
| 0 | Scaffolding and handoff system | no | yes |
| 1 | Dataset access, inventory and audit (mouse) | yes (mouse) | yes, except `[HUMAN]` items |
| 2 | Mouse model | yes | yes |
| 3 | Keyboard model and desktop fusion | yes (Aalto) | yes |
| 4 | Environment rule layer | no | yes (can run in parallel with 1-3) |
| 5 | Scoring backend | models from 2-3 | yes |
| 6 | Browser SDK | no (needs backend schema) | yes |
| 7 | Mock portal, step-up, simulator, desktop end-to-end | no | yes |
| 8 | Mobile extension (decision gate) | gated | needs `[HUMAN]` decision |
| 9 | Dashboard, privacy, accessibility | no | yes |
| 10 | Final evaluation, documentation, release | all | yes |

**Milestones:** M1 after Phase 3 (offline models); **M2 after Phase 7 (desktop MVP; the minimum acceptable deliverable)**; M3 after Phase 8; M4 after Phase 10.

**If free-tier budgets are tight,** the shortest path to a defensible project is: Phases 0, 1, 2, 3 (with small samples), 4, 5, 6, 7, then 10 (reduced). Phases 8 and 9 are extensions.

---

## Phase 0 — Scaffolding and handoff system

**Goal:** A clean repository where any agent can pick up the work, with the handoff files, task runner and CI in place.

### Tasks

- [ ] **P0-01** Create the repository layout (Section 2) with empty modules and docstrings. Add `.gitignore` (data, logs, venvs, `node_modules`, `*.parquet`, `*.zip`, `.env`, `config/datasets.local.yaml`, large `*.onnx`), `.gitattributes` (`* text=auto`), `.env.example`, `data/README.md`.
- [ ] **P0-02** Create `AGENTS.md`, `HANDOFF.md`, `PROGRESS.md` (task table below, filled from this plan), `docs/decision_log.md`, and the thin pointer files `.github/copilot-instructions.md` and `.cursor/rules/botguard.mdc` (exact contents in Appendix F and G). Copy this plan to `docs/MASTER_PLAN.md` and run `python scripts/split_plan.py` (Appendix G.4) to create `docs/plan/phase_N.md` files.
- [ ] **P0-03** `[HUMAN]` Ask the human for: RAM, free disk space, CPU cores, Python version, Node version, whether Docker/WSL2 is installed, whether `git clone` works from the agent's environment. Record in `docs/env.md`. Create `config/datasets.local.yaml` from Section 5.1 and `config/datasets.example.yaml` (placeholder root).
- [ ] **P0-04** Create `ml/pyproject.toml` and `backend/pyproject.toml` with core dependencies: `numpy`, `pandas`, `pyarrow`, `scikit-learn`, `lightgbm`, `shap`, `matplotlib`, `pyyaml`, `optuna`, `onnxruntime`, `skl2onnx`/`onnxmltools` (choose a working LightGBM-to-ONNX path and note it in the decision log), `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `pyjwt`, `redis` (optional extra), `fakeredis` (dev), `pytest`, `hypothesis`, `ruff`, `mypy`. Install into per-package virtual environments.
- [ ] **P0-05** Implement `scripts/tasks.py` with the commands in Section 3.1 (initially `setup`, `lint`, `test`, `test-fast`, `status`; others may print "not implemented yet") and `scripts/status.py` (Appendix G.2).
- [ ] **P0-06** Add `.github/workflows/ci.yml`: install, lint, fast tests for Python (Node jobs are added when `sdk/` exists).
- [ ] **P0-07** Write `README.md` stub, make the first commit on `main`, create branch `phase-1-dataset-audit`.

### `PROGRESS.md` task table (create exactly this structure; the agent fills commit hashes)

```markdown
| ID | Phase | Task (short) | Status | Commit | Notes |
|----|-------|--------------|--------|--------|-------|
| P0-01 | 0 | Repo skeleton and ignore files | TODO | | |
| ... one row per task ID in this plan ... |
```

### Acceptance criteria

- [ ] `python scripts/tasks.py setup && python scripts/tasks.py lint && python scripts/tasks.py test-fast` succeeds on a fresh clone.
- [ ] `python scripts/status.py` prints the next task correctly.
- [ ] `docs/plan/` exists; `AGENTS.md`, `HANDOFF.md`, `PROGRESS.md` exist and are consistent with each other.
- [ ] CI is green.

---

## Phase 1 — Dataset access, inventory and audit (mouse)

**Goal:** Turn the available mouse datasets into the canonical format safely (large files, Windows paths) and understand them before modelling.

**Mouse sources:** Bournemouth (primary), IEEE blog bots (external), CaptchaSolve30k (human-only stress test), DELBOT-Mouse (optional). BeCAPTCHA-Mouse is unavailable.

### Tasks

- [ ] **P1-01** Implement `scripts/inventory.py` (Appendix G.5): for a dataset key, print a shallow tree (depth 2), file counts and sizes by extension, and the first few lines (max 300 characters each) of up to 3 small text files. It must never open a file over 200 MB beyond its first 50 KB. Save outputs to `docs/datasets/inventory_<key>.txt`.
- [ ] **P1-02** Run the inventory for `web_bot_detection`, `ieee_blog_bots`, `captchasolve30k`. Read each dataset's own README (Bournemouth `README`, IEEE `readme.md`) and write `docs/datasets/<key>.md` (card template, Appendix F.3): file formats actually observed, label definitions, session counts, timestamps' units and sampling rate, coordinate space, known quirks, licence/terms. **Do not guess formats.**
- [ ] **P1-03** Implement `loaders/web_bot_detection.py` producing canonical `mouse_events` shards (Section 4.1). Keep `part` (1 or 2) as `domain` sub-label (`wiki_part1`, `wiki_part2`). `subject_id` = human participant/session id for humans and generator + run id for bots. Support `--max-sessions`. Unit tests with a tiny fixture that mimics the observed format.
- [ ] **P1-04** Implement `loaders/ieee_blog_bots.py` (canonical shards; `bot_type` in `human, naive, humanish, mimic, fallible`; keep clicks and scroll events as event types). Unit tests with a fixture.
- [ ] **P1-05** Implement `loaders/captchasolve30k.py`: stream sessions (do not load the whole dataset), decode the base64 `inputStream` (9-byte samples: little-endian float32 x, float32 y, 1 byte button) into events or use `tickInputs`; set `coord_space=grid200`, `domain=game_task`, keep `gameType` and `touchscreen`. Humans only (`label=0`, `bot_type=human`). Default `--max-sessions 3000`, stratified by `gameType`, seeded. Unit test the decoder with a hand-built byte string.
- [ ] **P1-06** Decide the unit of analysis: implement `features/windowing.py` (Appendix A.1) that cuts any canonical session into 10-second windows (hop 5 s) and drops windows with too few move events. Unit tests.
- [ ] **P1-07** DELBOT-Mouse: if the environment permits, `git clone --depth 1` the repo to `<datasets_root>/DELBOT-Mouse` and inspect; if a dataset archive exists, check its size and extract only what is needed to `data/raw_cache/`. If cloning is impossible or the archive is too large, mark `[HUMAN]`, set `delbot_mouse: skipped` in the config and the decision log, and continue. If obtained, write its card and loader (same pattern as P1-03).
- [ ] **P1-08** Record in `docs/decision_log.md`: BeCAPTCHA-Mouse and CMU unavailable (no workarounds attempted); UL-Keystroke repo status; DELBOT outcome.
- [ ] **P1-09** Implement `python scripts/tasks.py data-audit` producing `results/mouse/audit_<key>.json` and `.md`: counts per label, bot type, subject and domain; window counts; events-per-second and sampling-interval distributions; coordinate ranges; missing-value rates.
- [ ] **P1-10** EDA notebook or script `ml/notebooks/01_mouse_eda.py` saving figures to `results/mouse/eda/`: sample trajectories (human vs each bot type), speed profiles, sampling-interval histograms, per dataset.
- [ ] **P1-11** **Dataset-fingerprint test:** train a small classifier to predict `dataset/domain` from scale-invariant window features of **human-only** windows. Report accuracy per pair. High accuracy means datasets are easy to tell apart, so cross-dataset results must be read with care. Save to `results/mouse/fingerprint.json`.
- [ ] **P1-12** Update `data/manifest.json` (Section 4.5 rules for hashing) and commit.

### Acceptance criteria

- [ ] Loaders for Bournemouth and IEEE (and CaptchaSolve30k) run with `--max-sessions` small and produce canonical shards; loader tests pass.
- [ ] Re-running a loader skips existing shards (idempotent) and survives being interrupted (test by killing after the first shard).
- [ ] No participant id appears in both classes within a dataset.
- [ ] Peak memory during loading stays below `limits.max_ram_gb` (measure with `tracemalloc` or `psutil` and record).
- [ ] Dataset cards exist with licence/terms and citation for every dataset used.
- [ ] `[HUMAN]` reviewed audit reports and EDA figures.

### Pitfalls

- Sampling rates and units differ per dataset: record them, resample only in a documented step.
- Some bot classes may be trivially separable (perfect regularity). Note it in the audit.
- CaptchaSolve30k coordinates are on a 200x200 grid: use scale-invariant features only when comparing with other datasets.

---

## Phase 2 — Mouse model

**Goal:** A calibrated mouse-behaviour classifier with honest in-distribution, cross-phase, cross-dataset and held-out-bot-type results, plus a human-FPR stress test, exported to ONNX.

### Tasks

- [ ] **P2-01** Implement segmentation inside each window (`features/mouse.py: segment_trajectory`, Appendix A.1) with unit tests (pause splitting, minimum points).
- [ ] **P2-02** Implement the mouse features of Appendix A.2 (per segment) and the window-level aggregation (mean, std, max over segments plus window-level timing stats). Every feature has a docstring (formula, units) and a unit test with a hand-computed example (straight line has straightness 1.0; constant speed has zero acceleration). Add `hypothesis` property tests (finite outputs; straightness in [0, 1]; translation invariance).
- [ ] **P2-03** Build window feature shards from the canonical data (`python scripts/tasks.py train-mouse --stage features --max-sessions N`). Resumable per shard; write `data/processed/mouse_features/` plus `mouse_features.schema.json`. Include `dataset`, `domain`, `session_id`, `subject_id`, `split_group`, `label`, `bot_type`.
- [ ] **P2-04** Implement `splits.py`: `grouped_split`, `cross_phase_split` (Bournemouth part 1 vs part 2), `cross_dataset_split` (train datasets, test dataset), `leave_one_bot_type_out`. Add a test asserting that no `split_group` appears in two splits.
- [ ] **P2-05** Baselines on identical splits: majority class, Logistic Regression (scaled), Random Forest, LightGBM. Save `results/mouse/baselines.csv`.
- [ ] **P2-06** Hyperparameter search for LightGBM (Optuna; default 30 trials, time-boxed) with **grouped** CV on training data only. Save `results/mouse/hparams.json`.
- [ ] **P2-07** Session-level aggregation: define how window scores combine into a session or request score (mean, mean of top-k, max, small learned aggregator). Choose using validation data only; save the comparison.
- [ ] **P2-08** Calibration (isotonic or Platt) on a separate calibration split; reliability curve and Brier score.
- [ ] **P2-09** Evaluation (Appendix E): in-distribution, cross-phase, cross-dataset (Bournemouth -> IEEE), held-out bot types, plus the **human-FPR stress test on CaptchaSolve30k** (share of windows/sessions flagged at the chosen thresholds, by game type). Group bootstrap CIs. Save tables and figures under `results/mouse/`.
- [ ] **P2-10** Ablations: feature groups (kinematics, geometry, timing, click); with/without shortcut features (`n_points`, `duration_ms`, `dt_mean`, `dt_mode_fraction`).
- [ ] **P2-11** SHAP summary and a function returning top-3 contributing features per scored window.
- [ ] **P2-12** Export ONNX to `backend/models/mouse-<version>/model.onnx` and `metadata.json` (feature order, version, data manifest hash, metrics, calibration parameters, git commit). Add the ONNX-vs-native parity test (tolerance 1e-4).
- [ ] **P2-13** Write the mouse section of `docs/model_card.md`, including limitations: small sample sizes, bots created by dataset authors, game-task domain for CaptchaSolve30k, no live human validation.

### Acceptance criteria

- [ ] `python scripts/tasks.py train-mouse` reproduces features, model and results with fixed seeds from the canonical data.
- [ ] Leakage test passes.
- [ ] Cross-phase, cross-dataset, held-out-bot-type and human-FPR results are reported **even if poor**.
- [ ] ONNX parity test passes.
- [ ] If any in-distribution AUC exceeds 0.99, the cause is investigated and documented before reporting.
- [ ] `[HUMAN]` reviewed the results and the written interpretation.

### Pitfalls

- Dataset fingerprinting (the model separates datasets, not humans from bots). Use P1-11 results; normalise timing features per window if needed and re-test.
- Shortcut features (window length, event count, regular timestamps).
- Very small test sets (IEEE): always show confidence intervals and the number of groups.

---

## Phase 3 — Keyboard model and desktop fusion

**Goal:** A keystroke-timing model trained on Aalto human typing plus documented synthetic bots, and a score-level fusion with the mouse model.

### Tasks

- [ ] **P3-01** Inventory `Keystrokes` with `scripts/inventory.py` (zip or extracted? number of files? metadata file?). Read `readme.txt`. Write `docs/datasets/aalto_keystrokes.md`. Note the size situation (16 GB unzipped) and the chosen access method (zip streaming vs extracted files).
- [ ] **P3-02** Implement `loaders/aalto_keystrokes.py`: iterate participant files lazily, sample `--max-participants` (default 1,000; seeded), treat each typed sentence as a typing window with at least 10 key events, convert timestamps to the canonical `down_ms`/`up_ms`, **map key identity to `key_class` in memory and drop it**, write sharded `key_events` Parquet with a progress file. Participants whose files are malformed are skipped and counted. Unit tests with a hand-made fixture file in the observed format.
- [ ] **P3-03** Add a test that scans every produced keyboard shard and fails if any column contains key identities, typed text or sentences.
- [ ] **P3-04** Implement text-agnostic keyboard features (Appendix A.3) with unit tests (for example constant-interval input gives `dwell_cv` near 0).
- [ ] **P3-05** Implement synthetic bot generators K1, K2, K3, K4 (Appendix D.1) in `synthetic/keyboard.py`, parameters fitted on **training participants only**, deterministic by seed, with statistical tests.
- [ ] **P3-06** Build keyboard feature shards: human windows plus synthetic bot windows at configurable prevalence. Splits grouped by participant (humans) and by generator + seed block (bots); hold out K3 entirely.
- [ ] **P3-07** Train and evaluate with the Phase 2 protocol (baselines, tuning, calibration, bootstrap CIs). Report **per-generator** recall incl. K3, results by typist speed tercile, and the human FPR at the chosen thresholds.
- [ ] **P3-08** Optional second human source for FPR: if the human obtains SU-AIS BB-MAS (Section 5.5) or if the `ul_keystroke_repo` contains usable data, add a loader and report human FPR on it. Otherwise record "single human source" as a limitation.
- [ ] **P3-09** Export ONNX plus metadata to `backend/models/keyboard-<version>/`; add the parity test.
- [ ] **P3-10** Fusion (`fuse.py`): build **pseudo-sessions** by pairing a mouse window set with a keyboard window set of the **same class** (human with human, bot with bot) using a fixed seed. Compare mouse-only, keyboard-only, average of calibrated probabilities, noisy-OR, and a logistic-regression stacker trained on a validation split. Implement the missing-modality policy (only available modalities are fused; absent is never treated as bot) with tests for: mouse only, keyboard only, both, neither. Save `backend/models/fusion-<version>/metadata.json`. Label all fusion results "pseudo-session evaluation (simulated pairing)".
- [ ] **P3-11** Update `docs/model_card.md` with keyboard and fusion sections and the limitations: human data come from a typing test with prescribed sentences; bots are synthetic; fusion is evaluated on simulated pairings.

### Acceptance criteria

- [ ] `python scripts/tasks.py train-keyboard` reproduces results with small defaults (1,000 participants) in a reasonable time on the laptop; larger runs only after human approval.
- [ ] Loader never loads the whole dataset; memory stays within limits (measured and recorded).
- [ ] The no-key-identity scan test passes.
- [ ] Held-out generator results are reported.
- [ ] Fusion handles all four modality-availability cases.
- [ ] `[HUMAN]` reviewed the limitations text.

**Milestone M1 reached** when Phases 2 and 3 pass.

---
## Phase 4 — Environment rule layer

**Goal:** Deterministic, explainable checks that need no dataset. They catch trivial automation and feed the final decision.

### Tasks

- [ ] **P4-01** Define the environment payload schema (`backend/app/schemas.py: EnvSignals`) with the fields in Appendix B.2.
- [ ] **P4-02** Implement `rules.py` with each rule as a small pure function returning `RuleResult(id, fired: bool, weight: float, reason: str)`:

| Rule id | Condition (examples) | Default weight |
|---------|----------------------|----------------|
| R01_NO_PAYLOAD | No behaviour/environment payload at all | strong |
| R02_WEBDRIVER | `webdriver == true` | strong |
| R03_UA_PLATFORM_MISMATCH | UA OS family inconsistent with `platform` | medium |
| R04_UA_HINTS_MISMATCH | UA vs client-hints brand/version inconsistent | medium |
| R05_TZ_LANG_MISMATCH | Timezone and language list implausible together (soft) | weak |
| R06_SOFTWARE_RENDERER | WebGL renderer class is a software renderer | weak/medium |
| R07_ZERO_PLUGINS_DESKTOP | Desktop UA with zero plugins and other flags | weak |
| R08_VIEWPORT_ANOMALY | Outer window size zero or viewport larger than screen | medium |
| R09_TOUCH_INCONSISTENT | Touch events vs claimed device class mismatch | weak |
| R10_NATIVE_FUNCTION_TAMPER | Native-function integrity check failed | medium |
| R11_UNTRUSTED_EVENTS | High fraction of `isTrusted == false` input events | strong |
| R12_TOO_FAST | Time from nonce issue to action under a plausible minimum | medium |
| R13_RATE_LIMIT | Request-rate caps exceeded (server-side, Store) | hard |

- [ ] **P4-03** Combine rule weights into a **rule score** in [0, 1] (documented formula) and a list of reasons. A hard rule (R13, invalid nonce/signature) bypasses the model.
- [ ] **P4-04** Make weights configurable in `backend/config/rules.yaml`.
- [ ] **P4-05** Tests: one passing and one failing payload per rule; a "normal Chrome on Windows" fixture must produce rule score near 0; a "headless default" fixture must fire several rules.
- [ ] **P4-06** Document each signal and its privacy class in `docs/signals.md`.
- [ ] **P4-07** Optional baseline: compare against the open-source BotD library's verdicts on the same fixtures (only as an offline comparison; do not add it as a runtime dependency without a decision-log entry).

### Acceptance criteria

- [ ] All rule tests pass.
- [ ] A fixture list shows expected rule outcomes in `docs/signals.md`.
- [ ] No rule uses persistent identifiers or a unique fingerprint hash.

---

## Phase 5 — Scoring backend

**Goal:** A FastAPI service that issues nonces, scores sessions (rules + ONNX models + fusion), decides, issues signed tokens and logs decisions without PII.

### Tasks

- [ ] **P5-01** `config.py`: settings from environment/YAML (`STORE_BACKEND=memory|redis`, `REDIS_URL`, `DATABASE_URL` (default SQLite), key material, model paths, thresholds file, limits). Also implement `store.py`: a small `Store` interface (get/set/delete with TTL, atomic get-and-delete, counters and sliding windows) with an in-memory implementation (default for dev and tests) and a Redis implementation; run the same tests against both (use `fakeredis` for Redis).
- [ ] **P5-02** `schemas.py`: Pydantic v2 models for all requests/responses (Appendix B). Enforce limits: max body 64 KB, max trace points (for example 600 mouse points, 300 key events), numeric ranges, string lengths.
- [ ] **P5-03** `nonce.py`: issue random 32-byte URL-safe nonces; store via the `Store` abstraction with TTL (default 300 s) bound to a context hash (IP bucket + user-agent hash); single use (atomic get-and-delete).
- [ ] **P5-04** `scoring.py`:
  - Load ONNX sessions once at startup (mouse, keyboard, later touch) with metadata checks (feature order and version).
  - Extract features by importing the **same** feature code as the ML package (`botguard_ml.features`) — install it as a local dependency. Do not duplicate feature code.
  - Run models, apply stored calibration, fuse per `fusion` metadata, combine with the rule score, return `ScoreResult(score, band, reasons, model_versions)`.
  - Explainability: top-3 contributing features per modality (use pre-computed SHAP-style approximations or tree contributions available from the model/ONNX path; if not feasible at serving time, return rule reasons plus the top features by global importance and note the limitation).
- [ ] **P5-05** `policy.py`: map score + action class to `allow | challenge | deny` using `config/policy.yaml` (Appendix C). Never return the exact score to untrusted clients; return a band (`low`, `medium`, `high`). Exact score goes only to logs and the admin API.
- [ ] **P5-06** `tokens.py`: JWT with claims `iss`, `aud`, `act`, `iat`, `exp` (60-120 s), `jti`, `band`. Support HS256 for development and RS256/ES256 via key files for production-like mode. `jti` single-use via the Store.
- [ ] **P5-07** `ratelimit.py`: sliding-window limits in the Store per IP bucket, per session id, per endpoint. Separate limits for `/v1/nonce` and `/v1/assess`.
- [ ] **P5-08** `db.py`: SQLAlchemy models (SQLite by default, PostgreSQL optional) and migrations (Alembic) for `assessments` and `challenges` (Appendix B.5). No raw traces stored by default. Optional feature storage behind a config flag with TTL.
- [ ] **P5-09** `main.py`: endpoints `GET /v1/nonce`, `POST /v1/assess`, `POST /v1/assess/challenge`, `POST /v1/token/verify`, `GET /v1/health`, admin endpoints (Phase 9), with consistent error format and request ids.
- [ ] **P5-10** Middleware dependency `require_human_token(action)` for protected routes (used by the portal's protected API).
- [ ] **P5-11** Fail-safe policy (configurable, documented in `docs/architecture.md`): Store/Redis unavailable -> deny sensitive actions; model error -> rules-only decision and `degraded=true`; DB down -> continue and buffer logs.
- [ ] **P5-12** Structured logging with request id; never log payload contents or full IPs.
- [ ] **P5-13** Tests (pytest + httpx `AsyncClient`):
  - nonce single-use, expiry, and context binding;
  - oversize/malformed payload returns 4xx quickly;
  - replayed assess payload rejected;
  - token expiry, wrong action, reused `jti`, bad signature;
  - rate limit triggers;
  - fail-safe behaviour when Redis/model is unavailable (use fakes);
  - scoring with fixture payloads gives expected bands (a clean human-like fixture -> low; a headless/straight-line-bot fixture -> high).
- [ ] **P5-14** Latency micro-benchmark script `backend/bench_scoring.py` (1,000 calls; prints p50/p95/p99).

### Deliverables

Runnable backend, tests, OpenAPI document exported to `docs/api.md`, benchmark output in `results/system/scoring_latency.json`.

### Acceptance criteria

- [ ] `pytest backend/tests -q` passes; coverage on `nonce`, `tokens`, `policy`, `ratelimit` at least 85%.
- [ ] p95 scoring time under 200 ms on the developer machine (report hardware).
- [ ] Security tests listed above pass.
- [ ] No endpoint returns the raw score to unauthenticated callers.
- [ ] `python scripts/tasks.py serve` starts the backend (in-memory store, SQLite) and `/v1/health` reports the loaded model versions. Optional: a docker-compose profile with Redis + PostgreSQL also works.

---

## Phase 6 — Browser SDK

**Goal:** A small TypeScript SDK that collects the signals of Appendix B.2/B.3, talks to the backend, and exposes a clean API plus a React wrapper.

### Tasks

- [ ] **P6-01** Create the `sdk/` package skeleton (Vite + TypeScript + vitest + ESLint), add a Node job to CI, then write `config.ts`: defaults (window length, max points, throttle interval, endpoints).
- [ ] **P6-02** `collectors/env.ts`: environment snapshot (Appendix B.2). Coarsen values (buckets, class labels). **No persistent fingerprint hash.**
- [ ] **P6-03** `collectors/mouse.ts`: `mousemove` (throttled to about 60 Hz), `mousedown/up`, `click`, `wheel`; record `isTrusted`; bounded ring buffer; output downsampled `(x, y, t)` plus counts of untrusted events.
- [ ] **P6-04** `collectors/keyboard.ts`: `keydown/keyup` timing with **key class only** (map in code; never store `event.key` or `event.code`); paste/autofill event counts only; no access to input values.
- [ ] **P6-05** `collectors/scroll.ts` and `collectors/timing.ts`: scroll summary, focus/blur/visibility transitions, time from page load to first interaction and to action.
- [ ] **P6-06** `transport.ts`: fetch nonce, build payload, POST to `/v1/assess`, handle errors, retries with backoff, timeouts; never block the host page.
- [ ] **P6-07** `index.ts`: public API `BotGuard.start()`, `assess(action)`, `runChallenge()`, `stop()`; idempotent and safe to call multiple times.
- [ ] **P6-08** `challenge.ts`: renders a pluggable step-up UI (Phase 7 provides the default implementation).
- [ ] **P6-09** `react/`: `BotGuardProvider` and `useBotGuard()` hook.
- [ ] **P6-10** Performance work: passive listeners; throttle; aggregation in `requestIdleCallback` or a Web Worker; bounded buffers; `stop()` removes all listeners and clears memory.
- [ ] **P6-11** Tests (vitest + jsdom/happy-dom): collectors produce bounded output; key collector never exposes characters (assert on serialised payload); throttling works; payload size under the 64 KB limit in a stress test; `stop()` leaves no listeners.
- [ ] **P6-12** Bundle: ES module and UMD; report gzipped size in `results/system/sdk_size.json` (target under 30 KB core).
- [ ] **P6-13** Contract test: the SDK's payload validates against the backend's Pydantic schema (generate a JSON Schema from the backend and validate SDK-produced payloads in a test).

### Acceptance criteria

- [ ] `npm test` passes in `sdk/`.
- [ ] Contract test passes.
- [ ] Serialised payloads contain no characters typed and no input values (test with a form field filled with a known string; assert the string never appears).
- [ ] Bundle size reported.

---

## Phase 7 — Mock portal, step-up challenge, bot simulator, desktop end-to-end

**Goal:** The desktop MVP: a mock portal protected by the system, a minimal step-up, and a simulator that demonstrates the difference.

### Mock portal tasks

- [ ] **P7-01** React + Vite app labelled "DEMO — not a government portal".
- [ ] **P7-02** Pages: landing; "Resident login" with an identifier text field and **Send OTP** button; "Update details" form; "Centre search".
- [ ] **P7-03** Portal backend routes (can live in the same FastAPI app under `/portal-api/`): `/otp/request`, `/details/update`, `/centres/search`. Each requires a valid `X-Human-Token` for its action via `require_human_token`.
- [ ] **P7-04** A counter endpoint `/portal-api/stats` showing accepted vs rejected calls (used in the demo).
- [ ] **P7-05** Protection mode switch (`off | passive`) controlled by an environment variable, to demonstrate unprotected vs protected behaviour.

### Step-up challenge tasks

- [ ] **P7-06** Implement a default step-up UI: **press-and-hold** button with a server-chosen random hold duration (0.8-1.5 s) and a single-click alternative path for keyboard users (Space/Enter activation). No image or text puzzles.
- [ ] **P7-07** Challenge endpoint flow: `challenge` decision returns `challenge_id`, type, and parameters; SDK captures interaction timing and sends `POST /v1/assess/challenge`; the backend re-scores using the original session plus challenge features and returns allow/deny.
- [ ] **P7-08** Rate-limit challenge attempts per session and IP bucket; challenge ids are single-use and short-lived.
- [ ] **P7-09** Accessibility: labelled controls, focus handling, visible focus ring, keyboard path tested, no time pressure beyond the hold requirement (provide the keyboard alternative).
- [ ] **P7-10** Tests: challenge success, timeout, replay, too-fast completion, wrong id.

### Bot simulator tasks (`simulator/`, localhost-only)

- [ ] **P7-11** Safety: refuse to run if the target host is not in an allowlist (`localhost`, `127.0.0.1`, entries in `simulator/allowlist.txt`).
- [ ] **P7-12** Tier 1: plain HTTP client posting directly to the protected endpoint (no browser).
- [ ] **P7-13** Tier 2: Playwright (default settings) performing direct clicks and fills.
- [ ] **P7-14** Tier 3: Playwright with common automation-hiding adjustments applied to the browser context (keep it basic and documented; this tier exists to test the rule layer).
- [ ] **P7-15** Tier 4: Playwright with human-like mouse paths (Bezier curves with ease-in/out and noise, Appendix D.3) and typing with randomised delays.
- [ ] **P7-16** `run_all.py` runs N sessions per tier with parameter randomisation and writes `results/system/sim_runs.jsonl` (tier, params, outcome: allowed / challenged / denied / blocked-at-api).
- [ ] **P7-17** A scripted **"human-like reference"** run using recorded or hand-written realistic input events to show that a normal session passes (clearly labelled as a demo script, not a validation dataset).

### End-to-end tasks

- [ ] **P7-18** Playwright E2E tests: normal interaction path -> token -> OTP accepted; headless direct click -> denied or challenged; no token -> 401.
- [ ] **P7-19** `python scripts/tasks.py demo` starts the backend (in-memory store, SQLite) and the portal dev server. An optional `deploy/docker-compose.yml` profile adds Redis and PostgreSQL.
- [ ] **P7-20** `python scripts/tasks.py demo` starts everything; `docs/demo_script.md` describes the demo steps.
- [ ] **P7-21** Report simulator outcomes per tier in `results/system/sim_summary.md` (counts and rates; do not tune the model to the simulator and then report those numbers as generalisation).

### Acceptance criteria

- [ ] With protection `off`, Tier 1-4 bots succeed in submitting OTP requests; with `passive`, the outcomes are recorded and reported honestly.
- [ ] A keyboard-only scripted session (tab navigation, Enter) is **not** denied automatically and can pass via the keyboard challenge path.
- [ ] E2E tests pass in CI (headless).
- [ ] `[HUMAN]` ran the demo on a real browser with real mouse use and confirms the experience.

**Milestone M2 reached** when Phases 5-7 pass. This is the minimum acceptable deliverable.

---


## Phase 8 — Mobile extension (decision gate)

**Goal:** Support mobile/touch devices honestly. No touch dataset is currently available, so this phase begins with a human decision gate and then follows **Path A** (a touch dataset is obtained) or **Path B** (it is not).

### Decision gate

- [ ] **P8-01** `[HUMAN]` The human tries to obtain at least one candidate touch dataset (Section 5.5: HuMIdb, BioIdent, SU-AIS BB-MAS, H-MOG) and places it under the datasets root, or states that none could be obtained. The agent records the outcome in `docs/decision_log.md` and `config/datasets.local.yaml` (`mobile_touch: available | none`), then follows Path A or Path B. Do not wait for this gate to complete other phases.

### Path A — a human touch dataset is available

- [ ] **P8-02A** Inventory and dataset card for the obtained dataset (same safe procedure as Phase 1). Respect size limits (H-MOG is about 6 GB compressed: never extract everything).
- [ ] **P8-03A** Loader producing canonical `touch_events` shards (Section 4.3), with gesture segmentation (tap, swipe, drag), device metadata where available, `--max-users` sampling, resumable shards.
- [ ] **P8-04A** Touch features (Appendix A.4) with unit tests and property tests.
- [ ] **P8-05A** Synthetic touch bot generators T1-T4 (Appendix D.2) with tests; hold out T3.
- [ ] **P8-06A** Train and evaluate with the Phase 2 protocol: grouped by user, held-out generator, per-gesture-type results, human-FPR report. Calibrate and export ONNX to `backend/models/touch-<version>/`.
- [ ] **P8-07A** Extend fusion: touch replaces mouse on touch devices (device class from environment signals and observed events), same missing-modality policy; update the fusion metadata.
- [ ] **P8-08A** Backend: extend schemas and scoring for the touch payload; update the contract test and fixtures.
- [ ] **P8-09A** Update `docs/model_card.md` and `results/touch/` with limitations (authentication datasets used for bot detection, synthetic bots, device variety).

### Path B — no touch dataset (mobile readiness without a trained touch model)

- [ ] **P8-02B** SDK `collectors/touch.ts`: capture `touchstart/move/end` (position, time, radius/force when exposed), bounded buffers, no content capture. Update the payload schema (Appendix B.3, `behaviour.touch`) and the contract test.
- [ ] **P8-03B** Backend: accept the touch payload and set `device_class`; compute touch features with the unit-tested Appendix A.4 code **only for logging and future use**, not for the decision.
- [ ] **P8-04B** Policy for touch sessions without a trained model: decision uses the rule layer, rate limits and a conservative step-up policy; logs record `model_coverage: {touch: none}` and `degraded_modality: true`; the exact policy is written to `docs/decision_log.md` and `docs/architecture.md`.
- [ ] **P8-05B** Verify the fairness rule: a touch session with no mouse events is **not** penalised for missing mouse input (test).
- [ ] **P8-06B** Mobile-friendly step-up (large tap/press-and-hold target, no hover dependence) and responsive portal layout; test with browser device emulation.
- [ ] **P8-07B** Simulator tier "mobile emulation" (Playwright device emulation with scripted taps/swipes) for the demo only.
- [ ] **P8-08B** State the limitation prominently in README, model card and presentation: "touch behaviour is not modelled; mobile protection relies on rules, rate limits and step-up". Optionally run the mouse model on CaptchaSolve30k `touchscreen=true` sessions as an informal sanity check and report it as such (not as touch validation).

### Acceptance criteria

- [ ] The gate outcome is recorded in `docs/decision_log.md`.
- [ ] **Path A:** `python scripts/tasks.py train-touch` reproduces results; held-out generator and per-gesture results reported; touch payload passes the contract test; touch sessions are not penalised for missing mouse input.
- [ ] **Path B:** touch payload accepted and logged; touch sessions follow the documented conservative policy; limitation stated in README and model card; fairness test passes.
- [ ] `[HUMAN]` checked the mobile demo (emulated or on a real phone).

**Milestone M3 reached** when this phase passes (either path).

---
## Phase 9 — Dashboard, privacy, accessibility

**Goal:** Operational visibility, enforced privacy behaviour, and verified accessibility.

### Admin API and dashboard tasks

- [ ] **P9-01** Admin endpoints (API-key protected for the student project; note in docs that production needs SSO/RBAC): `/admin/overview`, `/admin/scores`, `/admin/assessments`, `/admin/assessments/{id}`, `/admin/feedback`, `/admin/sim-results`, `/admin/privacy`.
- [ ] **P9-02** Dashboard (React + Recharts) views:
  1. Overview: requests per minute, allow/challenge/deny split, latency, model versions.
  2. Score distribution histogram with threshold lines.
  3. Session detail: decision, band, rules fired, top contributing features (derived values only, no raw traces).
  4. Simulator results per tier (from `sim_runs.jsonl` ingestion endpoint).
  5. Feedback queue: mark "false positive / false negative" (stored, never auto-used for training).
  6. Privacy panel: retention settings, record counts, last purge.
- [ ] **P9-03** Dashboard component tests and one E2E smoke test.

### Privacy tasks

- [ ] **P9-04** `retention.py`: scheduled purge (cron-like background task or CLI) that deletes stored feature JSON older than the configured TTL (default 7 days) and anonymises or deletes assessments older than the configured long-term TTL; unit-tested with a fake clock.
- [ ] **P9-05** Session identifiers: random per page load, rotating; no cross-day linkage; IP stored only as a coarse bucket (or not at all) in logs.
- [ ] **P9-06** Verify with tests that: no table column or log line contains typed characters, form values, full IPs or persistent device identifiers (scan test over a run of the E2E suite).
- [ ] **P9-07** Write `docs/privacy_impact.md`: for each signal group — purpose, necessity, less-invasive alternative considered, retention. State assumptions about UIDAI/DPDP-style requirements explicitly and that formal compliance needs legal review.
- [ ] **P9-08** **Stretch:** local feature extraction mode in the SDK (`sendRawTrace=false`). Requires a TypeScript port of the mouse/keyboard features and **golden tests**: a set of fixture traces processed by Python and TypeScript must give features within a stated tolerance. Only enable by default if parity tests pass and the model results with local features are reported.

### Accessibility tasks

- [ ] **P9-09** Run axe-core on portal and challenge pages; fix issues.
- [ ] **P9-10** Keyboard-only E2E test: complete login/OTP flow with keyboard only.
- [ ] **P9-11** Screen-reader smoke test notes (manual, `[HUMAN]` with NVDA/VoiceOver if available).
- [ ] **P9-12** Verify the missing-modality policy end-to-end: a session with no mouse events and valid keyboard navigation is not auto-denied.
- [ ] **P9-13** Document known accessibility limitations in `docs/accessibility.md`.

### Optional model upgrades (only if time remains after M3)

- [ ] **P9-14** 1D-CNN or small GRU on raw mouse trajectories (fixed-length resampling, mask for padding); compare against LightGBM with the same splits and cross-dataset protocol; export to ONNX only if it beats the baseline on cross-dataset results and meets latency.
- [ ] **P9-15** Add as an additional model in fusion with metadata.

### Acceptance criteria

- [ ] Retention tests pass.
- [ ] Privacy scan test passes in CI.
- [ ] axe-core run has no critical violations on portal pages.
- [ ] Keyboard-only E2E passes.
- [ ] Dashboard loads data from the running backend.

---

## Phase 10 — Final evaluation, documentation, release

**Goal:** Reproducible, honest results and a polished repository.

### Tasks

- [ ] **P10-01** `python scripts/tasks.py eval-all` regenerates every table and figure from scratch into `results/` and copies the report-ready ones to `docs/report_assets/`.
- [ ] **P10-02** Final experiments (Appendix E): in-distribution, leave-one-dataset-out, leave-one-bot-type-out (mouse); per-generator (keyboard, touch); fusion (pseudo-sessions); ablations (feature groups, with/without shortcut features, with/without rule layer); calibration; threshold trade-off curves (challenge band width vs bot pass-through on held-out data).
- [ ] **P10-03** System-level results: simulator outcomes per tier; latency distribution; throughput.
- [ ] **P10-04** Load test (`loadtest/`): Locust or k6 scenarios — normal mix, flood of plain HTTP requests to a protected endpoint, flood of `/v1/nonce`, flood of malformed `/v1/assess`. Report requests/second, p50/p95/p99 latency, error rates, and how many malicious requests reached the protected API.
- [ ] **P10-05** Security checks: run the replay/tamper/oversize/rate-limit test suite; `pip-audit`, `npm audit`; `bandit` on backend code; record results.
- [ ] **P10-06** Finalise `docs/model_card.md` (intended use, data, metrics with confidence intervals, limitations, fairness/accessibility notes, update policy).
- [ ] **P10-07** Finalise `docs/architecture.md`, `docs/api.md`, `docs/signals.md`, `docs/threat_model.md`.
- [ ] **P10-08** `README.md`: overview, architecture diagram, quickstart (`python scripts/tasks.py setup`, `python scripts/tasks.py demo`), how to reproduce results, dataset acquisition instructions, limitations, licences and citations.
- [ ] **P10-09** Claims check script `scripts/check_claims.py`: every number quoted in `README.md` and `docs/model_card.md` must match a value in `results/` (fail CI otherwise).
- [ ] **P10-10** Record a demo video script and a `docs/demo_script.md` (the human records the video `[HUMAN]`).
- [ ] **P10-11** Tag release `v1.0.0`; create `CITATION.cff` and `LICENSE` (ask the human which licence).

### Acceptance criteria

- [ ] Fresh-clone reproduction works: documented steps produce the same tables (within seed-determined variation).
- [ ] CI green, including claims check.
- [ ] All limitations from Section 1.2 are stated in README and model card, plus: which datasets were unavailable (BeCAPTCHA-Mouse, CMU) and whether Path A or Path B was followed in Phase 8.
- [ ] `[HUMAN]` signed off the final results text.

---

## Appendix A — Feature specifications

All features are computed per **segment** (mouse, touch) or per **typing window** (keyboard), then optionally aggregated per session. Use these exact snake_case names in feature tables. Implement in `ml/src/botguard_ml/features/` and reuse in the backend.

### A.1 Windowing and segmentation

**Unit of classification = window.** Cut each session into windows of `window_s` (default **10 s**) with hop `hop_s` (default **5 s**). Keep windows with at least `min_moves` (default **20**) move events. All windows of a session share the session's `split_group` and label. The SDK sends the most recent window (bounded to 600 points), so training and serving see the same unit. Window-level features are the mean, std and max over the segment features below plus window-level timing statistics.

**Segmentation inside a window:**

- Sort events by `t_ms`; drop exact duplicate timestamps with identical coordinates.
- A new **segment** starts after a pause with no `move` events for `pause_ms` (default **100 ms**) or at a `down`/`up`/`click` boundary.
- Keep segments with at least `min_points` (default **8**) points and path length at least `min_path_px` (default **20 px**).
- Parameters live in `ml/configs/mouse_features.yaml`; changing them requires re-running training.

### A.2 Mouse features (per segment)

Kinematics (using finite differences on `(x, y, t)`; skip zero or negative `dt`):
`speed_mean`, `speed_std`, `speed_max`, `speed_p25`, `speed_p50`, `speed_p75`, `speed_p95`, `acc_mean`, `acc_std`, `acc_max_abs`, `acc_sign_change_rate`, `jerk_mean_abs`, `jerk_std`, `ang_vel_mean_abs`, `ang_vel_std`, `curvature_mean_abs`, `curvature_std`.

Geometry:
`path_length`, `displacement`, `straightness` (displacement / path_length, in [0, 1]), `n_direction_changes` (sign changes of heading beyond a small angle threshold), `direction_change_rate` (per 100 px), `bbox_area_norm` (bounding-box area / screen area when screen size known else NaN), `tail_reversal_ratio` (path length after the point closest to the endpoint / total path length).

Timing:
`duration_ms`, `n_points`, `dt_mean`, `dt_std`, `dt_cv`, `dt_mode_fraction` (share of intervals equal to the most common rounded interval; high values indicate synthetic timing), `pause_count`, `pause_total_ms`, `speed_peak_position` (time of peak speed / duration), `accel_phase_ratio` (time to peak speed / time from peak to end).

Click-related (when events exist): `click_dwell_mean`, `click_dwell_std`, `pre_click_slowdown` (mean speed in the last 100 ms divided by segment mean speed).

**Shortcut-risk features** (`n_points`, `duration_ms`, `dt_mean`, `dt_mode_fraction`): keep in the feature table but make inclusion configurable; always run the ablation with and without them and report both.

**SDK-only integrity features** (not available in datasets, used by rules only): `frac_untrusted_events`, `teleport_count`.

### A.3 Keyboard features (per typing window)

A typing window is a run of at least **10** key events within one field/session; define the rule in config. Text-agnostic only.

`n_keys`, `typing_speed_cps`,
`dwell_mean`, `dwell_std`, `dwell_median`, `dwell_mad`, `dwell_cv`, `dwell_skew`, `dwell_kurt`,
`flight_mean`, `flight_std`, `flight_median`, `flight_mad`, `flight_cv`, `flight_skew`, `flight_kurt`, `flight_min`, `flight_p5`, `flight_p95`,
`dd_mean`, `dd_std` (down-to-down interval),
`rollover_ratio` (fraction of key pairs with negative flight time),
`burst_count`, `burst_len_mean` (bursts split by flights over 300 ms),
`pause_count`, `pause_mean` (flights over 500 ms),
`lag1_autocorr_flight`, `dwell_flight_corr`,
`identical_interval_fraction` (share of intervals equal at 1 ms rounding),
`backspace_ratio`, `paste_events` (SDK/backend only; NaN in datasets that lack it).

### A.4 Touch features (per gesture) — Phase 8

Common: `duration_ms`, `n_points`, `path_length`, `displacement`, `straightness`, `speed_mean`, `speed_std`, `speed_max`, `acc_mean`, `acc_std`, `jerk_mean_abs`, `curvature_mean_abs`, `curvature_std`, `heading_angle`, `start_end_speed_ratio`, `dt_cv`, `dt_mode_fraction`.
Pressure/size (NaN allowed): `pressure_mean`, `pressure_std`, `pressure_min`, `pressure_max`, `pressure_slope`, `size_mean`, `size_std`.
Tap sequences (session): `tap_dwell_mean`, `tap_dwell_std`, `inter_tap_mean`, `inter_tap_cv`, `tap_position_dispersion`.
Stretch (if sensor data used): `acc_xyz_var_during_gesture`, `gyro_var_during_gesture`.

---

## Appendix B — API contract

### B.1 Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/v1/nonce` | GET | none (rate-limited) | Issue single-use nonce |
| `/v1/assess` | POST | nonce in body | Score session; return decision |
| `/v1/assess/challenge` | POST | nonce + `challenge_id` | Re-score after step-up |
| `/v1/token/verify` | POST | service API key | Optional remote token check |
| `/v1/health` | GET | none | Liveness, model versions |
| `/admin/*` | various | admin API key | Dashboard data |

Error format: `{"error": {"code": "invalid_nonce", "message": "...", "request_id": "..."}}`.

### B.2 Environment signals (`env`)

```json
{
  "webdriver": false,
  "ua_family": "chrome",
  "ua_major": 126,
  "ua_os": "windows",
  "platform": "Win32",
  "hints_brands": ["Chromium", "Google Chrome"],
  "hints_platform": "Windows",
  "languages_count": 2,
  "lang_primary": "en-IN",
  "timezone_offset_min": -330,
  "screen_w_bucket": 1920,
  "screen_h_bucket": 1080,
  "viewport_w": 1280,
  "viewport_h": 720,
  "outer_w": 1296,
  "outer_h": 800,
  "dpr_bucket": 1,
  "hw_concurrency_bucket": 8,
  "device_memory_bucket": 8,
  "webgl_renderer_class": "hardware",
  "plugins_count": 5,
  "max_touch_points": 0,
  "touch_event_supported": false,
  "native_fn_integrity_ok": true,
  "storage_available": true,
  "visibility": "visible"
}
```

All values are coarse/bucketed. No unique fingerprint hash is computed.

### B.3 Behaviour payload (`behaviour`)

```json
{
  "mouse": {
    "points": [[x, y, t_ms], "..."],
    "clicks": [[x, y, down_ms, up_ms], "..."],
    "untrusted_count": 0,
    "wheel_events": 3
  },
  "keys": {
    "events": [["letter", down_ms, up_ms], "..."],
    "paste_events": 0,
    "autofill_suspected": false
  },
  "touch": {
    "gestures": [{"type": "swipe", "points": [[x, y, t_ms, pressure, size], "..."]}]
  },
  "timing": {
    "ms_since_load": 8450,
    "ms_to_first_interaction": 1320,
    "ms_since_nonce": 7900,
    "scroll_events": 4,
    "focus_changes": 2
  },
  "device_class": "desktop"
}
```

Limits: at most 600 mouse points, 300 key events, 20 gestures with 100 points each. Key classes only: `letter | digit | space | punct | modifier | enter | backspace | other`.

### B.4 Responses and token

`POST /v1/assess` request:

```json
{ "nonce": "...", "action": "otp_request", "sdk_version": "1.0.0", "schema_version": 1,
  "client_ts": 1760000000000, "env": { }, "behaviour": { } }
```

Response:

```json
{ "decision": "allow", "band": "low", "token": "eyJ...", "challenge": null,
  "request_id": "uuid", "model_versions": {"mouse": "lgbm-1.0.0", "keyboard": "lgbm-1.0.0", "fusion": "1.0.0"},
  "degraded": false }
```

`decision` is one of `allow`, `challenge`, `deny`. When `challenge`, `challenge` contains `{ "id": "...", "type": "press_hold", "hold_ms": 1100, "expires_in": 60 }` and `token` is null.

Token claims: `iss`, `aud`, `act` (action), `iat`, `exp`, `jti`, `band`.

### B.5 Database schema

```sql
CREATE TABLE assessments (
  id UUID PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_hash TEXT NOT NULL,
  action TEXT NOT NULL,
  device_class TEXT,
  score REAL NOT NULL,
  band TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('allow','challenge','deny')),
  rules_fired TEXT[] NOT NULL DEFAULT '{}',
  top_factors JSONB NOT NULL DEFAULT '[]',
  model_versions JSONB NOT NULL,
  latency_ms REAL,
  degraded BOOLEAN NOT NULL DEFAULT FALSE,
  feedback TEXT CHECK (feedback IN ('fp','fn')),
  features JSONB,                    -- derived features only; optional; TTL-limited
  features_expires_at TIMESTAMPTZ
);
CREATE INDEX assessments_ts_idx ON assessments (ts);
CREATE INDEX assessments_decision_ts_idx ON assessments (decision, ts);

CREATE TABLE challenges (
  id UUID PRIMARY KEY,
  assessment_id UUID REFERENCES assessments(id),
  type TEXT NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  outcome TEXT
);
```

---

## Appendix C — Config files

### C.1 `backend/config/policy.yaml`

```yaml
# Thresholds are placeholders. Choose final values from validation data
# (Appendix E) and record the choice in docs/decision_log.md.
action_classes:
  low:    { allow_below: 0.50, deny_at_or_above: 0.90 }   # read-only pages
  medium: { allow_below: 0.30, deny_at_or_above: 0.80 }   # login, search
  high:   { allow_below: 0.15, deny_at_or_above: 0.70 }   # OTP request, updates
actions:
  page_view: low
  centre_search: medium
  login: medium
  otp_request: high
  details_update: high
fail_safe:
  redis_down: deny_high_allow_low
  model_error: rules_only
  db_down: continue_and_buffer
band_cutoffs: { low: 0.30, medium: 0.70 }   # for client-visible bands
```

### C.2 `backend/config/rules.yaml`

```yaml
rules:
  R02_WEBDRIVER:        { weight: 0.60, enabled: true }
  R03_UA_PLATFORM_MISMATCH: { weight: 0.30, enabled: true }
  R04_UA_HINTS_MISMATCH:    { weight: 0.30, enabled: true }
  R05_TZ_LANG_MISMATCH:     { weight: 0.10, enabled: true }
  R06_SOFTWARE_RENDERER:    { weight: 0.15, enabled: true }
  R07_ZERO_PLUGINS_DESKTOP: { weight: 0.10, enabled: true }
  R08_VIEWPORT_ANOMALY:     { weight: 0.30, enabled: true }
  R09_TOUCH_INCONSISTENT:   { weight: 0.10, enabled: true }
  R10_NATIVE_FUNCTION_TAMPER: { weight: 0.30, enabled: true }
  R11_UNTRUSTED_EVENTS:     { weight: 0.60, enabled: true }
  R12_TOO_FAST:             { weight: 0.30, enabled: true }
combine: noisy_or            # rule_score = 1 - prod(1 - weight_i for fired rules)
final_score: max_of_model_and_rules   # decision documented and ablated in Phase 10
```

### C.3 `ml/configs/train.yaml` (example)

```yaml
seed: 42
mouse:
  train_datasets: [web_bot_detection]          # add delbot_mouse if obtained
  external_test_datasets: [ieee_blog_bots]
  human_only_stress_test: [captchasolve30k]
  window_s: 10
  hop_s: 5
  features_config: configs/mouse_features.yaml
  include_shortcut_features: false
  cv: { type: grouped_kfold, n_splits: 5 }
  model: { family: lightgbm, search: optuna, n_trials: 50 }
  calibration: { method: isotonic, holdout_fraction: 0.15 }
keyboard:
  datasets: [aalto_keystrokes]
  max_participants: 1000
  synthetic_generators: [K1_constant, K2_uniform, K4_burst]   # K3_mimic held out
  held_out_generator: K3_mimic
  bot_prevalence_eval: [0.01, 0.05, 0.20]
```

---

## Appendix D — Synthetic bot generator specifications

All generators take `seed` and parameters. Parameters that mimic humans (means, standard deviations) are fitted on **training-split humans only**. Each synthetic session stores `bot_type` and its parameters.

### D.1 Keyboard bots (`synthetic/keyboard.py`)

| Id | Name | Behaviour |
|----|------|-----------|
| K1 | constant | Fixed dwell and flight (for example 90 ms and 120 ms) with at most 1-2 ms jitter |
| K2 | uniform | Dwell and flight drawn independently from uniform ranges (for example 40-160 ms and 50-300 ms) |
| K3 | mimic | Dwell and flight drawn from log-normal distributions fitted to the training humans' population mean and spread, independently per key (no autocorrelation structure). **Held out from training.** |
| K4 | burst | Pasted/injected input: all keys within a few milliseconds, optionally with a single long pause |

Per-session length sampled from the human length distribution. Also produce "slow bot" variants (for example K1 with 200 ms flights) to avoid the trivial rule "bots are fast".

### D.2 Touch bots (`synthetic/touch.py`)

| Id | Name | Behaviour |
|----|------|-----------|
| T1 | linear | Straight swipe, constant speed, constant pressure/size, regular sampling |
| T2 | bezier | Cubic Bezier with ease-in/out and small positional noise; pressure constant or slightly noisy |
| T3 | replay-perturb | A real training-set human gesture with small random time-scaling and offset. **Held out from training**; note that it is close to human data by construction, so report results carefully |
| T4 | tap-bot | Taps at fixed intervals with fixed dwell and identical positions |

### D.3 Human-like mouse path for the simulator (`simulator/humanlike.py`)

Used only to exercise the live system. Cubic Bezier between start and target with random control points, ease-in/ease-out time warping (smoothstep), Gaussian positional jitter of about 1-2 px, small end-of-path corrections, randomised pauses. Parameters randomised per run.

```python
import numpy as np

def bezier_path(p0, p3, n=60, jitter=1.5, rng=None):
    rng = rng or np.random.default_rng()
    p0, p3 = np.array(p0, float), np.array(p3, float)
    d = p3 - p0
    p1 = p0 + d * rng.uniform(0.2, 0.4) + rng.normal(0, 30, 2)
    p2 = p0 + d * rng.uniform(0.6, 0.8) + rng.normal(0, 30, 2)
    t = np.linspace(0, 1, n)
    t = t * t * (3 - 2 * t)                       # smoothstep easing
    t = t[:, None]
    pts = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3
    return pts + rng.normal(0, jitter, pts.shape)
```

---

## Appendix E — Evaluation protocol

### E.1 Splitting

- `split_group` = `subject_id` for humans; `generator_run_id` for bots. All segments from one group stay together.
- Hold-out structure (mouse):
  1. **In-distribution:** grouped train/validation/calibration/test (for example 60/10/10/20 by group) on Bournemouth.
  2. **Cross-phase:** train on Bournemouth part 1, test on part 2, and the reverse.
  3. **Cross-dataset:** train on Bournemouth (plus DELBOT if obtained), test on the IEEE blog dataset. The IEEE test set is small: report CIs and group counts.
  4. **Leave-one-bot-type-out:** train without one bot class (Bournemouth moderate/advanced; IEEE mimic/fallible), test on it.
  5. **Human FPR stress test:** apply the final model to CaptchaSolve30k (human-only) and report the flagged share by game type. This set is never used for training.
- Hold-out structure (keyboard): participant-grouped splits on Aalto samples; held-out generator K3; optional second human source for FPR.
- Hold-out structure (touch, Path A only): user-grouped splits; held-out generator T3.
- Thresholds are selected on the validation split only. The test split is used once for reporting.

### E.2 Metrics

ROC-AUC; PR-AUC; recall (bot detection rate) at 1% and 5% human false-positive rate; Equal Error Rate; confusion matrix at the chosen threshold; Brier score and reliability curve (calibration); for session-level results, also the share of **human sessions that would be challenged** under the policy bands.

### E.3 Uncertainty

Bootstrap by group (at least 1,000 resamples; seeded) for 95% confidence intervals on every headline metric. Report the number of groups in each test split.

### E.4 Prevalence

Report PR-AUC and precision at operating points under bot prevalence of 1%, 5% and 20% (reweighting or resampling the test set).

### E.5 Required result tables (save as CSV and Markdown in `results/`)

1. Dataset summary (counts per dataset, label, bot type).
2. Baseline comparison per modality (majority, LR, RF, LightGBM).
3. Cross-dataset results (rows: held-out dataset; columns: metrics with CIs).
4. Held-out bot type / generator results.
5. Feature-group ablation and shortcut-feature ablation.
6. Fusion comparison on pseudo-sessions (mouse only, keyboard only, average, noisy-OR, stacker) — labelled as simulated pairing.
7. Threshold trade-off: human challenge rate vs bot pass-through.
8. System results: simulator outcomes per tier, latency percentiles, load-test summary.

### E.5.1 Required figures

ROC and PR curves; reliability diagram; SHAP summary; example trajectories (human vs bot types); ablation bar chart; threshold trade-off curve; latency histogram.

### E.6 Failure analysis

For each modality, list the 10 highest-scoring humans (false positives) and 10 lowest-scoring bots (false negatives) with their key features and a short written explanation. Save as `results/<modality>/failure_analysis.md`.

### E.7 Honesty checklist (must be included in the final report)

- Results are on public benchmarks; no live human validation was done.
- Keyboard and touch bot classes are synthetic.
- Fusion was evaluated on simulated pseudo-sessions.
- Performance may differ on other sites, devices and bot generators.
- Client-side signals can be spoofed; the system raises cost, it does not guarantee prevention.

---


## Appendix F — Templates

### F.1 `PROGRESS.md`

```markdown
# Progress

**Current phase:** 0  |  **Branch:** main  |  **Last updated:** YYYY-MM-DD  |  **Last agent/tool:** (name)

## Task table
| ID | Phase | Task (short) | Status | Commit | Notes |
|----|-------|--------------|--------|--------|-------|
| P0-01 | 0 | Repo skeleton and ignore files | TODO | | |
| P0-02 | 0 | AGENTS/HANDOFF/PROGRESS files, split plan | TODO | | |
| ... | | (one row per task ID P0-01 ... P10-xx taken from docs/MASTER_PLAN.md) | | | |

Status values: TODO, IN_PROGRESS, BLOCKED, DONE, SKIPPED (with reason in Notes).

## Blockers
- (none)

## Human checkpoints pending
- (none)

## Results index (files under results/)
- (none yet)
```

### F.2 `HANDOFF.md` (rewritten at every task boundary; keep under 60 lines)

```markdown
# Handoff

**Updated:** YYYY-MM-DD HH:MM  |  **By:** (tool name)  |  **Branch:** phase-N-name  |  **Last commit:** <hash>

## Current task
- ID: P2-04 — <short description>
- State: not started | in progress | blocked | needs tests | done (then point to next task)

## Done in this task so far
- (bullets, with file paths)

## Exact next step
- (one concrete action, command or function to write)

## Files touched (uncommitted or recently changed)
- path — what changed

## Commands to run first
    python scripts/tasks.py test-fast
    (any task-specific command)

## Known problems / gotchas
- (bugs, flaky tests, dataset quirks, decisions pending)

## Dataset / long-job state
- (which shards exist, which job was running, how to resume it)

## Questions for the human (if BLOCKED)
- Question — option A — option B
```

### F.3 Dataset card (`docs/datasets/<key>.md`)

```markdown
# Dataset card: <name>
- Source URL / DOI:
- Local folder (relative to datasets root):
- Access date:
- Licence / terms (copy the key points):
- Citation:
- Modality and labels (human / bot types):
- Contents (users, sessions, sizes):
- File formats as OBSERVED (not assumed):
- Time units and sampling rate:
- Coordinate space and screen information:
- Known quirks / issues:
- Loader module and version:
- Canonical output shards:
- Used for: (train / validate / cross-dataset test / human-FPR stress test)
- Memory/disk notes (how it is read safely):
```

### F.4 Resume prompts (the human pastes one into the next tool)

1. **Fresh start:** "Read AGENTS.md in the repository root. Run `python scripts/status.py`, read HANDOFF.md, then continue the current task. Follow the rules in AGENTS.md. Work in small steps and update PROGRESS.md and HANDOFF.md after every task."
2. **After a cut-off:** "The previous tool ran out of tokens. Read AGENTS.md, run `python scripts/status.py`, read HANDOFF.md, check `git status` and `git diff --stat`, run `python scripts/tasks.py test-fast`, then decide whether to keep or stash uncommitted changes (record the decision in HANDOFF.md) and continue the in-progress task."
3. **Start a phase:** "Read AGENTS.md and docs/plan/phase_N.md. Create branch phase-N-<name>. Start with the first TODO task of Phase N. Stop at any [HUMAN] task and ask me."
4. **Review before accepting results:** "Review the current results for leakage, dataset-fingerprint effects and unrealistically high scores before I accept them. Use the Pitfalls sections and Appendix E. Do not change code; write findings to docs/review_notes.md."
5. **Phase finished:** "Run the acceptance criteria of Phase N, list which pass or fail, summarise deviations from the plan, update PROGRESS.md and HANDOFF.md, and propose the next phase."

---

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

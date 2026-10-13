## Phase 1 — Dataset access, inventory and audit (mouse)

**Goal:** Turn the available mouse datasets into the canonical format safely (large files, Windows paths) and understand them before modelling.

**Mouse sources:** Bournemouth (primary), IEEE blog bots (external), CaptchaSolve30k (human-only stress test), DELBOT-Mouse (optional). BeCAPTCHA-Mouse is unavailable.

### Tasks

- [ ] **P1-01** Implement `scripts/inventory.py` (Appendix G.5): for a dataset key, print a shallow tree (depth 2), file counts and sizes by extension, and the first few lines (max 300 characters each) of up to 3 small text files. It must never open a file over 200 MB beyond its first 50 KB. Save outputs to `docs/datasets/inventory_<key>.txt`.
- [ ] **P1-02** Run the inventory for `web_bot_detection`, `ieee_blog_bots`, `captchasolve30k`. Read each dataset's own README (Bournemouth `README`, IEEE `readme.md`) and write `docs/datasets/<key>.md` (card template, Appendix F.3): file formats actually observed, label definitions, session counts, timestamps' units and sampling rate, coordinate space, known quirks, licence/terms. **Do not guess formats.**
- [ ] **P1-03** Implement `loaders/web_bot_detection.py` producing canonical `mouse_events` shards (Section 4.1). Keep `part` (1 or 2) as `domain` sub-label (`wiki_part1`, `wiki_part2`). `subject_id` = human participant/session id for humans and generator + run id for bots. Support `--max-sessions`. Unit tests with a tiny fixture that mimics the observed format.
- [x] **P1-04** Implement `loaders/ieee_blog_bots.py` (canonical shards; `bot_type` in `human, naive, humanish, mimic, fallible`; keep clicks and scroll events as event types). Unit tests with a fixture.
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

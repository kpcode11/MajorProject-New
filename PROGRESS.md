# Progress

**Current phase:** 2  |  **Branch:** phase-2-mouse-model  |  **Last updated:** 2026-10-13  |  **Last agent/tool:** Cursor

## Task table

| ID | Phase | Task (short) | Status | Commit | Notes |
|----|-------|--------------|--------|--------|-------|
| P0-01 | 0 | Repo skeleton and ignore files | DONE | 138dbc9 | Python stubs compile. |
| P0-02 | 0 | Agent records, plan split, pointers | DONE | b59792d | Split-plan output validated. |
| P0-03 | 0 | Human environment and dataset config | DONE | d63224c | Environment recorded; local config ignored by Git. |
| P0-04 | 0 | Python package projects and dependencies | DONE | 0550595, adea826 | Installed and validated on Python 3.14.7. |
| P0-05 | 0 | Task runner and status script | DONE | 9534e33 | setup, lint, test, test-fast, status, and placeholders validated. |
| P0-06 | 0 | Python CI workflow | DONE | 63a2c00 | Windows Python 3.14 workflow YAML validated locally. |
| P0-07 | 0 | README and phase-1 branch | DONE | 015cc73 | Phase 0 commands pass; Phase 1 branch created. |
| P1-01 | 1 | Safe dataset inventory | DONE | a6a0bfa | Bounded report saved for Bournemouth; fast tests pass. |
| P1-02 | 1 | Dataset inventory cards | DONE | 31e0ecc | Cards use only locally observed formats and documentation. |
| P1-03 | 1 | Web bot-detection loader | DONE | 94d15f4 | Streams both observed phase formats; parser and smoke conversion pass. |
| P1-04 | 1 | IEEE blog-bots loader | DONE | c8c43c9 | Streams train/test sessions, preserves move/click/scroll events, and passes fixture and real-data smoke tests. |
| P1-05 | 1 | CaptchaSolve30k loader | DONE | 6aeab38 | Streams JSONL sessions, prefers observed tickInputs, includes the 9-byte decoder, and passes fixture and real-session smoke tests. |
| P1-06 | 1 | Windowing | DONE | d0a28c7 | Adds 10-second/5-second overlapping windows, exact duplicate removal, sorting, and minimum move filtering. |
| P1-07 | 1 | DELBOT acquisition and loader | DONE | 72bef69 | Shallow clone succeeded; archive inspected and streamed directly with two bounded samples extracted for inspection. |
| P1-08 | 1 | Dataset availability decisions | DONE | pending | Recorded unavailable BeCAPTCHA/CMU, repo-only UL-Keystroke, and obtained DELBOT outcomes. |
| P1-09 | 1 | Mouse data audit | DONE | a4a3bd5 | Adds incremental Parquet audits with JSON/Markdown reports and focused coverage. |
| P1-10 | 1 | Mouse exploratory analysis | DONE | 44974f9 | Adds bounded trajectory, speed, and sampling-interval figures per canonical dataset. |
| P1-11 | 1 | Dataset-fingerprint test | DONE | 20af833 | Adds human-only scale-invariant pairwise classification; current report honestly records insufficient data. |
| P1-12 | 1 | Data manifest | DONE | 40a70c6 | Records observed source files, metadata, licence notes, and full/first-1-MiB SHA-256 hashes. |
| P2-01 | 2 | Mouse trajectory segmentation | DONE | ad62ff1 | Pause and click/down/up splits; min_points and min_path_px filters; focused tests pass. |
| P2-02 | 2 | Mouse feature extraction | DONE | pending | Appendix A.2 segment features, window aggregation, hand-computed tests, and Hypothesis invariants. |
| P2-03 | 2 | Mouse feature shards | DONE | pending | Resumable canonical-Parquet feature shards, schema, metadata, and train-mouse CLI. |
| P2-04 | 2 | Leakage-safe split utilities | DONE | pending | Added grouped, cross-phase, cross-dataset, and leave-one-bot-type-out splits with group-isolation tests. |
| P2-05 | 2 | Mouse baselines | DONE | pending | Added majority, scaled Logistic Regression, Random Forest, and LightGBM on one grouped split with CSV output. |
| P2-06 | 2 | LightGBM optimisation | DONE | pending | Added time-boxed Optuna search with stratified grouped CV on training groups only and JSON output. |
| P2-07 | 2 | Session score aggregation | DONE | pending | Added mean, top-k mean, max, and learned logistic aggregation comparison on validation sessions. |
| P2-08 | 2 | Model calibration | DONE | pending | Added separate grouped calibration split with isotonic/Platt scaling, reliability data, and Brier scores. |
| P2-09 | 2 | Mouse evaluation | DONE | pending | Added Appendix E score evaluation, split modes, group bootstrap CIs, and human-FPR-by-game reporting. |
| P2-10 | 2 | Mouse ablations | DONE | pending | Added kinematics, geometry, timing, click, and shortcut-inclusive/exclusive ablations on one grouped split. |
| P2-11 | 2 | Mouse SHAP explanations | TODO | | |
| P2-12 | 2 | Mouse ONNX export | TODO | | |
| P2-13 | 2 | Mouse model-card section | TODO | | |
| P3-01 | 3 | Aalto inventory and card | TODO | | |
| P3-02 | 3 | Aalto keyboard loader | TODO | | |
| P3-03 | 3 | Keyboard privacy scan | TODO | | |
| P3-04 | 3 | Keyboard features | TODO | | |
| P3-05 | 3 | Synthetic keyboard bots | TODO | | |
| P3-06 | 3 | Keyboard feature shards | TODO | | |
| P3-07 | 3 | Keyboard evaluation | TODO | | |
| P3-08 | 3 | Optional second keyboard source | TODO | | |
| P3-09 | 3 | Keyboard ONNX export | TODO | | |
| P3-10 | 3 | Desktop fusion | TODO | | |
| P3-11 | 3 | Keyboard and fusion model card | TODO | | |
| P4-01 | 4 | Environment signal schema | TODO | | |
| P4-02 | 4 | Pure environment rules | TODO | | |
| P4-03 | 4 | Rule score | TODO | | |
| P4-04 | 4 | Configurable rule weights | TODO | | |
| P4-05 | 4 | Rule-layer tests | TODO | | |
| P4-06 | 4 | Signal privacy documentation | TODO | | |
| P4-07 | 4 | Optional BotD comparison | TODO | | |
| P5-01 | 5 | Settings and score store | TODO | | |
| P5-02 | 5 | API schemas and limits | TODO | | |
| P5-03 | 5 | Nonces | TODO | | |
| P5-04 | 5 | Model scoring | TODO | | |
| P5-05 | 5 | Risk policy | TODO | | |
| P5-06 | 5 | Human tokens | TODO | | |
| P5-07 | 5 | Rate limiting | TODO | | |
| P5-08 | 5 | Persistence and migrations | TODO | | |
| P5-09 | 5 | Scoring API endpoints | TODO | | |
| P5-10 | 5 | Protected-route dependency | TODO | | |
| P5-11 | 5 | Failure policy | TODO | | |
| P5-12 | 5 | Privacy-safe logging | TODO | | |
| P5-13 | 5 | Backend tests | TODO | | |
| P5-14 | 5 | Latency benchmark | TODO | | |
| P6-01 | 6 | SDK package and CI | TODO | | |
| P6-02 | 6 | Environment collector | TODO | | |
| P6-03 | 6 | Mouse collector | TODO | | |
| P6-04 | 6 | Keyboard collector | TODO | | |
| P6-05 | 6 | Scroll and timing collectors | TODO | | |
| P6-06 | 6 | SDK transport | TODO | | |
| P6-07 | 6 | SDK public API | TODO | | |
| P6-08 | 6 | SDK challenge UI | TODO | | |
| P6-09 | 6 | React SDK integration | TODO | | |
| P6-10 | 6 | SDK performance controls | TODO | | |
| P6-11 | 6 | SDK tests | TODO | | |
| P6-12 | 6 | SDK bundle report | TODO | | |
| P6-13 | 6 | SDK/backend contract test | TODO | | |
| P7-01 | 7 | Demo portal scaffold | TODO | | |
| P7-02 | 7 | Demo portal pages | TODO | | |
| P7-03 | 7 | Protected portal API | TODO | | |
| P7-04 | 7 | Portal API statistics | TODO | | |
| P7-05 | 7 | Protection-mode switch | TODO | | |
| P7-06 | 7 | Accessible step-up UI | TODO | | |
| P7-07 | 7 | Challenge flow | TODO | | |
| P7-08 | 7 | Challenge rate limits | TODO | | |
| P7-09 | 7 | Challenge accessibility | TODO | | |
| P7-10 | 7 | Challenge tests | TODO | | |
| P7-11 | 7 | Simulator local-host safety | TODO | | |
| P7-12 | 7 | Simulator tier 1 | TODO | | |
| P7-13 | 7 | Simulator tier 2 | TODO | | |
| P7-14 | 7 | Simulator tier 3 | TODO | | |
| P7-15 | 7 | Simulator tier 4 | TODO | | |
| P7-16 | 7 | Simulator batch runner | TODO | | |
| P7-17 | 7 | Human-like reference run | TODO | | |
| P7-18 | 7 | Portal end-to-end tests | TODO | | |
| P7-19 | 7 | Demo startup command | TODO | | |
| P7-20 | 7 | Demo script | TODO | | |
| P7-21 | 7 | Simulator summary | TODO | | |
| P8-01 | 8 | Human touch-data decision | TODO | | |
| P8-02A | 8 | Touch dataset inventory | TODO | | |
| P8-03A | 8 | Touch data loader | TODO | | |
| P8-04A | 8 | Touch features | TODO | | |
| P8-05A | 8 | Synthetic touch bots | TODO | | |
| P8-06A | 8 | Touch model evaluation | TODO | | |
| P8-07A | 8 | Touch fusion | TODO | | |
| P8-08A | 8 | Touch scoring integration | TODO | | |
| P8-09A | 8 | Touch model card | TODO | | |
| P8-02B | 8 | Touch collector without model | TODO | | |
| P8-03B | 8 | Touch logging integration | TODO | | |
| P8-04B | 8 | No-touch-model policy | TODO | | |
| P8-05B | 8 | Touch missing-modality fairness | TODO | | |
| P8-06B | 8 | Mobile step-up UI | TODO | | |
| P8-07B | 8 | Mobile simulator | TODO | | |
| P8-08B | 8 | Mobile limitation documentation | TODO | | |
| P9-01 | 9 | Admin API | TODO | | |
| P9-02 | 9 | Admin dashboard | TODO | | |
| P9-03 | 9 | Dashboard tests | TODO | | |
| P9-04 | 9 | Retention purge | TODO | | |
| P9-05 | 9 | Rotating session identifiers | TODO | | |
| P9-06 | 9 | Privacy regression scan | TODO | | |
| P9-07 | 9 | Privacy impact assessment | TODO | | |
| P9-08 | 9 | Optional local feature extraction | TODO | | |
| P9-09 | 9 | Accessibility audit | TODO | | |
| P9-10 | 9 | Keyboard-only portal test | TODO | | |
| P9-11 | 9 | Human screen-reader check | TODO | | |
| P9-12 | 9 | Missing-modality E2E test | TODO | | |
| P9-13 | 9 | Accessibility limitations | TODO | | |
| P9-14 | 9 | Optional trajectory neural model | TODO | | |
| P9-15 | 9 | Neural-model fusion | TODO | | |
| P10-01 | 10 | Reproducible full evaluation | TODO | | |
| P10-02 | 10 | Final experiments | TODO | | |
| P10-03 | 10 | System-level results | TODO | | |
| P10-04 | 10 | Load testing | TODO | | |
| P10-05 | 10 | Security checks | TODO | | |
| P10-06 | 10 | Final model card | TODO | | |
| P10-07 | 10 | Final technical documentation | TODO | | |
| P10-08 | 10 | Final README | TODO | | |
| P10-09 | 10 | Claims checker | TODO | | |
| P10-10 | 10 | Demo-video script | TODO | | |
| P10-11 | 10 | Release metadata | TODO | | |

Status values: TODO, IN_PROGRESS, BLOCKED, DONE, SKIPPED (with reason in Notes).

## Blockers

- P0-03 — human development-environment details are required before dependency setup.

## Human checkpoints pending

- P0-03 — provide environment details and permission/status for `git clone`.
- P8-01 — decide whether a public touch dataset can be obtained.

## Results index (files under results/)

- (none yet)

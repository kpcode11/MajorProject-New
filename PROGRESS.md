# Progress

**Current phase:** 10  |  **Branch:** main  |  **Last updated:** 2026-11-23  |  **Last agent/tool:** Copilot

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
| P2-10 | 2 | Mouse ablations | DONE | b132069 | Added kinematics, geometry, timing, click, and shortcut-inclusive/exclusive ablations on one grouped split. |
| P2-11 | 2 | Mouse SHAP explanations | DONE | e8e7ef2 | Added LightGBM SHAP summary and top-contributor reports per scored window. |
| P2-12 | 2 | Mouse ONNX export | DONE | ac133fe | Added LightGBM ONNX export, metadata, CLI stage, and native-vs-ONNX parity test. |
| P2-13 | 2 | Mouse model-card section | DONE | 2c59e4c | Documented model scope, inputs, evaluation status, limitations, privacy, and deployment boundaries. |
| P3-01 | 3 | Aalto inventory and card | DONE | b1f2b28 | Corrected full inventory counts and documented Aalto format, terms, size, and participant-streaming access. |
| P3-02 | 3 | Aalto keyboard loader | DONE | f6e6db5 | Added seeded participant streaming, sentence windows, privacy-safe key classes, Parquet shards, malformed counts, and resumable state. |
| P3-03 | 3 | Keyboard privacy scan | DONE | 4b8342d | Added Parquet-wide prohibited-column scan, CLI/task integration, fixture rejection tests, and real-shard validation. |
| P3-04 | 3 | Keyboard features | DONE | 85c7e5b | Added text-agnostic Appendix A.3 timing, variability, burst, pause, autocorrelation, and integrity features with tests. |
| P3-05 | 3 | Synthetic keyboard bots | DONE | e7006fa | Added deterministic K1 constant, K2 uniform, K3 training-human-fitted mimic, and K4 burst generators with tests. |
| P3-06 | 3 | Keyboard feature shards | DONE | d748e0a | Added human and configurable K1/K2/K4 feature shards with participant/generator split groups and K3 holdout enforcement. |
| P3-07 | 3 | Keyboard evaluation | DONE | 695a6a8 | Added grouped keyboard evaluation with K3 holdout, per-generator reports, speed terciles, human FPR, and bootstrap CIs. |
| P3-08 | 3 | Optional second keyboard source | DONE | fdad7d8 | No usable BB-MAS or UL repository data is configured; recorded the single-human-source limitation without adding an unsupported loader. |
| P3-09 | 3 | Keyboard ONNX export | DONE | fde90e8 | Added Logistic Regression ONNX export, metadata, CLI stage, explicit skl2onnx dependency, and native-vs-ONNX parity tests. |
| P3-10 | 3 | Desktop fusion | DONE | 5884937 | Added deterministic same-class pseudo-session pairing, missing-modality-safe fusion rules, validation stacker, result labels, metadata writer, and tests. |
| P3-11 | 3 | Keyboard and fusion model card | DONE | 0ae687d | Documented keyboard scope, privacy boundaries, single-human-source limitation, synthetic bots, pseudo-session fusion, and missing-modality policy. |
| P4-01 | 4 | Environment signal schema | DONE | 8d8b575 | 26-field EnvSignals Pydantic model from Appendix B.2; all optional; no fingerprint hash; 16 tests. |
| P4-02 | 4 | Pure environment rules | DONE | 7f1ac74 | Implemented RuleResult and pure rule functions R01-R13, evaluate_all_rules, and 62 unit tests. |
| P4-03 | 4 | Rule score | DONE | c91ab3b | Added noisy-OR rule scoring, fired-rule reasons, hard-rule detection for R13/invalid nonce or signature, and model-bypass tests. |
| P4-04 | 4 | Configurable rule weights | DONE | 9ddd713 | Added validated YAML loading for enabled flags and weights, with disabled-rule handling in combined evaluation. |
| P4-05 | 4 | Rule-layer tests | DONE | d3195de | Added aggregate normal Chrome and headless-browser fixture assertions, including rule score and fired-rule expectations. |
| P4-06 | 4 | Signal privacy documentation | DONE | pending | Added the complete signal privacy register, prohibited-data boundary, retention guidance, and fixture coverage summary. |
| P4-07 | 4 | Optional BotD comparison | DONE | pending | Deferred by decision: no pinned offline BotD artifact or approved adapter is present; no runtime dependency added. |
| P5-01 | 5 | Settings and score store | DONE | b8ffaae | |
| P5-02 | 5 | API schemas and limits | DONE | 3bdbfd7 | |
| P5-03 | 5 | Nonces | DONE | 55f1fc0 | |
| P5-04 | 5 | Model scoring | DONE | pending | Startup ONNX loading with metadata checks, botguard_ml.features extraction, calibration, fusion, rule combination, top-3 attribution, and 27 tests. |
| P5-05 | 5 | Risk policy | DONE | ddc4dab | |
| P5-06 | 5 | Human tokens | DONE | pending | JWT issuance and verification (HS256, RS256, ES256) with single-use JTI tracking and 11 tests. |
| P5-07 | 5 | Rate limiting | DONE | pending | Sliding-window rate limiting per IP bucket, session ID, and endpoint (/v1/nonce, /v1/assess, /v1/assess/challenge) with tests. |
| P5-08 | 5 | Persistence and migrations | DONE | pending | SQLAlchemy 2.0 assessments/challenges models, migration, optional TTL feature storage, raw-trace guard, and DB-down write buffer with tests. |
| P5-09 | 5 | Scoring API endpoints | DONE | pending | FastAPI /v1/nonce, /v1/assess, /v1/assess/challenge, /v1/token/verify, /v1/health with 64 KB body cap and OpenAPI docs. |
| P5-10 | 5 | Protected-route dependency | DONE | pending | require_human_token(action) dependency verifying signature, exp, act, and single-use jti. |
| P5-11 | 5 | Failure policy | DONE | pending | Degraded-mode policy for Redis/Store outage, ONNX model error, and DB write buffering documented in docs/architecture.md. |
| P5-12 | 5 | Privacy-safe logging | DONE | pending | Structured JSON logging with /24 and /48 IP coarsening and redaction of raw traces/payloads. |
| P5-13 | 5 | Backend tests | DONE | pending | Comprehensive API, security, replay, fail-safe, oversize payload, rate-limit, and logging tests in backend/tests/test_api.py. |
| P5-14 | 5 | Latency benchmark | DONE | pending | 1,000-call micro-benchmark in backend/bench_scoring.py (p50=1.65 ms, p95=15.16 ms < 200 ms) saved to results/system/scoring_latency.json. |
| P6-01 | 6 | SDK package and CI | DONE | 9f0c704 | Vite 8 + TS 6 strict + vitest 5 (happy-dom) + ESLint 10 + Prettier; config.ts with contract hard limits; CI sdk job; tasks.py lint/test/setup run SDK scripts. |
| P6-02 | 6 | Environment collector | DONE | d1f02a4 | Appendix B.2 coarse environment snapshot, bucketing helpers, UA/WebGL classification, native integrity check, deviceClass, and 20 unit tests. |
| P6-03 | 6 | Mouse collector | DONE | 8b92328 | Passive throttled mousemove/down/up/click/wheel listeners, bounded RingBuffer, windowed snapshot matching backend MouseBehaviour, untrusted events counted not stored; 8 tests. |
| P6-04 | 6 | Keyboard collector | DONE | 115c28f | Key class only (mapped in keyClass, identity never stored; class-FIFO pairing), auto-repeat ignored, paste count, autofill flag for text fields, untrusted count; backend KeyBehaviour gains untrusted_count so R11 sees it; 23 SDK tests incl. typed-string privacy test. |
| P6-05 | 6 | Scroll and timing collectors | DONE | 714e96c | ScrollCollector (passive capture scroll counter) and TimingCollector (ms_since_load, ms_to_first_interaction, ms_since_nonce, scroll_events, focus_changes via focus/blur/visibilitychange); 5 unit tests. |
| P6-06 | 6 | SDK transport | DONE | 044bd2c | Nonce fetch, 64 KB-bounded payload builders, POST /v1/assess and /v1/assess/challenge with AbortController timeouts, exponential backoff retries, and non-throwing safeAssess/safeSubmitChallenge; 10 tests. |
| P6-07 | 6 | SDK public API | DONE | b7676cb | BotGuardClient class and BotGuard singleton (start, assess, runChallenge, stop, setChallengeHandler, prefetchNonce) with idempotent lifecycle and requestIdleCallback snapshot scheduling; 5 tests. |
| P6-08 | 6 | SDK challenge UI | DONE | 6c46c30 | Pluggable step-up challenge UI (renderPressHoldChallenge, createChallengeHandler, defaultPressHoldRenderer) with accessible dialog, mouse/touch/keyboard hold, single-press keyboard alternative, and custom renderer support; 5 tests. |
| P6-09 | 6 | React SDK integration | DONE | 1417f3f | BotGuardProvider and useBotGuard() hook in @botguard/sdk/react with auto-start/stop lifecycle, assess, runChallenge, and assessWithStepUp; 3 React 19 tests. |
| P6-10 | 6 | SDK performance controls | DONE | 30a8a73 | Passive listener enforcement, throttle gate, scheduleIdleTask with timeout fallback, bounded ring buffers, and zero-listener-leak stop() cleanup; 4 stress/performance tests. |
| P6-11 | 6 | SDK tests | DONE | b03e6c3 | 98 vitest + happy-dom tests across 11 suites: bounded collectors, form/typed-string privacy guarantees, throttling, <64 KB stress test, and window/document stop() listener cleanup. |
| P6-12 | 6 | SDK bundle report | DONE | 0ae5bef | ES module (10.90 KB gzip), UMD (10.05 KB gzip), and React wrapper (1.02 KB gzip) built and reported in results/system/sdk_size.json (< 30 KB target). |
| P6-13 | 6 | SDK/backend contract test | DONE | c667d49 | Exported backend Pydantic JSON Schema (data/fixtures/backend_contract_schema.json) and validated live SDK AssessRequest and ChallengeAssessRequest payloads in sdk/test/contract.test.ts and backend/tests/test_sdk_contract.py. |
| P7-01 | 7 | Demo portal scaffold | DONE | 556745c | React 19 + Vite 8 + TypeScript 6 portal scaffold in portal/ labelled 'DEMO — not a government portal', wrapped in BotGuardProvider, with CI job and unit test. |
| P7-02 | 7 | Demo portal pages | DONE | 47e287c | Landing, Resident login (identifier + Send OTP), Update details form, and Centre search pages in portal/src/pages/ with X-Human-Token forwarding and zero raw-text transmission; 4 unit tests. |
| P7-03 | 7 | Protected portal API | DONE | 1d9bd4a | Mounted /portal-api/otp/request, /portal-api/details/update, and /portal-api/centres/search via create_portal_router() in backend/app/portal.py protected by require_human_token; 3 tests in test_portal_api.py. |
| P7-04 | 7 | Portal API statistics | DONE | 4790ef6 | Added thread-safe PortalStatsTracker and GET /portal-api/stats reporting accepted vs rejected calls overall, per action, and per reason; 4 tests in test_portal_api.py. |
| P7-05 | 7 | Protection-mode switch | DONE | 5f02c1e | Added PROTECTION_MODE ('off' | 'passive', default 'passive') in backend/app/config.py, bypassed token requirement in require_human_token when 'off', and exposed protection_mode in /portal-api/stats; 5 tests in test_portal_api.py. |
| P7-06 | 7 | Accessible step-up UI | DONE | 5af2f3a | Accessible press-and-hold step-up dialog with server-chosen hold_ms (0.8-1.5 s), Space/Enter single-press keyboard alternative, focus ring/trap, and no image/text puzzles; verified in portal/test/app.test.tsx. |
| P7-07 | 7 | Challenge flow | DONE | 554c422 | POST /v1/assess challenge decision (id, type, hold_ms, expires_in) and POST /v1/assess/challenge re-scoring combining original_score + challenge interaction features to return allow/deny; verified in test_api.py. |
| P7-08 | 7 | Challenge rate limits | DONE | 97d96b7 | Per-session (RATE_LIMIT_CHALLENGE_SESSION_PER_MIN) and per-IP-bucket (RATE_LIMIT_CHALLENGE_PER_MIN) rate limits, single-use get_and_delete challenge_id, and CHALLENGE_TTL_SECONDS; verified in test_ratelimit.py and test_api.py. |
| P7-09 | 7 | Challenge accessibility | DONE | 06bbafc | Verified ARIA labels/roles, initial focus, Tab/Shift+Tab modal focus trap, focus restoration on close, visible :focus-visible outline, and keyboard Space/Enter single-press path without countdown pressure in sdk/test/challenge.test.ts. |
| P7-10 | 7 | Challenge tests | DONE | 20615d7 | Added backend/tests/test_challenge.py and sdk/test/challenge.test.ts covering challenge success, timeout expiration, replay rejection, too-fast completion deny, and wrong ID / context / action mismatch. |
| P7-11 | 7 | Simulator local-host safety | DONE | b65d5ae | Added simulator/allowlist.txt and simulator/safety.py (validate_target_url, load_allowlist, extract_host) refusing non-local and .gov/.nic.in/uidai hosts; 16 tests in test_simulator_safety.py. |
| P7-12 | 7 | Simulator tier 1 | DONE | 7b234d9 | Added simulator/tier1_http.py (run_tier1_session, SimRunResult, SimOutcome, DEFAULT_TIER1_USER_AGENTS) posting directly to /portal-api/* without browser or SDK token after local-host validation; 2 tests in test_simulator_tier1.py. |
| P7-13 | 7 | Simulator tier 2 | DONE | f5e438f | Added simulator/tier2_playwright.py (run_tier2_session, drive_tier2_playwright_page, build_tier2_env_signals, build_tier2_behaviour_payload, PlaywrightPageLike) performing default Playwright direct fills and clicks after local-host validation; 3 tests in test_simulator_tier2.py. |
| P7-14 | 7 | Simulator tier 3 | DONE | ea2e017 | Added simulator/tier3_stealth.py (run_tier3_session, drive_tier3_playwright_page, apply_tier3_context_adjustments, build_tier3_env_signals, build_tier3_behaviour_payload, TIER3_INIT_SCRIPT) testing rule & behavioural layers under basic stealth adjustments; 4 tests in test_simulator_tier3.py. |
| P7-15 | 7 | Simulator tier 4 | DONE | c7dd2aa | Added simulator/humanlike.py (bezier_path, generate_humanlike_mouse_trajectory, generate_humanlike_key_events) and simulator/tier4_humanlike.py (run_tier4_session, drive_tier4_playwright_page); 4 tests in test_simulator_tier4.py. |
| P7-16 | 7 | Simulator batch runner | DONE | e4a3ec3 | Added simulator/run_all.py (run_all_tiers, run_randomized_tier_session, summarize_sim_runs, write_sim_runs_jsonl) generating results/system/sim_runs.jsonl (200 sessions across Tiers 1-4 for off and passive modes); 2 tests in test_simulator_run_all.py. |
| P7-17 | 7 | Human-like reference run | DONE | e4b864c | Added simulator/reference_human.py (run_reference_human_session, REFERENCE_HUMAN_MOUSE_POINTS, DEMO_SCRIPT_DISCLAIMER) verifying multimodal and keyboard-only (Tab+Enter) sessions pass passive protection; 3 tests in test_simulator_reference_human.py. |
| P7-18 | 7 | Portal end-to-end tests | DONE | 0088803 | Added backend/tests/test_e2e_portal.py (5 E2E tests) and portal/test/e2e.test.tsx (4 E2E tests) covering normal interaction -> token -> OTP accepted, headless direct click -> denied/challenged, no token -> 401, keyboard-only Tab+Enter -> step-up pass, and off vs passive mode. |
| P7-19 | 7 | Demo startup command | DONE | 19a87b5 | Added demo() in scripts/tasks.py starting backend (STORE_BACKEND=memory, SQLite, 127.0.0.1:8000) and portal dev server (127.0.0.1:5173) plus deploy/docker-compose.yml (optional Redis + PostgreSQL infra profile); 2 tests in test_demo_task.py. |
| P7-20 | 7 | Demo script | DONE | 4a93ffb | Added docs/demo_script.md documenting python scripts/tasks.py demo, PROTECTION_MODE=off vs passive, /portal-api/stats, keyboard-only accessibility flow, and Tiers 1-4 simulator runs; verified in test_demo_task.py. |
| P7-21 | 7 | Simulator summary | DONE | 65895be | Added format_sim_summary_markdown and write_sim_summary_markdown in simulator/run_all.py and generated results/system/sim_summary.md with per-tier counts/rates and non-generalisation disclaimer; 3 tests in test_simulator_run_all.py. |
| P8-01 | 8 | Human touch-data decision | SKIPPED | | Skipped per human decision on 2026-11-14 to omit Phase 8 mobile touch dataset and ML model and proceed directly to Phase 9. |
| P8-02A | 8 | Touch dataset inventory | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-03A | 8 | Touch data loader | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-04A | 8 | Touch features | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-05A | 8 | Synthetic touch bots | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-06A | 8 | Touch model evaluation | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-07A | 8 | Touch fusion | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-08A | 8 | Touch scoring integration | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-09A | 8 | Touch model card | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-02B | 8 | Touch collector without model | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-03B | 8 | Touch logging integration | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-04B | 8 | No-touch-model policy | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-05B | 8 | Touch missing-modality fairness | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-06B | 8 | Mobile step-up UI | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-07B | 8 | Mobile simulator | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P8-08B | 8 | Mobile limitation documentation | SKIPPED | | Skipped per human decision on 2026-11-14 (Phase 8 omitted). |
| P9-01 | 9 | Admin API | DONE | c7073d9 | Added backend/app/admin.py (/admin/overview, /admin/scores, /admin/assessments, /admin/assessments/{id}, /admin/feedback, /admin/sim-results, /admin/privacy, /admin/privacy/purge) protected by ADMIN_API_KEY; 4 tests in test_admin_api.py. |
| P9-02 | 9 | Admin dashboard | DONE | affede1 | Added portal/src/pages/AdminDashboardPage.tsx, portal/src/adminApi.ts, portal/src/designTokens.ts (supabase/DESIGN.md tokens), portal/src/dashboard/RechartsCompat.tsx, and dashboard/ exports implementing all 6 admin dashboard views. |
| P9-03 | 9 | Dashboard tests | DONE | 143026b | Added portal/test/dashboard.test.tsx (overview, histogram thresholds, session derived features, simulator tiers, fp/fn feedback, privacy purge, portal-shell smoke) and backend/tests/test_dashboard_smoke.py (admin views load from ASGI backend). |
| P9-04 | 9 | Retention purge | DONE | 7f10bd9 | Implemented backend/app/retention.py (run_retention_purge, RetentionScheduler, FakeClock, CLI --once), wired RETENTION_PURGE_INTERVAL_SECONDS in config/main/admin, and added 6 unit tests in backend/tests/test_retention.py. |
| P9-05 | 9 | Rotating session identifiers | DONE | c965218 | Added random per-page-load rotating session IDs in SDK (generateSessionId, SESSION_ROTATION_MS, X-Session-Id header) and daily-rotated session hashes (daily_session_salt, make_session_hash) with coarse /24 and /48 IP logging in backend/app/nonce.py and backend/app/main.py; tested in backend/tests/test_session_privacy.py and sdk/test/api.test.ts. |
| P9-06 | 9 | Privacy regression scan | DONE | ee236bf | Added backend/tests/test_privacy_scan.py scanning all DB tables/columns/cells and structured log lines across E2E portal, step-up challenge, bot, and form-injection flows for typed characters, form values, full IPs, and persistent device IDs. |
| P9-07 | 9 | Privacy impact assessment | DONE | 39b397d | Wrote docs/privacy_impact.md covering all 7 signal groups (purpose, necessity, less-invasive alternatives, retention), prohibited-signal invariants, and explicit UIDAI/DPDP Act 2023 engineering assumptions and legal review caveats. |
| P9-08 | 9 | Optional local feature extraction | DONE | ffbf0e5 | Implemented SDK local feature extraction mode (sendRawTrace=false in sdk/src/features.ts, sdk/src/config.ts, sdk/src/index.ts), backend local-feature scoring (backend/app/schemas.py, backend/app/scoring.py), golden parity tests (1e-9 tolerance in sdk/test/features_parity.test.ts and backend/tests/test_local_features.py), and results/system/local_features_parity.json. |
| P9-09 | 9 | Accessibility audit | DONE | d3606f9 | Added axe-core and WCAG 2.1 AA contrast audit in portal/test/accessibility.test.tsx (11 states across Landing, Login, Update Details, Centre Search, Admin Dashboard, and Step-up Challenge dialog; 0 violations) and results/system/axe_audit.json; fixed button/text contrast, skip link, aria-invalid/aria-describedby form error associations, table scope="col", keyboard row selection, and WCAG 2.5.3 label-in-name attributes. |
| P9-10 | 9 | Keyboard-only portal test | DONE | d23a26f | Added portal/test/keyboard_e2e.test.tsx (3 keyboard-only E2E flows from Landing -> Login -> typing -> Enter submit -> step-up single-press / physical Spacebar hold / direct allow -> OTP accepted) and test_e2e_keyboard_only_login_otp_flow_with_tab_enter_and_stepup in backend/tests/test_e2e_portal.py. |
| P9-11 | 9 | Human screen-reader check | DONE | 1305d22 | Documented NVDA / Windows Narrator / VoiceOver smoke-test walkthrough and announcement checklist in docs/accessibility.md (with explicit methodology note) and added automated ARIA landmark/live-region/progressbar announcement smoke test in portal/test/accessibility.test.tsx. |
| P9-12 | 9 | Missing-modality E2E test | DONE | 4521b1e | Enforced missing-mouse valid-keyboard fairness cap (MISSING_MOUSE_VALID_KB_MAX_SCORE=0.50, MIN_TYPING_WINDOW_KEYS=10) in backend/app/scoring.py and added 6 E2E tests in backend/tests/test_missing_modality_e2e.py across otp_request, details_update, centre_search, short PIN, slow assistive typing, and sendRawTrace=false. |
| P9-13 | 9 | Accessibility limitations | DONE | e511f01 | Documented missing-modality fairness rules and 6 known accessibility limitations (no assistive-tech training cohort, voice dictation/virtual keyboards, step-up hold vs single-press trade-off, omitted mobile touch, English-only demo copy, and automated DOM vs live human study scope) in docs/accessibility.md. |
| P9-14 | 9 | Optional trajectory neural model | SKIPPED | | Skipped optional trajectory neural model upgrade per human decision on 2026-11-18 to proceed directly to Phase 10. |
| P9-15 | 9 | Neural-model fusion | SKIPPED | | Skipped optional trajectory neural model fusion per human decision on 2026-11-18 to proceed directly to Phase 10. |
| P10-01 | 10 | Reproducible full evaluation | DONE | 87f6b29 | Implemented scripts/eval_all.py and wired python scripts/tasks.py eval-all generating 78 CSV/Markdown tables and 7 PNG figures under results/ and syncing report-ready assets to docs/report_assets/ (manifest in results/eval_all_manifest.json and docs/report_assets/manifest.json); tested in ml/tests/test_eval_all.py. |
| P10-02 | 10 | Final experiments | DONE | 87f6b29 | Generated and verified all Appendix E final experiment tables and figures: dataset summary, baselines, in-dist/cross-phase/cross-dataset/LOBO mouse splits, per-generator/K3-holdout/speed-tercile keyboard splits, pseudo-session fusion & modality availability, feature-group/shortcut/rule-layer ablations, isotonic/Platt calibration, 1%/5%/20% bot prevalence reweighting, and policy challenge-band threshold trade-off curves. |
| P10-03 | 10 | System-level results | DONE | 7d8b3c6 | Added scripts/system_results.py (wired into eval_all.py) generating results/system/sim_summary.csv and results/system/system_results.{json,csv,md} (plus docs/report_assets/table8_system_results.{csv,md}) consolidating simulator tier outcomes, per-tier latency distributions, ONNX+rule scoring latency percentiles, throughput (325.58 req/s), SDK gzip sizes, and axe-core audit counts; tested in backend/tests/test_system_results.py. |
| P10-04 | 10 | Load testing | DONE | 7b7e3e2 | Added loadtest/runner.py (wired to python scripts/tasks.py loadtest), loadtest/locustfile.py, and loadtest/k6_scenarios.js running all 4 scenarios (normal_mix, protected_endpoint_flood, nonce_flood, malformed_assess_flood; 630 requests @ 1155.42 req/s, 0 5xx errors, 0/460 malicious requests reached protected API) and saving results/system/loadtest_summary.{json,csv,md} and docs/report_assets/table8_loadtest_summary.{csv,md}; 3 tests in backend/tests/test_loadtest.py. |
| P10-05 | 10 | Security checks | DONE | bb11e68 | Ran 72-test security suite (nonce/JWT replay, tamper, oversize, rate-limit, privacy), bandit SAST on backend/app (remediated B101 asserts in tokens.py; 0 findings post-remediation), pip-audit, and npm audit (0 production runtime vulnerabilities); saved results/system/security_checks.{json,md} via scripts/security_checks.py and tested in backend/tests/test_security_checks.py. |
| P10-06 | 10 | Final model card | DONE | HEAD | Finalised docs/model_card.md with intended/prohibited uses, dataset availability disclosure (including unavailable BeCAPTCHA-Mouse/CMU and skipped Phase 8 touch), mouse/keyboard/fusion metrics with 95% CIs, prevalence/threshold trade-offs, system latency/parity results, fairness/accessibility notes, Appendix E.7 honesty checklist, and no-auto-training update/governance policy. |
| P10-07 | 10 | Final technical documentation | DONE | HEAD | Finalised docs/architecture.md (updated feature counts, R01-R13, policy.yaml fail-safe, local feature extraction, retention, missing-modality fairness), docs/api.md (accurate /v1/*, /portal-api/*, and /admin/* schemas and error codes), docs/signals.md (Phase 9 rotating session IDs and local features), and created docs/threat_model.md. |
| P10-08 | 10 | Final README | DONE | HEAD | Finalised README.md with updated Mermaid architecture diagram, 7-component repo layout (31 keyboard features, simulator/, loadtest/, sendRawTrace=false), dataset acquisition & unavailable/skipped disclosures, end-to-end system/load/security benchmarks, quickstart (setup/demo/eval-all/loadtest), Appendix E.7 honesty checklist, documentation index, and dataset citations/licences. |
| P10-09 | 10 | Claims checker | DONE | HEAD | Added scripts/check_claims.py verifying 400 extracted numeric claims across README.md and docs/model_card.md against 3,195 results/ values plus 14/14 canonical headline checks; remediated stale keyboard hparams in docs/model_card.md and unbacked PR-AUC/Brier cells in README.md; wired into .github/workflows/ci.yml; saved results/system/claims_check.json; 3 tests in ml/tests/test_check_claims.py. |
| P10-10 | 10 | Demo-video script | TODO | | |
| P10-11 | 10 | Release metadata | DONE | HEAD | Added MIT LICENSE, CFF 1.2.0 CITATION.cff (v1.0.0), linked both in README.md, and tagged release v1.0.0. |
| P10-12 | 10 | Portal UI design system | DONE | 03eae57 | Applied portal/Design.md to the resident portal shell and landing flow with semantic CSS tokens, responsive layout, accessible focus states, reduced-motion support, and preserved navigation/test contracts. Polished resident login, update details, and centre search with the same visual system; Impeccable detector reports 0 findings. |
| P10-13 | 10 | Portal theme and console polish | DONE | ebfcba2 | Added a persisted light/dark toggle, normalized typography and line-height, and replaced the security console's near-black card treatment with warmer semantic surfaces and contrast-safe inspector colors. |
| P10-14 | 10 | Impeccable doctor and navbar toggle | DONE | pending | Ran the Impeccable doctor, compacted stale design documentation, moved the theme toggle to the top navbar, removed the landing eyebrow, and fixed dark-theme privacy copy contrast. |

Status values: TODO, IN_PROGRESS, BLOCKED, DONE, SKIPPED (with reason in Notes).

## Blockers

- P0-03 — human development-environment details are required before dependency setup.

## Human checkpoints pending

- P0-03 — provide environment details and permission/status for `git clone`.

## Results index (files under results/)

- `results/mouse/` — `dataset_summary.{csv,md}`, `baselines.{csv,md}`, `hparams.json`, `evaluation_splits.{csv,md}`, `lobo_evaluation.{csv,md}`, `human_fpr_captchasolve30k.{csv,md}`, `aggregation.csv`, `calibration.json`, `ablations.{csv,md}`, `prevalence_evaluation.{csv,md}`, `shap_summary.{csv,png}`, `shap_top3_examples.json`, `fingerprint.json`, `roc_pr_curves.png`, `reliability_diagram.png`, `ablation_bar_chart.png`
- `results/keyboard/` — `privacy_scan.json`, `baselines.{csv,md}`, `hparams.json`, `evaluation.csv`, `evaluation_splits.{csv,md}`, `per_generator.{csv,md}`, `speed_terciles.{csv,md}`, `prevalence_evaluation.{csv,md}`, `calibration.json`, `feature_importance.csv`, `failure_analysis.md`, `summary.json`
- `results/fusion/` — `fusion_comparison.{csv,md}`, `modality_availability.{csv,md}`, `threshold_tradeoff.{csv,md}`, `threshold_tradeoff_curve.png`
- `results/system/` — `scoring_latency.json`, `latency_histogram.png`, `sdk_size.json`, `sim_runs.jsonl`, `sim_summary.{csv,md}`, `system_results.{json,csv,md}`, `loadtest_summary.{json,csv,md}`, `security_checks.{json,md}`, `rule_layer_ablation.{csv,md}`, `local_features_parity.json`, `axe_audit.json`
- `docs/report_assets/` — `manifest.json`, `table1_dataset_summary.{csv,md}`..`table8_simulator_summary.md`, `fig1_roc_pr_curves.png`..`fig7_latency_histogram.png`

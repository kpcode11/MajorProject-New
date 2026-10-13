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

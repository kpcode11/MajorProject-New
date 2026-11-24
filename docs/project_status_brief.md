# Passive Bot Guard (SIH1672) — Complete Project Status Brief

> **Purpose of this document:** A complete, self-contained snapshot of the project's current state, architecture, verified empirical results, limitations, and next steps (as of **2026-11-19**, release **`v1.0.0`**). Every metric below is verified against saved files in `results/` by `scripts/check_claims.py`.

---

## 1. Project Identity & Current Repository State

- **Project Name:** Passive Bot Guard (SIH1672)
- **Problem Statement:** Smart India Hackathon **SIH1672** — Privacy-preserving passive behavioural bot detection as a replacement for intrusive visual/audio CAPTCHAs on web portals (UIDAI-style citizen portal demonstration).
- **Author & Licence:** Keshav Prajapati — **MIT License** (`LICENSE`), citation metadata in `CITATION.cff` (`v1.0.0`).
- **Repository:** `https://github.com/kpcode11/MajorProject-New`
- **Current Branch & Tag:** `phase-10-final-eval-release` | Latest commit: `e7cb096` | Annotated release tag: **`v1.0.0`**
- **Overall Progress (`PROGRESS.md`):**
  - **DONE:** `121` tasks across Phases 0–10
  - **SKIPPED:** `18` tasks (Phase 8 mobile touch — explicitly scoped out as `touch: null`; optional Phase 9 neural trajectory model `P9-14`/`P9-15`)
  - **TODO:** `1` task remaining — **`P10-10` (Demo-video script & human demo recording)**
- **Quality Gates (All Passing):**
  - `python scripts/tasks.py lint` — **0 issues** (Ruff lint/format, strict mypy, Prettier)
  - `python scripts/tasks.py test-fast` — **100% pass** (ML pytest + Hypothesis, Backend pytest, `111` SDK Vitest tests, `23` Portal Vitest tests)
  - `python scripts/check_claims.py` — **Pass** (`400` extracted numeric claims across `README.md` & `docs/model_card.md` verified against `3,195` measured values in `results/`; `14/14` canonical headline checks passed; wired into `.github/workflows/ci.yml`)

---

## 2. System Architecture & Tech Stack

The system is a 7-part modular architecture implementing **defence in depth** (environment integrity rules + calibrated behavioural ML + accessible step-up challenge):

1. **Browser Collector SDK (`sdk/`):**
   - Zero-dependency TypeScript library built with Vite (`16.22 KB` ESM / `14.86 KB` UMD gzipped, under the `30 KB` budget).
   - Captures passive mouse kinematics, privacy-safe keystroke timing (`key_class` only — never characters), and ephemeral browser automation signals.
   - Supports **client-side local feature extraction (`sendRawTrace=false`)** computing the exact 120 mouse + 31 keyboard features in the browser (`< 1e-9` parity with Python server extraction) so raw trajectories never leave the device.
   - Uses a rotating ephemeral `X-Session-Id` (no cookies or persistent device fingerprints).
2. **Scoring & Portal Backend (`backend/`):**
   - **FastAPI + Pydantic v2 + ONNX Runtime** (`mouse-v1`, `keyboard-v1`, `fusion-v1`; `touch: null`).
   - **Single-use cryptographic nonces (`nonce.py`):** Bound to BLAKE2b hash of coarse IP prefix (`/24` IPv4 or `/48` IPv6) + User-Agent; atomic get-and-delete prevents replay.
   - **13 Pure Environment Rules (`R01`–`R13` in `rules.py`, configured in `config/rules.yaml`):**
     - `R01`–`R12` soft signals (e.g., `navigator.webdriver`, headless UA tokens, missing languages/plugins, zero viewport, impossible timestamps) combined via weighted **Noisy-OR**.
     - `R13` & nonce/token integrity checks act as hard blocks.
   - **3-Band Risk Policy (`policy.py`, `backend/config/policy.yaml`):**
     - `score < 0.35` → **`allow`** (issues short-lived HS256-signed single-use JWT human token bound to `act` claim; zero friction).
     - `0.35 <= score < 0.75` → **`challenge`** (triggers accessible step-up verification).
     - `score >= 0.75` or hard rule → **`deny`**.
     - Configurable `fail_safe.mode` (`challenge` default) prevents silent fail-open bypasses.
   - **Endpoints:**
     - Assessment: `/v1/nonce`, `/v1/assess`, `/v1/assess/challenge`, `/v1/health`
     - Protected Mock Citizen Portal: `/portal-api/otp/request`, `/portal-api/details/update`, `/portal-api/centres/search`, `/portal-api/stats`
     - Admin Telemetry: `/admin/*` (live stats, rule weights, thresholds, feedback — prototype-only, no SSO/RBAC yet)
   - **Storage & Retention (`store.py`, `retention.py`):** `InMemoryStore`, `SQLiteStore`, `RedisStore`; daily-salted `session_hash`; automated purge of decision logs after `7` days and daily aggregates after `30` days.
3. **Mock Citizen Portal & Admin Dashboard (`portal/`):**
   - React + Vite frontend with protected workflows (OTP login, profile update, centre search), accessible step-up modal (physical Spacebar hold + single-press accessible fallback), and an embedded Admin Dashboard (`AdminDashboardPage.tsx`).
4. **Offline ML Pipeline (`ml/`):**
   - Streaming chunked dataset loaders, $O(N)$ two-pointer 10s/5s sliding windowing, 120 mouse features + 31 keyboard features, leakage-free grouped splits (`train_groups.isdisjoint(test_groups)` enforced by assertion), Optuna 5-fold `StratifiedGroupKFold` tuning, isotonic/Platt calibration, TreeSHAP explanations, and ONNX export with `< 1e-4` parity checks.
5. **Localhost-Only Bot Simulator (`simulator/`):**
   - Strictly refuses non-local hosts (`simulator/safety.py` + `simulator/allowlist.txt`).
   - Implements **Tier 1** (plain HTTP), **Tier 2** (default Playwright), **Tier 3** (stealth Playwright), and **Tier 4** (human-like spline + log-normal timing bot).
6. **Load Testing (`loadtest/`):**
   - Standalone async runner (`python scripts/tasks.py loadtest`), Locust file, and k6 scenarios testing normal mixed traffic, protected-endpoint floods, nonce floods, and malformed `/v1/assess` floods.
7. **Reproducible Evaluation & Docs (`scripts/`, `results/`, `docs/`):**
   - `python scripts/tasks.py eval-all` regenerates all 85+ tables, JSONs, and PNG figures into `results/` and `docs/report_assets/`.
   - Complete docs: `README.md`, `docs/model_card.md`, `docs/architecture.md`, `docs/api.md`, `docs/signals.md`, `docs/threat_model.md`, `docs/accessibility.md`, `docs/privacy_register.md`, `docs/data_inventory.md`, `docs/decision_log.md`.

---

## 3. Privacy, Accessibility & Fairness Engineering

- **Zero Keystroke Content Logging:** Only syntactic key class (`ALPHA`, `DIGIT`, `SPACE`, `BACKSPACE`, `ENTER`, `MODIFIER`, `PUNCT`, `OTHER`) + press/release timestamps (`down_ms`, `up_ms`). Automated scanner verified **`0` prohibited columns** across `997` shards / `725,436` key events (`results/keyboard/privacy_scan.json`).
- **No Persistent Fingerprinting:** Canvas, WebGL, AudioContext, and font enumeration are prohibited; only ephemeral automation indicators are inspected.
- **Missing-Modality Fairness:** Keyboard-only or mouse-only users are never penalized for missing channels. Keyboard-only sessions with valid typing windows (`>= 10` keys) are capped at `MISSING_MOUSE_VALID_KB_MAX_SCORE = 0.50` (never hard-denied; verified by 6 E2E tests in `backend/tests/test_missing_modality_e2e.py`).
- **WCAG 2.1 AA Accessibility:** **`0` serious/critical `axe-core` violations across `11` UI states** (`results/system/axe_audit.json`), full keyboard-only E2E portal flows (`portal/test/keyboard_e2e.test.tsx`), and documented screen-reader smoke checklist (`docs/accessibility.md`).

---

## 4. Datasets & Explicit Scope Disclosures

| Dataset | Modality | Role | Extracted Volume |
| :--- | :--- | :--- | :--- |
| **Bournemouth (`web_bot_detection`)** | Mouse + Env | Primary human & bot (`Phase 1` & `Phase 2`) | `449` sessions / `22,851` windows (`P1`: 150 / 7,574; `P2`: 299 / 15,277) |
| **IEEE Blog Bots (`ieee_blog_bots`)** | Mouse | Cross-dataset & LOBO (`human`, `fallible`, `humanish`, `mimic`) | `126` sessions / `1,114` windows |
| **DELBOT-Mouse (`delbot_mouse`)** | Mouse | Multi-generator (`human`, `gan`, `naturalmousemotion`, `pyhm`, `pynput`) | `3,493` sessions / `4,432` windows |
| **CaptchaSolve30k** | Mouse | **Human-only FPR stress test** (240 Hz games, held out from training) | `300` sessions / `662` windows |
| **Aalto 136M Keystrokes** | Keyboard | Human typing paired with synthetic bots `K1`–`K4` (`K3` held out) | `997` participants / `14,941` human windows / `725,436` key events (`+ 14,941` `K1`/`K2`/`K4` + `4,980` held-out `K3`) |

**Explicitly Disclosed Omissions:**
- **BeCAPTCHA-Mouse & CMU Keystroke:** Unavailable for public download during acquisition.
- **UL-Keystroke:** Repository contains analysis scripts only (no raw data).
- **Phase 8 Mobile Touch:** Explicitly skipped (`touch: null` in API and policy).

---

## 5. Verified Empirical Results (All Matched to `results/`)

### 5.1 Mouse Behaviour Model (`LightGBM` + Isotonic Calibration + ONNX)
- **Shortcut / Dataset Fingerprint Discovery:** A dataset classifier achieves `0.9985` accuracy (`results/mouse/fingerprint.json`), proving raw in-distribution scores are inflated by sampling-rate shortcuts (`dt_mean`, `duration_ms`, `n_points`, `dt_mode_fraction`). Removing 20 shortcut features (`no_shortcuts`, 100 behavioural features) dramatically improves transfer:
  - **In-Distribution (`all_features`, 120):** ROC-AUC `0.9999` `[0.9999, 1.0000]`, PR-AUC `1.0000`, Recall@1%FPR `0.9994`
  - **In-Distribution (`no_shortcuts`, 100):** ROC-AUC `0.9990` `[0.9982, 0.9996]`, PR-AUC `0.9991`, Recall@1%FPR `0.9904`
  - **Cross-Phase `P1 -> P2`:** `0.8297` (`all_features`) → **`0.9785` `[0.9715, 0.9846]`** (`no_shortcuts`, Recall@5%FPR `0.8517`)
  - **Cross-Phase `P2 -> P1`:** `0.9746` (`all_features`) → **`0.9970` `[0.9959, 0.9980]`** (`no_shortcuts`, Recall@1%FPR `0.9690`)
  - **Cross-Dataset (`Bournemouth + DELBOT -> IEEE`, `no_shortcuts`):** **ROC-AUC `0.9305` `[0.9006, 0.9551]`**, PR-AUC `0.8977`, Recall@1%FPR `0.2235`
- **Leave-One-Bot-Type-Out (LOBO, zero-shot unseen bots, `no_shortcuts`):**
  - Strong on 8 of 9 families: `mimic` (`0.9950`), `fallible` (`0.9947`), `humanish` (`0.9927`), `advanced` (`0.9710`), `pyhm` (`0.9490`), `moderate` (`0.9195`), `naturalmousemotion` (`0.8365`), `pynput` (`0.8202`).
  - **Known blind spot:** `delbot_mouse:gan` = **`0.4872`** ROC-AUC when no GAN samples are in training.
- **CaptchaSolve30k Human-FPR Stress Test (240 Hz game tasks at 5% browsing threshold):**
  - `all_features`: `76.67%`–`95.91%` FPR → `no_shortcuts`: **`31.71%`–`57.25%`** FPR (shows domain-specific threshold calibration is required for non-form tasks).
- **Calibration & ONNX Parity:** Isotonic calibration reduces Brier loss from `0.0023` to `0.0018`; ONNX `max_abs_diff = 7.52e-08 < 1e-4`.

### 5.2 Keyboard Behaviour Model (`31` Timing Features) & Desktop Fusion
- **Deployed Reference (`keyboard-v1`, Scaled Logistic Regression `C = 0.1`, ONNX `max_abs_diff = 8.04e-08`):**
  - In-distribution (`K1`, `K2`, `K4`): ROC-AUC `1.0000`
  - Held-out `K3` (log-normal human mimic, zero-shot): ROC-AUC **`0.8415` `[0.8191, 0.8640]`** (Recall@1%FPR `0.0353`, Recall@5%FPR `0.2492`)
  - Overall (`K1`–`K4`): ROC-AUC **`0.9011` `[0.8880, 0.9138]`**
- **Non-linear Comparison (`keyboard-lgbm-v1`, Tuned LightGBM):**
  - Held-out `K3` (zero-shot): ROC-AUC **`0.9951` `[0.9884, 0.9988]`** (Recall@1%FPR `0.9851`)
  - Overall (`K1`–`K4`): ROC-AUC **`0.9969` `[0.9935, 0.9993]`**
  - Typing-speed terciles (`slow` / `medium` / `fast`): LightGBM ROC-AUC `0.9842` / `0.9971` / `0.9999` (LR Human FPR @ 1% global thr: `0.16%` / `0.93%` / `1.37%`).
- **Desktop Score Fusion (`2,462` held-out pseudo-sessions, simulated pairing):** `stacker` ROC-AUC `1.0000`, Brier `0.0001`.

### 5.3 End-to-End System, Simulator, Load & Security Benchmarks
- **ONNX + Rules Scoring Latency:** `p50 = 1.65 ms`, `mean = 3.07 ms`, `p95 = 15.16 ms`, `p99 = 22.07 ms`, **`325.58 req/s`** (target `p95 < 200 ms`).
- **Bot Simulator (Passive Mode, 25 runs/tier, `seed=42`):**
  - `protection_mode=off`: `0%` caught (`100%` of Tiers 1–4 succeed).
  - `protection_mode=passive`: Tier 1 **`100.0%`**, Tier 2 **`100.0%`**, Tier 3 **`100.0%`**, Tier 4 **`92.0%`** caught (challenged/denied/blocked-at-api).
- **Mixed Load Test (`loadtest`):** `630` total requests @ **`1,155.42 req/s`**, **`0/460` malicious requests reached protected API**, **`0` `5xx` errors**.
- **Security Suite & Static Analysis:** **`72/72` security tests passed**, **`0` Bandit SAST findings**, **`0` production runtime npm vulnerabilities**.

---

## 6. Detailed Problems, Weaknesses & Root-Cause Analysis (For Report & Judge Q&A)

Below is a detailed, honest breakdown of every major technical, data, ML, accessibility, and security problem in the current `v1.0.0` system, backed by measured evidence from `results/`, current mitigations, and concrete production remediation paths.

---

### Problem 1: Zero-Shot GAN Mimicry Breaks the Mouse-Only Classifier
- **Measured Evidence:** In `results/mouse/lobo_evaluation.csv`, when `delbot_mouse:gan` (`1,899` bot sessions / `1,899` windows) is held out from training, the non-shortcut LightGBM mouse model drops to **`0.4872` ROC-AUC**, **`0.0026` Recall @ 1% FPR**, and **`0.0026` Recall @ 5% FPR** (worse than random guessing at low FPR).
- **Root Cause:** The DELBOT GAN was trained directly on DELBOT circle-task human mouse trajectories, reproducing human-like speed, curvature, and pause statistics on fixed window-level summary features. Tabular aggregate statistics (`mean`, `std`, `p50`, `iqr`, `skew`) cannot easily distinguish a generator explicitly trained to match those marginal kinematics unless adversarial/GAN samples are included in training or sequence-level temporal structure is modelled.
- **Impact:** A sophisticated attacker using a generative trajectory model (or human replay) can bypass the mouse-only ML channel if they also spoof browser environment checks.
- **Current Mitigation:** Defence-in-depth fusion — environment rules (`R01`–`R13`), single-use context-bound nonces, keyboard timing (`keyboard-v1`), and the 3-band policy (`challenge` step-up) still catch non-browser or headless/stealth wrappers (`100%` of Tiers 1–3, `92%` of Tier 4 in `results/system/sim_summary.csv`).
- **Concrete Fix (Future Work):** Add adversarial/GAN-generated trajectories to training data, evaluate a sequence/trajectory neural model (skipped `P9-14`/`P9-15`) over raw `(dx, dy, dt)` sequences, and incorporate cross-interaction page-flow signals (focus order, scroll-to-click timing).

---

### Problem 2: Dataset Fingerprinting & Severe Threshold Drift Under Domain Shift
- **Measured Evidence:**
  - `results/mouse/fingerprint.json`: A classifier trained solely to predict *which dataset* a human mouse window came from achieves **`0.9985` accuracy**, proving raw trajectories carry strong collection-rate and UI-layout artifacts (`dt_mean`, `dt_mode_fraction`, `duration_ms`, `n_points`).
  - `results/mouse/evaluation_splits.csv`: Removing 20 shortcut features lifts cross-phase `P1 -> P2` ROC-AUC from `0.8297` to **`0.9785`**, and cross-dataset (`Bournemouth + DELBOT -> IEEE Blog Bots`) achieves **`0.9305` ROC-AUC** — **but Recall @ 1% FPR drops to `0.2235`** (and `Balanced Accuracy` drops to `0.6071`) because probability calibration shifts across websites.
  - `results/mouse/human_fpr_captchasolve30k.csv`: On `CaptchaSolve30k` (human players solving fast 240 Hz game puzzles on a `200x200` canvas where `dt_mode_fraction = 1.0`), a browsing-calibrated 5% FPR threshold flags **`76.67%`–`95.91%`** of real humans with all features, and still **`31.71%`–`57.25%`** even after removing shortcut features.
- **Root Cause:** Mouse kinematics depend heavily on the *UI task* (filling a web form vs playing a 240 Hz canvas game vs reading a blog), monitor DPI, and OS/browser pointer polling rate. While the *relative ranking* (ROC-AUC) transfers well across web tasks, the *absolute score threshold* does not.
- **Impact:** Deploying static global thresholds (`0.35` / `0.75`) onto a brand-new portal without site-specific calibration can cause either high false positives (real humans pushed to `challenge`) or low bot recall.
- **Current Mitigation:** Shortcut features are excluded in transfer evaluations; the 3-band policy routes ambiguous scores (`0.35 <= score < 0.75`) to an accessible step-up challenge instead of hard-denying; admin endpoints (`/admin/*`) allow tuning thresholds per deployment.
- **Concrete Fix (Future Work):** Collect a small unlabelled/verified human calibration sample on the target portal during a shadow-mode rollout and fit site-specific isotonic/temperature calibration + per-route thresholds.

---

### Problem 3: Synthetic Keyboard Bots & Deployed Keyboard Model Gap (`keyboard-v1` vs `keyboard-lgbm-v1`)
- **Measured Evidence:**
  - All four keyboard bot generators (`K1`–`K4`) are synthetic (`14,941` `K1`/`K2`/`K4` + `4,980` held-out `K3`) because no public real-world automated-bot keystroke dataset was available.
  - The currently deployed `backend/models/keyboard-v1/model.onnx` is **Scaled Logistic Regression (`C = 0.1`)**, which achieves **`0.8415` ROC-AUC** on held-out log-normal mimic `K3` — but only **`0.0353` (3.53%) Recall @ 1% FPR** and **`0.2492` (24.92%) Recall @ 5% FPR** (`results/keyboard/per_generator.csv`).
  - By contrast, the trained non-linear model `backend/models/keyboard-lgbm-v1/model.onnx` (Tuned LightGBM) achieves **`0.9951` ROC-AUC** and **`0.9851` (98.51%) Recall @ 1% FPR** on `K3`, yet is not the default served model.
- **Root Cause:** Linear Logistic Regression cannot separate `K3`'s realistic log-normal marginal dwell/flight distributions from human typing when non-linear feature interactions (e.g., burst-length vs lag-1 autocorrelation vs dwell-flight correlation) carry the signal. Additionally, synthetic bots may not reflect real-world credential-stuffing frameworks or browser autofill/password managers.
- **Impact:** Under the default `keyboard-v1` model, a stealthy bot using log-normal typing jitter (`K3`) is rarely caught by keyboard timing alone at strict FPR targets. Furthermore, real human password-manager autofill or copy-paste can look like `K4` (copy-paste burst) if not handled carefully.
- **Current Mitigation:** `keyboard-v1` is fused with mouse kinematics and environment rules (`R01`–`R13`), and missing-mouse keyboard-only users are protected by `MISSING_MOUSE_VALID_KB_MAX_SCORE = 0.50` so they are never hard-denied.
- **Concrete Fix (Future Work):** Promote `keyboard-lgbm-v1` to default after validating false-positive rates on real password-manager / autofill / short-PIN sessions, and collect real Playwright/Selenium typing traces to supplement synthetic `K1`–`K4`.

---

### Problem 4: Simulated Desktop Fusion (Pseudo-Sessions, Not Real Simultaneous Recordings)
- **Measured Evidence:** `results/fusion/fusion_comparison.csv` reports `1.0000` ROC-AUC and `0.0001` Brier score for `stacker` across `2,462` held-out sessions (`969` human, `1,493` bot) — explicitly labelled `pseudo-session evaluation (simulated pairing)`.
- **Root Cause:** No single public dataset contains simultaneous mouse trajectories, keystroke timing, and browser environment logs from the same real human and bot sessions. Human mouse windows (Bournemouth/IEEE/DELBOT) were paired deterministically (`seed=42`) with independent human keyboard windows (Aalto), and bot mouse windows with synthetic keyboard bots.
- **Impact:** The `1.0000` fusion ROC-AUC is an **upper bound**, not a live-portal measurement. Real users often exhibit sparse telemetry (e.g., clicking once and autofilling a form, or tabbing through fields with no mouse movement), and real bots may mix human-like mouse movement with scripted typing or vice versa.
- **Current Mitigation:** Explicitly labelled as `pseudo-session evaluation (simulated pairing)` in `backend/models/fusion-v1/metadata.json`, `docs/model_card.md`, and `README.md`; end-to-end live-flow behaviour is separately measured via the 4-tier bot simulator (`results/system/sim_summary.csv`).
- **Concrete Fix (Future Work):** Record an IRB/consent-approved joint multi-modal dataset on the mock citizen portal with real human volunteers and real browser-automation bots performing the same forms.

---

### Problem 5: No Mobile / Touch Support (`touch: null`)
- **Measured Evidence:** All 16 Phase 8 tasks were explicitly skipped (`PROGRESS.md`, `docs/decision_log.md`). `backend/app/scoring.py` and `results/system/scoring_latency.json` report `"touch": null`.
- **Root Cause:** Scope and time prioritisation for desktop mouse + keyboard + full-stack security/accessibility delivery, plus lack of clean paired mobile web-bot touch datasets.
- **Impact:** For an Indian citizen portal (SIH1672 / UIDAI-style context), a large majority of real citizens access portals from Android/iOS smartphones. Without a touch model, mobile sessions cannot be scored on tap pressure, swipe velocity, or touch-area kinematics.
- **Current Mitigation:** Missing-modality fairness guarantees mobile users are **never penalized** for having no mouse events (`touch: null`, `mouse: null`); mobile sessions fall back cleanly to environment rules (`R01`–`R13`), keyboard timing (if present), and the accessible step-up challenge.
- **Concrete Fix (Future Work):** Implement the Phase 8 touch collector (`PointerEvent` / `TouchEvent` tap duration, contact radius, scroll inertia) and train a mobile touch ONNX model on public touch-dynamics datasets + mobile emulator bots.

---

### Problem 6: No Real-World Assistive-Technology User Testing & Step-Up Friction Trade-Offs
- **Measured Evidence:** `results/system/axe_audit.json` confirms `0` serious/critical `axe-core` WCAG 2.1 AA violations across `11` UI states, and `portal/test/keyboard_e2e.test.tsx` + `backend/tests/test_missing_modality_e2e.py` pass. However, `docs/accessibility.md` explicitly notes that no real human screen-reader, switch-device, eye-tracker, or motor-impaired participants were recorded or evaluated.
- **Root Cause:** Student prototype without access to an assistive-technology user study cohort.
- **Impact:**
  - Users of voice dictation, on-screen virtual keyboards, or switch devices produce unusual or zero key-down/key-up intervals that may push scores into the `challenge` band (`0.35`–`0.50`).
  - The accessible step-up challenge offers a single-press fallback alongside the physical Spacebar hold; while inclusive for motor-impaired users, an overly permissive single-press fallback lowers the security bar against Tier 3/4 bots that automate the step-up modal.
- **Current Mitigation:** Hard cap `MISSING_MOUSE_VALID_KB_MAX_SCORE = 0.50` ensures keyboard-only humans with valid typing (`>= 10` keys) are never hard-denied; manual NVDA/Narrator/VoiceOver walkthrough checklist is documented in `docs/accessibility.md`.
- **Concrete Fix (Future Work):** Conduct usability testing with assistive-technology users, add privacy-preserving accessibility-friendly challenge alternatives (e.g., cryptographic proof-of-work + interaction timing), and calibrate thresholds on assistive-input telemetry.

---

### Problem 7: Prototype Security & Deployment Boundaries (Not Production-Hardened)
- **Measured Evidence:** `results/system/security_checks.json` passes `72/72` security tests with `0` Bandit findings and `0` production npm runtime vulnerabilities, **within the prototype scope**. However, `docs/threat_model.md` and `docs/api.md` document explicit prototype gaps:
  1. **No Admin Authentication / RBAC:** `/admin/*` endpoints (viewing telemetry, modifying rule weights and risk thresholds, submitting feedback) have no SSO, OAuth2, or role-based access control.
  2. **Single Local Symmetric Secret:** Human tokens are signed with local `HS256` (`BOTGUARD_SECRET_KEY`), and there is no KMS/HSM key rotation or distributed JWKS infrastructure.
  3. **No Distributed Botnet / IP-Reputation / TLS-JA3 Layer:** Rate limiting operates per `/24` IPv4 (or `/48` IPv6) bucket and ephemeral session in local memory/SQLite/Redis. A distributed residential-proxy botnet rotating IPs and sessions can stay under per-bucket rate limits.
  4. **Client-Side Feature Extraction Trust Boundary (`sendRawTrace=false`):** While great for privacy, trusting client-computed feature vectors lets a determined attacker forge clean-looking 120-element mouse feature arrays directly in JSON without moving a mouse.
  5. **Demo-Only Simulator Guardrail:** `Tier 4` bots still achieve an `8.0%` (`2/25`) allow rate in passive mode (`results/system/sim_summary.csv`), showing that well-tuned human-like bots can occasionally slip below `0.35`.
- **Concrete Fix (Future Work):** Put `/admin/*` behind SSO/RBAC + audit logs; use asymmetric `RS256`/`ES256` with automated key rotation; combine passive behavioural scoring with edge WAF / TLS fingerprinting / ASN reputation at the CDN layer; and require server-side raw-trace verification (or attested execution) on high-sensitivity routes if feature-vector forgery is in scope.

---

### Problem 8: Missing Operational Polish Before Stage Presentation
- **Unavailable Public Datasets:** `BeCAPTCHA-Mouse` and `CMU Keystroke` could not be downloaded during acquisition, and `UL-Keystroke` only published analysis scripts — limiting cross-dataset validation breadth.
- **Unfinished Task `P10-10`:** No written `docs/demo_script.md` or recorded backup demo video exists yet. Live demos on venue Wi-Fi/laptops are risky without a rehearsed script and backup recording.
- **Branch Not Yet Merged to `main`:** All Phase 10 work and tag `v1.0.0` currently live on `phase-10-final-eval-release` and should be merged to `main` and pushed to GitHub before final submission.

---

## 7. Key Commands to Run, Demo & Reproduce

```powershell
# Setup all Python & Node environments
python scripts/tasks.py setup

# Launch local interactive demo (FastAPI backend + Mock Portal + Admin Dashboard)
python scripts/tasks.py demo

# Run bot simulator (Tiers 1-4, in-process ASGI, fast)
backend\.venv\Scripts\python.exe simulator\run_all.py --n-per-tier 25 --seed 42

# Run bot simulator against live running demo server
backend\.venv\Scripts\python.exe simulator\run_all.py --live-http --base-url http://127.0.0.1:8000 --n-per-tier 10 --seed 42

# Run mixed human + malicious flood load test
python scripts/tasks.py loadtest

# Regenerate all 85+ evaluation tables & figures into results/ and docs/report_assets/
python scripts/tasks.py eval-all

# Verify lint, fast tests, and numeric claims
python scripts/tasks.py lint
python scripts/tasks.py test-fast
python scripts/check_claims.py
```

---

## 8. Remaining Steps Before Final Hackathon Submission

1. **`P10-10` (Only remaining TODO):** Write a concise 2–3 minute demo script (`docs/demo_script.md`) and record a backup demo video showing: (a) seamless human login (`allow`, no CAPTCHA), (b) keyboard-only / ambiguous flow (`challenge` accessible step-up), (c) Tier 1–4 bot simulator blocked (`deny` / `blocked-at-api`), and (d) live telemetry on the Admin Dashboard.
2. **Dry-run on presentation laptop:** Test `python scripts/tasks.py demo` + `--live-http` simulator end-to-end before going on stage.
3. **Final Git cleanup:** Merge `phase-10-final-eval-release` into `main` and push the branch + `v1.0.0` tag to GitHub when ready.

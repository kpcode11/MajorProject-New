# Privacy Impact Assessment (P9-07)

**Project:** Passive Bot Detection to Replace CAPTCHA (SIH1672)  
**Scope:** Browser SDK (`sdk/`), Scoring & Admin Backend (`backend/`), Mock Resident Self-Service Portal (`portal/`), and Offline Training Pipeline (`ml/`)

> **Legal & Regulatory Disclaimer:**  
> This document records the engineering privacy analysis, data-minimisation controls, and retention architecture implemented in this student prototype. All references to the **Digital Personal Data Protection (DPDP) Act, 2023 (India)**, **UIDAI / Aadhaar ecosystem security guidelines**, and **GDPR / ISO 27701 principles** reflect **engineering assumptions** used to guide technical design. **Formal legal or regulatory compliance requires review and sign-off by qualified legal counsel and an appointed Data Protection Officer (DPO) prior to any production deployment.**

---

## 1. Architectural Privacy Principles

1. **Zero Keystroke Content Capture:** The browser SDK (`sdk/src/collectors/keyboard.ts`) maps `KeyboardEvent` inputs immediately to 8 coarse categories (`letter`, `digit`, `space`, `punct`, `modifier`, `enter`, `backspace`, `other`) plus millisecond press/release timestamps (`[key_class, down_ms, up_ms]`). Raw `event.key`, `event.code`, input values, and clipboard contents are never read, buffered, transmitted, or stored.
2. **No Persistent Device Fingerprinting:** Environment signals (`sdk/src/collectors/env.ts`, `backend/app/schemas.py:EnvSignals`) are bucketed to coarse hardware/viewport classes solely to evaluate plausibility rules (`R01`–`R13`). Canvas hashes, WebGL unmasked serials, AudioContext fingerprints, font enumerations, battery telemetry, and persistent storage identifiers are never collected.
3. **Ephemeral, Daily-Unlinked Session Identifiers (`P9-05`):**
   - The SDK generates a random 128-bit session token (`generateSessionId()` in `sdk/src/index.ts`) held strictly in JavaScript heap memory (`X-Session-Id` header), rotating on every page load (`start()`), on `stop()`, or after 15 minutes (`SESSION_ROTATION_MS`). It never touches `localStorage`, `sessionStorage`, `IndexedDB`, or `document.cookie`.
   - The backend (`make_session_hash()` in `backend/app/nonce.py`) hashes the coarse IP bucket (`/24` IPv4 or `/48` IPv6), User-Agent, and per-page-load token with a **UTC day-bound rotating salt** (`daily_session_salt()`). Identical client inputs across two different UTC calendar days produce unlinkable 64-bit digests (`session_hash`), preventing cross-day tracking.
4. **Coarse IP Bucketing Only:** Full client IP addresses are never written to any database column or structured log line. Logs record only `ip_bucket` (`198.51.100.0/24` or `2001:db8:abcd::/48` via `_coarsen_ip()`).
5. **Two-Tier Automated Retention Purge (`P9-04`):**
   - Raw coordinate/timing arrays (`points`, `clicks`, `events`, `gestures`) exist only in request memory during scoring (~2–15 ms) and are discarded immediately (`sanitize_derived_features()` in `backend/app/db.py`).
   - Optional derived scalar features (`assessments.features`) expire after **7 days** (`FEATURE_TTL_SECONDS = 604800`) and are nulled out by `RetentionScheduler` (`backend/app/retention.py`).
   - Assessment and challenge rows expire after **30 days** (`ASSESSMENT_TTL_SECONDS = 2592000`) and are permanently deleted.

---

## 2. Signal-Group Analysis (Purpose, Necessity, Alternatives, Retention)

### 2.1 Group A — Coarse Environment & Browser Integrity Signals (`EnvSignals`)

| Attribute | Details |
| :--- | :--- |
| **Collected Fields** | `webdriver`, `ua_family`, `ua_major`, `ua_os`, `platform`, `hints_brands`, `hints_platform`, `languages_count`, `lang_primary`, `timezone_offset_min`, `screen_w_bucket`, `screen_h_bucket`, `viewport_w`, `viewport_h`, `outer_w`, `outer_h`, `dpr_bucket`, `hw_concurrency_bucket`, `device_memory_bucket`, `webgl_renderer_class`, `plugins_count`, `max_touch_points`, `touch_event_supported`, `native_fn_integrity_ok`, `storage_available`, `visibility` |
| **Purpose** | Detect deterministic automation indicators (`navigator.webdriver`), headless/virtual rendering (`SwiftShader`/`llvmpipe` classified as `software`/`virtual`), impossible geometry (`viewport > screen`, `0x0` outer window), UA-vs-platform contradictions, and monkey-patched browser prototypes (`R01`–`R09`). |
| **Necessity** | Necessary to stop Tier-1 HTTP scripts and Tier-2/Tier-3 headless browsers even before rich behavioural interaction occurs. All high-entropy values are bucketed on the client (e.g., `webgl_renderer_class` is one of `hardware`, `software`, `virtual`, `unknown`; `dpr_bucket` is rounded to `{1, 1.5, 2, 3}`). |
| **Less-Invasive Alternatives Considered** | 1. *Server-side HTTP header inspection only (`User-Agent` + TLS/headers):* Considered and retained for Tier-1 bots, but insufficient alone because headless Chromium sends standard HTTP headers while exposing DOM-level inconsistencies (`webdriver`, `0x0` outer dimensions, software WebGL).<br>2. *Full device fingerprinting (Canvas/WebGL/Audio hashes):* **Rejected** as privacy-invasive and unnecessary; coarse categorical buckets suffice for consistency rules without uniquely identifying a resident's device. |
| **Retention** | Raw `EnvSignals` JSON is **not stored** in the database (used in-memory during `POST /v1/assess` only). Only the rule IDs fired (e.g., `["R02", "R05"]`) and coarse `device_class` (`desktop`, `mobile`, `tablet`, `unknown`) are stored in `assessments` for up to **30 days**. |

---

### 2.2 Group B — Mouse Kinematics & Click Signals (`MouseBehaviour`)

| Attribute | Details |
| :--- | :--- |
| **Collected Fields** | Up to 600 throttled (~60 Hz) `[x, y, t_ms]` viewport-relative cursor samples, up to 50 `[x, y, down_ms, up_ms]` click records, `untrusted_count` (`!event.isTrusted`), and `wheel_events` count within a rolling 10-second ring buffer. |
| **Purpose** | Extract 29 aggregate kinematic features (path efficiency, velocity/acceleration moments, jerk, curvature entropy, submovement count, Fitts's law ratio, minimum-jerk residual, click dwell) for the LightGBM mouse classifier and rules `R10`/`R11`. |
| **Necessity** | Necessary to distinguish human neuromotor variability (submovements, bell-shaped velocity profiles, micro-corrections) from synthetic linear paths, constant-step Bezier splines, and instantaneous coordinate teleports. |
| **Less-Invasive Alternatives Considered** | 1. *Event counts only (e.g., total `mousemove` count):* Considered, but trivially defeated by bots firing synthetic `mousemove` events along a straight line.<br>2. *Client-side feature extraction (`sendRawTrace=false`, `P9-08`):* Supported as an architectural upgrade path where the 29 scalar summary statistics are computed in the browser so raw `[x, y, t_ms]` points never leave the client. Even when transmitted, raw points are discarded immediately after in-memory feature extraction on the server. |
| **Retention** | **Raw `[x, y, t_ms]` points and clicks: 0 seconds (never written to disk or logs).** Derived scalar features (29 floats, when `STORE_FEATURES_IN_DB=true`): **7 days** (`FEATURE_TTL_SECONDS`), then nulled out by `run_retention_purge()`. |

---

### 2.3 Group C — Keyboard Timing & Key-Class Signals (`KeyBehaviour`)

| Attribute | Details |
| :--- | :--- |
| **Collected Fields** | Up to 300 `[key_class, down_ms, up_ms]` tuples (`key_class` $\in$ `{"letter", "digit", "space", "punct", "modifier", "enter", "backspace", "other"}`), `paste_events` count, `autofill_suspected` boolean, and `untrusted_count`. |
| **Purpose** | Extract 20 aggregate keystroke timing features (hold-time distribution, flight-time distribution, rollover ratio, rhythm CV, RMSSD, backspace ratio, inter-class transition matrix) for the keyboard classifier and rule `R12`. |
| **Necessity** | Necessary to detect programmatic form filling (`element.fill()`, zero-variance synthetic typing loops) on forms where a user types an identifier or query, while respecting the **missing-modality policy** (paste/autofill is treated as missing keyboard cadence, never as a bot penalty). |
| **Less-Invasive Alternatives Considered** | 1. *Exact key codes (`KeyA`, `Digit1`):* **Rejected** unconditionally (`AGENTS.md` non-negotiable rule) because exact character/digraph timing can leak typed secrets or enable biometric user identification.<br>2. *Timestamp-only without key class:* Considered, but distinguishing `backspace` (error correction) and `modifier`/`enter` transitions improves bot separation without revealing any character identity. |
| **Retention** | **Raw `[key_class, down_ms, up_ms]` tuples: 0 seconds (never written to disk or logs).** Enforced at schema level (`KeyEvent.key_class_valid`) and verified by `ml/keyboard/privacy_scan.py` and `backend/tests/test_privacy_scan.py`. Derived scalar features (20 floats, when enabled): **7 days**, then nulled out. |

---

### 2.4 Group D — Page-Level Timing & Scroll Signals (`TimingSignals`)

| Attribute | Details |
| :--- | :--- |
| **Collected Fields** | `ms_since_load`, `ms_to_first_interaction`, `ms_since_nonce`, `scroll_events` count, `focus_changes` count. |
| **Purpose** | Detect impossibly fast form submissions (`R13`, e.g., submission $< 150\text{ ms}$ after page load or nonce issuance) and provide interaction context. |
| **Necessity** | Coarse page-level counters and relative durations (in milliseconds since page load) carry zero personal or cross-site information while catching automated replay and instant-submit scripts. |
| **Less-Invasive Alternatives Considered** | *Server-side nonce age only (`now - nonce_issued_at`):* Used in addition to client timing, but `ms_to_first_interaction` helps distinguish a human who pre-loaded a tab from a script that immediately fires synthetic events on load. |
| **Retention** | Raw `TimingSignals` object is discarded after request scoring (0 seconds on disk). Derived timing scalars (if `STORE_FEATURES_IN_DB=true`): **7 days**. |

---

### 2.5 Group E — Network Context, Single-Use Nonces & Rotating Session Hashes

| Attribute | Details |
| :--- | :--- |
| **Collected Fields** | Client IP (coarsened immediately to `/24` IPv4 or `/48` IPv6), HTTP `User-Agent` (hashed), ephemeral per-page-load `X-Session-Id` header, single-use `/v1/nonce` token, and short-lived `/v1/assess` human JWT. |
| **Purpose** | Prevent nonce/token replay (`P5-03`, `P5-07`), enforce per-subnet/session rate limits (`P5-04`), and group within-session assessments in the operational dashboard without tracking users across days (`P9-05`). |
| **Necessity** | Without coarse context binding and rate limiting, an attacker could harvest tokens or flood the scoring API. Coarsening IP to `/24` or `/48` and rotating the server-side session salt at UTC midnight eliminates individual IP storage and cross-day linkability. |
| **Less-Invasive Alternatives Considered** | 1. *Storing full IP addresses for security audit:* **Rejected**; `/24` (IPv4) and `/48` (IPv6) prefixes provide sufficient subnet-level visibility for rate limiting and abuse telemetry without storing personal IP identifiers.<br>2. *Cookie/localStorage session IDs:* **Rejected**; in-memory per-page-load tokens (`generateSessionId()`) plus daily-salted BLAKE2b hashes (`make_session_hash()`) require zero client storage. |
| **Retention** | - Nonces (`nonce:<token>`) & consumed JWT `jti` keys: **60–300 seconds TTL** in memory/Redis.<br>- `session_hash` in `assessments`: **30 days** (`ASSESSMENT_TTL_SECONDS`), unlinkable across UTC days.<br>- `ip_bucket` (`/24` or `/48`): Structured application logs only; never stored in database tables. |

---

### 2.6 Group F — Step-Up Challenge Telemetry (`ChallengeAssessRequest`)

| Attribute | Details |
| :--- | :--- |
| **Collected Fields** | `challenge_id`, `hold_start_ms`, `hold_end_ms`, plus optional bounded `env` and `behaviour` window during the press-and-hold interaction (`800–1500 ms`). |
| **Purpose** | Verify human completion of the accessible press-and-hold step-up challenge (`POST /v1/assess/challenge`) when initial passive confidence is in the medium band. |
| **Necessity** | Replaces cognitive/visual puzzles (distorted text or image grids) with a single accessible press-and-hold interaction (`Space`/`Enter`/pointer/touch). |
| **Less-Invasive Alternatives Considered** | *Traditional image/text CAPTCHA:* **Rejected** due to high user friction, screen-reader barriers, and third-party tracking cookies. |
| **Retention** | `challenges` table stores only `id`, `assessment_id`, `type` (`press_hold`), `issued_at`, `completed_at`, and `outcome` (`passed`/`failed`) for **30 days** (`ASSESSMENT_TTL_SECONDS`). Hold timestamps and behaviour traces are discarded after verification. |

---

### 2.7 Group G — Mock Portal Action Metadata & Operator Feedback

| Attribute | Details |
| :--- | :--- |
| **Collected Fields** | - Portal endpoints (`backend/app/portal.py`): `identifier_length` (int), `fields_updated` (list of field names, e.g., `["name"]`), `city_code`, `language_code`, `service_type`, `query_length` (int).<br>- Admin feedback (`POST /admin/feedback`): `assessment_id`, `feedback` (`"fp"` or `"fn"`). |
| **Purpose** | Demonstrate protected resident portal routes (`/portal-api/otp/request`, `/portal-api/details/update`, `/portal-api/centres/search`) and allow operators to flag suspected false positives/negatives for offline review. |
| **Necessity** | Pydantic models enforce `ConfigDict(extra="forbid")` so any request accidentally containing raw form values (`identifier`, `full_name`, `address`, `phone`, `email`) is rejected with `422 Unprocessable Entity` before reaching handler logic. |
| **Less-Invasive Alternatives Considered** | *Accepting and hashing resident identifiers on the mock portal:* **Rejected**; transmitting only integer lengths (`identifier_length`, `query_length`) and enum codes proves token gating without ever handling personal data. |
| **Retention** | Portal stats are aggregate in-memory counters (`PortalStatsTracker`). Operator `feedback` (`fp`/`fn`) is stored on the `assessments` row for **30 days** and is **never** used for automated online retraining. |

---

## 3. UIDAI / DPDP Act 2023-Style Assumptions & Compliance Mapping

The table below states the engineering assumptions adopted for this prototype alongside the corresponding verification controls and the legal review caveat:

| Principle / Requirement Area | Engineering Assumption in This Prototype | Implemented Technical Control | Verification / Test |
| :--- | :--- | :--- | :--- |
| **Purpose Limitation & No Biometric Profiling** *(DPDP Act S. 4 / S. 6; Dataset Licence Terms)* | Behavioural signals are processed strictly for **one-bit session security** (`human` vs `automated bot` on the current request) and **never** for biometric identification, user authentication, or cross-session behavioural profiling. | Models output only a single scalar bot-risk probability $p \in [0, 1]$ mapped to `low`/`medium`/`high`. No user ID or biometric template is ever created. | `backend/tests/test_api.py`, `backend/tests/test_privacy_scan.py` |
| **Data Minimisation** *(DPDP Act S. 6; UIDAI Minimal Telemetry Principle)* | Only the minimum coarse signals needed to separate automation from human interaction may leave the browser; typed characters, form values, and full IPs must never be collected. | `keyClass()` strips key identities in the browser; `extra="forbid"` on portal schemas; `_coarsen_ip()` masks IPv4 to `/24` and IPv6 to `/48`; `_REDACTED_LOG_KEYS` strips sensitive keys from logs. | `sdk/test/keyboard.test.ts`, `ml/keyboard/privacy_scan.py`, `backend/tests/test_privacy_scan.py` |
| **Storage Limitation & Automated Erasure** *(DPDP Act S. 8(7))* | Derived diagnostic features should be kept only briefly for false-positive review, and all assessment logs must be purged automatically on a fixed schedule. | `RetentionScheduler` (`backend/app/retention.py`) nulls `assessments.features` after **7 days** (`FEATURE_TTL_SECONDS`) and deletes `assessments` + `challenges` after **30 days** (`ASSESSMENT_TTL_SECONDS`). | `backend/tests/test_retention.py` (tested with `FakeClock`) |
| **Unlinkability Across Days** *(Privacy-by-Design)* | A passive security layer on a public portal must not create a persistent tracking identifier across days. | SDK generates random in-memory `X-Session-Id` per page load (`SESSION_ROTATION_MS = 15 min`); backend mixes UTC date salt (`daily_session_salt()`) into `make_session_hash()`. | `backend/tests/test_session_privacy.py`, `sdk/test/api.test.ts` |
| **Non-Discrimination & Accessibility Fairness** *(DPDP / RPwD Accessibility Assumption)* | Users of assistive technologies (keyboard-only navigation, screen readers, password managers, slow typists) must not be auto-denied due to missing mouse or keyboard modalities. | Missing-modality neutral imputation (`absent != bot`); Rule `R01` only fires when *all* payload signals are empty; step-up challenge is keyboard-operable (`Space`/`Enter`). | `ml/fusion/evaluate.py`, `backend/tests/test_rules.py`, `P9-09`–`P9-13` |

### Mandatory Legal Review Caveat

1. **No Legal Advice:** The mappings above are technical engineering controls designed for an academic demonstration (`SIH1672`) on a local mock portal. They do not constitute legal advice or a formal compliance certification.
2. **Production Prerequisites:** Before deploying passive behavioural telemetry on any live government or citizen-facing portal, the operating agency must conduct a formal **Data Protection Impact Assessment (DPIA)** with legal counsel, verify notice/consent or legitimate-use grounds under the **Digital Personal Data Protection Act, 2023** and applicable **UIDAI / CERT-In** retention directives, and configure enterprise SSO/RBAC on all `/admin/*` endpoints.

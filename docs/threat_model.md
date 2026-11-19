# BotGuard Threat Model (`docs/threat_model.md`)

**Project:** Passive Behaviour-Based Bot Detection to Replace CAPTCHA (SIH1672)
**Scope:** Local mock resident portal (`portal/`), browser telemetry SDK (`sdk/`), FastAPI + ONNX Runtime scoring/token backend (`backend/`), and operational admin API (`/admin/*`).

---

## 1. Assets Protected

1. **Protected Portal Actions (`/portal-api/*`):**
   - `otp_request` (`high` sensitivity — prevents OTP SMS flooding / account enumeration)
   - `details_update` (`high` sensitivity — prevents automated demographic update spam)
   - `centre_search` (`medium` sensitivity — prevents high-rate scraping)
2. **User Privacy & Zero-PII Guarantees:** Typed characters, form field values, full client IPs, and persistent cross-day device identifiers must never be collected, logged, or persisted.
3. **Model & Policy Integrity:** Risk thresholds, ONNX model artifacts, and offline analyst feedback queues must be protected against score-oracle probing and data poisoning.

---

## 2. Adversary Profiles (Bot Tiers & Attack Classes)

| Adversary / Tier | Capabilities | Primary Target |
|---|---|---|
| **Tier 1 — Plain HTTP Flooder** (`simulator/tier1_http.py`) | Sends raw `POST` requests directly to `/portal-api/*` without executing JavaScript or obtaining a nonce/token, or sends empty `/v1/assess` probes. | OTP flooding, scraping, API availability. |
| **Tier 2 — Default Headless Browser** (`simulator/tier2_playwright.py`) | Runs Playwright/Selenium with default settings (`navigator.webdriver = true`, software WebGL, `0` plugins) using direct `page.fill()` / `page.click()`. | Bypassing simple client-side JS checks. |
| **Tier 3 — Stealth Scripted Browser** (`simulator/tier3_stealth.py`) | Hides `navigator.webdriver`, spoofs headers/platform partially, and injects linear mouse steps and fixed-interval keystrokes. | Bypassing deterministic rule checks (`R02`). |
| **Tier 4 — Human-Like Mimicry Bot** (`simulator/tier4_humanlike.py`) | Generates cubic Bezier mouse paths with smoothstep easing and Gaussian jitter plus randomised typing delays; attempts step-up hold timing. | Evading kinematic ML models and step-up verification. |
| **Replay / Tamper / Flood Adversary** (`loadtest/runner.py`, `backend/tests/test_tokens.py`) | Captures and replays valid human nonces, traces, or `X-Human-Token` JWTs across actions or IPs; sends oversized (`>64 KB`), malformed, or high-rate `/v1/nonce` and `/v1/assess` floods. | Token reuse, cross-endpoint escalation, CPU/memory exhaustion. |
| **Model / Feedback Poisoning Adversary** | Submits crafted traffic to probe numeric risk scores or poison future training data. | Threshold reverse-engineering, model degradation. |

---

## 3. Threat-to-Mitigation Matrix

| Threat | Mitigation Implemented | Verification Evidence |
|---|---|---|
| **Direct API abuse without browser** (Tier 1) | `require_human_token(expected_action)` enforces signed `X-Human-Token` on all `/portal-api/*` routes; empty assess payloads fire `R01_NO_PAYLOAD` (`w=0.80`). | `results/system/sim_summary.csv` (`100%` Tier 1 blocked); `loadtest_summary.md` (`200/200` `401` on `protected_endpoint_flood`). |
| **Headless & tampered browsers** (Tier 2 / Tier 3) | Rules `R02`–`R12` check `webdriver`, UA/platform/Client-Hints consistency, software WebGL, desktop plugins, viewport anomalies, native-function integrity, untrusted DOM events (`isTrusted === false`), and too-fast submission (`< 200 ms`). | `backend/tests/test_rules.py`; `results/system/rule_layer_ablation.csv` (`100%` Tier 2 & Tier 3 caught). |
| **Mechanical & Bezier behavioural bots** (Tier 3 / Tier 4) | Calibrated LightGBM mouse model (`120` features) + Logistic Regression keyboard model (`31` features) + `press_hold` step-up challenge (`800–1500 ms` random duration). | `results/system/sim_summary.csv` (`100%` Tier 3, `92%` Tier 4 caught); `results/mouse/lobo_evaluation.csv`. |
| **Nonce & trace replay** | `/v1/nonce` issues 32-byte random single-use nonces bound to `HMAC(/24 IP + UA)` and atomically consumed via `get_and_delete` on first `/v1/assess`. | `backend/tests/test_nonce.py` (`23/23` passed). |
| **JWT forgery, expiry, replay, or cross-action reuse** | `HS256`/`RS256`/`ES256` signature check, short TTL (`60–120 s`), strict `act == expected_action` check (`403 action_mismatch`), and single-use `jti` consumption (`401 token_already_used`). | `backend/tests/test_tokens.py` (`11/11` passed). |
| **Request flooding & payload DoS** | `MaxBodySizeMiddleware` rejects `> 64 KB` bodies with `413` before JSON parsing; Pydantic v2 caps `<= 600` mouse points & `<= 300` key events (`422`); sliding-window rate limits (`R13`) throttle floods with `429` + `Retry-After`. | `results/system/loadtest_summary.md` (`0/460` malicious reached API, `0` `5xx` across `630` requests); `backend/tests/test_ratelimit.py`. |
| **Score-oracle gradient probing** | `/v1/assess` and `/v1/assess/challenge` return only `decision` and coarse `band` (`low`/`medium`/`high`); exact numeric scores are never returned to untrusted clients. | `backend/tests/test_api.py`; `docs/api.md`. |
| **Feedback-queue training poisoning** | `/admin/feedback` is protected by `ADMIN_API_KEY` (SSO/RBAC in production) and enforces `training_policy = "stored_only_never_auto_trained"`; human review is required before any offline retraining. | `backend/app/admin.py`; `backend/tests/test_admin_api.py`. |
| **PII leakage / keylogging** | SDK drops key identities inside `keyClass()`; Pydantic rejects raw characters and extra portal fields (`extra="forbid"`); rotating ephemeral `X-Session-Id` + daily-salted `session_hash` + `/24` IP truncation + 7d/30d TTL purge. | `backend/tests/test_privacy_scan.py`; `backend/tests/test_session_privacy.py`; `backend/tests/test_retention.py`. |
| **Simulator misuse against external targets** | `simulator/safety.py` enforces `simulator/allowlist.txt` (localhost-only) and unconditionally rejects `.gov`, `.nic.in`, and `uidai` substrings in both `simulator/` and `loadtest/`. | `backend/tests/test_simulator_safety.py`; `backend/tests/test_loadtest.py`. |

---

## 4. Explicit Non-Goals & Residual Risks

1. **Human-operated CAPTCHA farms / click farms:** Behavioural bot detection distinguishes automated scripts from human motor control; a real human paid to solve flows will exhibit human kinematics and is outside scope.
2. **Network-level volumetric DDoS (L3/L4/SYN floods):** BotGuard operates at the application layer (L7) and does not replace edge CDN/WAF rate-limiting or DDoS scrubbing.
3. **Adversarial generative trajectories:** As shown in `results/mouse/lobo_evaluation.csv`, held-out adversarial GAN trajectories (`delbot_mouse:gan`, `0.4872` LOBO ROC-AUC) can evade a mouse-only model trained without GAN examples. Defence-in-depth (combining rules, multi-modality, step-up challenges, and rate limits) raises attacker cost rather than guaranteeing 100% prevention.
4. **Client-side signal spoofing:** Any browser-originated signal can be forged by a sufficiently instrumented browser engine. Passive scoring is designed to make large-scale automation economically expensive, not cryptographically impossible.
5. **Admin API authentication in prototype:** Static `ADMIN_API_KEY` is acceptable only for the local student prototype; production deployments must place `/admin/*` behind SSO/OIDC and RBAC.

# BotGuard System Architecture (SIH1672)

## 1. Overview

BotGuard is a passive behavioural bot-detection and adaptive risk-scoring prototype designed to replace visual/audio CAPTCHA puzzles for legitimate desktop users on a **local mock resident portal** (`DEMO — not a government portal`).

The system consists of four decoupled layers:
1. **Browser SDK (`sdk/`, `@botguard/sdk`):** Zero-dependency TypeScript library (~16.2 KB gzipped ESM, ~14.9 KB gzipped UMD) with React bindings (`@botguard/sdk/react`). Passively collects bounded mouse trajectories (`<= 600` points), privacy-safe keystroke timings (`key_class` + `down_ms`/`up_ms` only, `<= 300` events, never character identities), timing/scroll/focus signals, and coarse environment integrity checks. Supports both raw-window transport (`sendRawTrace: true`) and optional in-browser feature extraction (`sendRawTrace: false`, verified to `< 1e-9` parity with Python).
2. **Risk Scoring, Policy & Token Backend (`backend/app/`):** FastAPI + ONNX Runtime service that issues single-use context-bound nonces (`/v1/nonce`), enforces sliding-window rate limits (`R13`) and body-size caps (`64 KB`), extracts `120` mouse features and `31` keyboard features via the shared `botguard_ml.features` package (or consumes client-extracted feature maps), runs calibrated ONNX inference (`mouse-v1` LightGBM + `keyboard-v1` Logistic Regression; `touch: null` because Phase 8 was skipped), evaluates `R01`–`R13` deterministic rules, fuses active modalities via `fusion-v1` without penalising missing modalities, maps `max(model_score, rule_score)` through `backend/config/policy.yaml` to `allow | challenge | deny`, and issues short-lived single-use `X-Human-Token` JWTs (`HS256` / `RS256` / `ES256`).
3. **Mock Protected Portal & Accessible Step-Up UI (`portal/`, `sdk/src/challenge.ts`):** React + Vite mock resident portal (`Landing`, `Resident login`, `Update details`, `Centre search`) calling `/portal-api/otp/request`, `/portal-api/details/update`, and `/portal-api/centres/search` protected by `require_human_token(expected_action)`. Medium-risk (`challenge`) responses open a WCAG 2.1 AA press-and-hold modal (`800–1500 ms` server-chosen hold) with an explicit single-press keyboard accessibility alternative (`Use Keyboard Single-Press Verify`) and zero visual puzzles.
4. **Operational Admin Dashboard & Retention Enforcement (`portal/src/pages/AdminDashboardPage.tsx`, `dashboard/`, `backend/app/admin.py`, `backend/app/retention.py`):** API-key-protected (`/admin/*`) operational observability (RPM, allow/challenge/deny split, latency percentiles, score histogram with threshold lines, derived-feature session inspector, simulator tier results, FP/FN feedback queue, and automated/manual TTL retention purge).

---

## 2. End-to-End Request Flow

```text
Browser (@botguard/sdk)                  BotGuard Backend (/v1/*)                 Protected Portal (/portal-api/*)
     |                                              |                                           |
     |--- 1. GET /v1/nonce ------------------------>|                                           |
     |    Header: X-Session-Id (rotating, in-mem)   | (stores context hash: /24 IP + UA)        |
     |<-- { nonce, expires_in: 300 } ---------------|                                           |
     |                                              |                                           |
     | (Collects passive mouse/keyboard/env signals |                                           |
     |  or extracts features locally if configured) |                                           |
     |--- 2. POST /v1/assess { nonce, action, ... }>|                                           |
     |                                              |-- Enforces 64 KB cap + rate limits (R13)  |
     |                                              |-- Atomically consumes single-use nonce    |
     |                                              |-- Runs ONNX models + R01..R13 rules       |
     |                                              |-- Applies missing-modality & policy bands |
     |<-- { decision, band, token | challenge } ----| (raw numeric score never returned)        |
     |                                              |                                           |
     | [If decision == "challenge"]                 |                                           |
     | (Press-and-hold OR Keyboard single-press UI) |                                           |
     |--- 2b. POST /v1/assess/challenge ----------->|                                           |
     |<-- { decision: "allow", token } -------------|                                           |
     |                                              |                                           |
     |--- 3. POST /portal-api/otp/request --------->|------------------------------------------>|
     |       Header: X-Human-Token: <jwt>           |<-- require_human_token("otp_request") ----|
     |                                              |    Verifies sig, exp, act, single-use jti |
     |<-- 200 OK { status: "otp_sent" } ------------|-------------------------------------------|
```

---

## 3. Infrastructure & Storage Abstraction

BotGuard defaults to zero-external-dependency local operation while supporting production-like stores via environment variables:

| Component | Default (Dev / Tests) | Optional Production-Like Profile (`deploy/docker-compose.yml`) |
|---|---|---|
| Ephemeral state (nonces, challenges, single-use `jti`, sliding-window rate limits) | `STORE_BACKEND=memory` (`InMemoryStore`) | `STORE_BACKEND=redis` (`RedisStore`) |
| Audit & feedback database (`assessments`, `challenges`) | `DATABASE_URL=sqlite:///./botguard.db` | `DATABASE_URL=postgresql+psycopg://...` |
| Scheduled retention purge | `RetentionScheduler` background thread (`RETENTION_PURGE_INTERVAL_SECONDS`) or CLI `python -m app.retention --once` | Same scheduler or external cron calling `python -m app.retention --once` |

---

## 4. Fail-Safe & Degraded-Mode Policy (`P5-11`)

Configured in `backend/config/policy.yaml` under `fail_safe:` and surfaced in every `/v1/assess` response via `"degraded": true | false`:

| Failure Mode | Config Key (`policy.yaml`) | Default Policy | Runtime Behaviour |
|---|---|---|---|
| **Redis / Store Outage** | `fail_safe.redis_down` | `deny_high_allow_low` | High-sensitivity actions (`otp_request`, `details_update`) return `decision="deny"`, `band="high"`, `degraded=true`. Medium actions (`login`, `centre_search`) return `challenge`. Low actions (`page_view`) return `allow` with a stateless fallback token. |
| **ONNX Model Error** | `fail_safe.model_error` | `rules_only` | Scoring falls back automatically to deterministic rules (`R01`–`R13`), sets `degraded=true`, and applies the action's policy thresholds to `rule_score`. |
| **Database Outage** | `fail_safe.db_down` | `continue_and_buffer` | Assessment and token issuance proceed uninterrupted; audit records buffer in `DatabaseManager._buffer` (up to `1,000` entries) and flush via `flush_buffer()` when connectivity returns. |

---

## 5. Missing-Modality Fairness, Privacy & Security Boundaries

1. **Missing-Modality Fairness (`P3-10`, `P9-12`):** Only available modalities are fused (`mouse_score = None` is never treated as bot). Sessions with `0` mouse movement points and valid human keyboard navigation (short `<10`-key `Tab`/`Enter`/PIN flows or non-constant assistive typing with `untrusted_count == 0`) are capped at `MISSING_MOUSE_VALID_KB_MAX_SCORE = 0.50` (`medium` challenge band) so keyboard-only users are never auto-denied.
2. **Zero Keystroke Content Capture (`P3-01`, `P6-04`, `P9-06`):** Typed characters, raw keycodes, and form field values are dropped in the SDK (`keyClass()`), rejected by Pydantic schemas (`KeyBehaviour`), and verified absent from all DB tables and structured logs by `backend/tests/test_privacy_scan.py`.
3. **Ephemeral Session Rotation & Coarse IP Bucketing (`P9-05`):** The SDK generates an in-memory random `X-Session-Id` per page load (rotating every 15 minutes; never stored in cookies or `localStorage`). The backend hashes it with a daily-rotated server salt (`daily_session_salt`) and truncates IPs to `/24` (IPv4) or `/48` (IPv6).
4. **No Raw Trace Persistence & TTL Enforcement (`P5-08`, `P9-04`):** Raw `points` and `events` are never persisted. Optional derived feature summaries (`STORE_FEATURES_IN_DB=true`) are purged automatically after `FEATURE_TTL_SECONDS` (default 7 days), and assessment records after `ASSESSMENT_TTL_SECONDS` (default 30 days).
5. **No Raw Score Leakage (`P5-05`):** Untrusted clients receive only `decision` and `band`; numeric risk scores and derived feature contributors are restricted to structured audit logs and `/admin/*`.

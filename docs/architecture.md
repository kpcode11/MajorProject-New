# BotGuard System Architecture (SIH1672)

## 1. Overview

BotGuard is a passive behavioural bot-detection and adaptive risk-scoring system designed to protect high-traffic public portals (such as UIDAI Aadhaar services) without requiring traditional visual or audio CAPTCHAs for legitimate human users.

The system consists of three primary layers:
1. **Browser SDK (`sdk/`)**: Passively captures mouse trajectories, privacy-safe keystroke timing (`key_class` + dwell/flight timestamps only, never character identities), touch gestures, and browser environment integrity signals, then submits compact JSON payloads bound to a single-use server nonce.
2. **Risk Scoring & Token Backend (`backend/app/`)**: Validates nonces, enforces sliding-window rate limits, extracts 44 mouse features + 20 keyboard features via `botguard_ml`, runs calibrated ONNX Runtime inference (`mouse-v1` LightGBM + `keyboard-v1` Logistic Regression) and deterministic rule checks (`R01..R14`), maps fused risk scores to action-specific decision bands (`allow`, `challenge`, `deny`), and issues short-lived single-use JWT `X-Human-Token` passes.
3. **Protected Portal & Invisible Step-Up Challenge (`portal/`)**: Verifies `X-Human-Token` headers on sensitive endpoints (`/portal-api/otp/request`, `/portal-api/status/check`, `/portal-api/appointment/book`, etc.) via the `require_human_token(expected_action)` FastAPI dependency, and triggers an accessible press-and-hold or tap-target step-up challenge only for medium-risk (`challenge` band) requests.

---

## 2. End-to-End Request Flow

```
Browser (SDK)                              BotGuard Backend (/v1/*)                  Protected Portal (/portal-api/*)
     |                                                |                                             |
     |--- 1. GET /v1/nonce -------------------------->|                                             |
     |<-- { nonce, ttl_seconds: 120 } ----------------| (stores HMAC(UA + IP_bucket) in Store)      |
     |                                                |                                             |
     | (Collects passive mouse/keyboard/env signals)  |                                             |
     |--- 2. POST /v1/assess { nonce, action, ... } ->|                                             |
     |                                                |-- Atomically consumes single-use nonce      |
     |                                                |-- Extracts features + runs ONNX models      |
     |                                                |-- Evaluates R01..R14 environment/trace rules|
     |                                                |-- Fuses scores + applies action thresholds  |
     |<-- { decision: "allow", band: "low", token } --| (or decision: "challenge" / "deny")         |
     |                                                |                                             |
     |--- 3. POST /portal-api/otp/request ----------->|-------------------------------------------->|
     |       Header: X-Human-Token: <jwt>             |<-- require_human_token("otp_request") ------|
     |                                                |    Verifies signature, exp, act, single JTI |
     |<-- 200 OK { status: "otp_sent" } --------------|---------------------------------------------|
```

---

## 3. Fail-Safe & Degraded-Mode Policy (`P5-11`)

Public-facing identity portals must degrade gracefully during partial infrastructure outages without exposing high-sensitivity endpoints (such as OTP dispatch or appointment booking) to automated abuse. BotGuard implements a configurable fail-safe policy controlled by `backend/config/rules.yaml` under `fail_safe:` and surfaced in every `/v1/assess` response via `"degraded": true | false`.

| Failure Mode | Configuration Key (`rules.yaml`) | Default Policy | Runtime Behaviour |
|---|---|---|---|
| **Redis / Store Outage** (nonce & rate-limit state unavailable) | `fail_safe.redis_down` | `deny_high_allow_low` | High-sensitivity actions (`otp_request`, `appointment_book`, `login`, `status_check`, `Form_submit`) return `decision="deny"`, `band="high"`, `degraded=true`. Low-sensitivity actions (`page_view`, `centre_search`) return `decision="allow"`, `band="low"`, `degraded=true` with a stateless fallback token so browsing remains functional. |
| **ONNX Model Unavailable or Inference Error** | `fail_safe.model_error` | `rules_only` | Scoring falls back automatically to the deterministic rule engine (`R01..R14`), sets `degraded=true` in the response and audit record, and applies the action's policy thresholds to the rule score. |
| **Database Unavailable** (PostgreSQL / SQLite write failure) | `fail_safe.db_down` | `continue_and_buffer` | Assessment and token issuance proceed with zero user-facing disruption. Audit rows are buffered in an in-memory ring buffer (`DatabaseManager._buffer`, up to 1,000 entries) and flushed via `flush_buffer()` when database connectivity recovers. |

---

## 4. Privacy & Security Guarantees

1. **Zero Keystroke Content Capture**: Keyboard telemetry contains only `["letter" | "digit" | "backspace" | "space" | "enter" | "modifier" | "other", t_down_ms, t_up_ms]`. Raw characters, key codes, and input values are rejected at both the SDK and Pydantic schema validation boundary (`KeyBehaviour`).
2. **No Raw Behavioural Trace Persistence (`P5-08`)**: Only aggregate scores, decisions, top-3 contributing feature names, and optional TTL-limited derived feature vectors (`STORE_DERIVED_FEATURES=true`) are stored in `assessments`. Raw mouse coordinate arrays (`points`) and key timing lists (`events`) are stripped by `sanitize_derived_features()`.
3. **Coarse IP Bucketing (`P5-12`)**: Full client IP addresses are never written to logs or database rows. IPv4 addresses are truncated to `/24` (`203.0.113.0/24`) and IPv6 addresses to `/48` before rate-limiting, nonce context hashing, or structured JSON logging (`format_safe_log_record`).
4. **No Raw Score Leakage (`P5-02`, `P5-09`)**: `/v1/assess` and `/v1/assess/challenge` return only `decision` (`allow` | `challenge` | `deny`) and `band` (`low` | `medium` | `high`) to untrusted callers, preventing adversarial gradient estimation.


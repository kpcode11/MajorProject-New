# BotGuard Scoring, Portal & Admin API Specification (`v1`)

- **OpenAPI JSON (live FastAPI schema):** `/openapi.json`
- **Swagger UI:** `/docs`
- **Canonical contract fixture:** `data/fixtures/backend_contract_schema.json`

---

## 1. Public Risk Scoring & Verification Endpoints (`/v1/*`)

### 1.1 `GET /v1/nonce`
Issues a cryptographically random single-use nonce bound to the caller's User-Agent and coarse IP subnet (`/24` IPv4 or `/48` IPv6).

- **Rate Limit:** `RATE_LIMIT_NONCE_PER_MIN` (default `60/min` per coarse IP bucket and session).
- **Response (`200 OK`, `NonceResponse`):**
  ```json
  {
    "nonce": "r8K3vN9mQ2xL5pZ1wB4cT7yF0hJ6dG8s",
    "expires_in": 300
  }
  ```

### 1.2 `POST /v1/assess`
Consumes a single-use nonce, runs calibrated ONNX models (`mouse-v1`, `keyboard-v1`; `touch: null`) and deterministic environment rules (`R01`–`R13`), and returns a policy decision (`allow`, `challenge`, or `deny`).

- **Optional Header:** `X-Session-Id` (rotating ephemeral in-memory session identifier; hashed with a daily-rotated server salt).
- **Rate Limit:** `RATE_LIMIT_ASSESS_PER_MIN` (default `120/min` per coarse IP bucket and session).
- **Max Request Body Size:** `MAX_BODY_BYTES` (`65536` bytes; larger payloads rejected with `413 payload_too_large` before parsing).
- **Request (`AssessRequest`):**
  ```json
  {
    "nonce": "r8K3vN9mQ2xL5pZ1wB4cT7yF0hJ6dG8s",
    "action": "otp_request",
    "sdk_version": "1.0.0",
    "schema_version": 1,
    "env": {
      "ua_family": "chrome",
      "ua_major": 130,
      "ua_os": "windows",
      "platform": "Win32",
      "webdriver": false,
      "plugins_count": 5,
      "viewport_w": 1440,
      "viewport_h": 900,
      "webgl_renderer_class": "hardware"
    },
    "behaviour": {
      "device_class": "desktop",
      "mouse": {
        "points": [[756.0, 273.0, 191.0], [744.0, 273.0, 199.3]],
        "clicks": [],
        "untrusted_count": 0,
        "wheel_events": 1
      },
      "keys": {
        "events": [["digit", 100.0, 185.0], ["digit", 240.0, 320.0]],
        "paste_events": 0,
        "autofill_suspected": false,
        "untrusted_count": 0
      },
      "timing": {
        "ms_since_load": 3800.0,
        "ms_to_first_interaction": 191.0,
        "ms_since_nonce": 3400.0,
        "scroll_events": 1,
        "focus_changes": 2
      }
    }
  }
  ```
  *Local feature extraction mode (`sendRawTrace: false`):* `mouse.points` and `keys.events` may be empty `[]` when `mouse.features` / `mouse.feature_windows` and `keys.features` carry the pre-extracted numeric feature maps (`P9-08`).
- **Response (`200 OK`, `AssessResponse`):**
  - **Low Risk (`allow`):**
    ```json
    {
      "decision": "allow",
      "band": "low",
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "challenge": null,
      "request_id": "a1b2c3d4-...",
      "model_versions": {
        "mouse": "lightgbm-v1",
        "keyboard": "logistic_regression-v1",
        "touch": null,
        "fusion": "v1"
      },
      "degraded": false
    }
    ```
  - **Medium Risk (`challenge`):** `token` is `null` and `challenge` contains:
    ```json
    {
      "id": "8f14e45f-...",
      "type": "press_hold",
      "hold_ms": 1150,
      "expires_in": 60
    }
    ```
  - **High Risk (`deny`):** `decision: "deny"`, `band: "high"`, `token: null`, `challenge: null`.
  *(Exact numeric risk scores are never returned to untrusted clients.)*

### 1.3 `POST /v1/assess/challenge`
Verifies completion of a single-use step-up challenge (`press_hold` or keyboard single-press alternative) issued by `/v1/assess`, enforcing hold duration and timing bounds, and returns an `AssessResponse` (`allow` with single-use `X-Human-Token`, or `deny`).

- **Rate Limit:** `RATE_LIMIT_CHALLENGE_PER_MIN` and `RATE_LIMIT_CHALLENGE_SESSION_PER_MIN`.
- **Request (`ChallengeAssessRequest`):** `{ "nonce", "challenge_id", "action", "hold_start_ms", "hold_end_ms", "env"?, "behaviour"? }`.

### 1.4 `POST /v1/token/verify`
Verifies signature, expiration, action binding (`act == expected_action`), and atomically consumes the single-use `jti` claim for external/polyglot backends.

- **Request (`TokenVerifyRequest`):** `{ "token": "<jwt>", "expected_action": "otp_request" }`.
- **Response (`200 OK`, `TokenVerifyResponse`):** `{ "valid": true, "action": "otp_request", "band": "low", "reason": null }`.

### 1.5 `GET /v1/health`
Returns service liveness, loaded ONNX model versions (`touch: null`), store backend (`memory` or `redis`), and database connectivity (`db_ok`).

---

## 2. Mock Protected Portal Endpoints (`/portal-api/*`)

All mutating portal routes enforce `require_human_token(expected_action)` via the `X-Human-Token` header when `PROTECTION_MODE=passive` (bypassed only when `PROTECTION_MODE=off` for before/after demos) and reject extra/PII fields (`extra="forbid"`):

| Method & Path | Expected Action | Policy Class | Request Body (No Raw PII) |
|---|---|---|---|
| `POST /portal-api/otp/request` | `otp_request` | `high` | `{ "action": "otp_request", "identifier_length": 12 }` |
| `POST /portal-api/details/update` | `details_update` | `high` | `{ "action": "details_update", "fields_updated": ["name"], "city_code": "BENGALURU", "language_code": "EN", "confirmed": true }` |
| `POST /portal-api/centres/search` | `centre_search` | `medium` | `{ "action": "centre_search", "service_type": "ALL", "query_length": 6 }` |
| `GET /portal-api/stats` | *(read-only demo counter)* | — | Returns `protection_mode`, `accepted`, `rejected`, `by_action`, `by_reason`. |

---

## 3. Operational Admin Endpoints (`/admin/*`)

> **Authentication Note:** For this student research prototype, `/admin/*` endpoints are protected by a static API key (`ADMIN_API_KEY`, default `dev-admin-key`) supplied via `X-Admin-Key` or `Authorization: Bearer <key>`. Production deployments require SSO/OIDC/OAuth2 with role-based access control (RBAC).

| Method & Path | Purpose |
|---|---|
| `GET /admin/overview` | Requests/min, allow/challenge/deny split, p50/mean/p95 latency, degraded count, protection mode, loaded model versions. |
| `GET /admin/scores` | Risk score distribution histogram bins (`[0.0, 1.0]`) and active policy thresholds per sensitivity class. |
| `GET /admin/assessments` | Paginated assessment list filterable by `decision`, `action`, `limit`, `offset`. |
| `GET /admin/assessments/{id}` | Single session detail: decision, band, fired rules, top contributing derived features (no raw traces), challenge history. |
| `GET /admin/feedback` | Lists analyst-flagged `fp` / `fn` assessments (`training_policy: "stored_only_never_auto_trained"`). |
| `POST /admin/feedback` | Marks or clears `fp` / `fn` feedback on an assessment ID (stored for offline review only; never auto-trained). |
| `GET /admin/sim-results` | Aggregated bot simulator outcomes per tier from `results/system/sim_runs.jsonl`. |
| `GET /admin/privacy` | Retention TTL settings (`feature_ttl_days`, `assessment_ttl_days`), record counts, last purge summary, and privacy guarantees. |
| `POST /admin/privacy/purge` | Triggers an immediate retention purge via `backend/app/retention.py` and returns purged feature/assessment counts. |

---

## 4. Standard Error Envelope (`ErrorResponse`)

All `4xx` / `5xx` errors return:
```json
{
  "error": {
    "code": "invalid_or_expired_nonce",
    "message": "Nonce verification failed: invalid_or_expired_nonce",
    "request_id": "req-1234"
  }
}
```

| HTTP Status | Error Code | Description |
|---|---|---|
| `401 Unauthorized` | `invalid_or_expired_nonce` / `nonce_context_mismatch` | Nonce missing, expired, replayed, or bound to a different IP bucket/UA |
| `401 Unauthorized` | `missing_token` / `expired_token` / `token_already_used` / `invalid_token` | Missing, expired, replayed, or invalid `X-Human-Token` |
| `401 Unauthorized` | `unauthorized_admin` | Missing or invalid `X-Admin-Key` / Bearer token on `/admin/*` |
| `403 Forbidden` | `action_mismatch` | Token `act` claim does not match the protected route's `expected_action` |
| `413 Content Too Large` | `payload_too_large` | Request body exceeds `MAX_BODY_BYTES` (`64 KB`) |
| `422 Unprocessable Entity` | `validation_error` | Schema constraint violation (e.g., `>600` mouse points, raw character in `key_class`, or extra PII field) |
| `429 Too Many Requests` | `rate_limit_exceeded` | Sliding-window rate limit exceeded (includes `Retry-After` header) |

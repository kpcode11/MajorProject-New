# BotGuard Scoring & Token API Specification (`v1`)

Base URL: `/v1`  
OpenAPI JSON (served automatically by FastAPI): `/openapi.json`

---

## 1. Endpoints

### 1.1 `GET /v1/nonce`
Issues a cryptographically random single-use nonce bound to the caller's User-Agent and coarse IP subnet (`/24` IPv4 or `/48` IPv6).

- **Rate Limit**: `RATE_LIMIT_NONCE_PER_MIN` (default `60/min` per coarse IP bucket).
- **Response (`200 OK`, `NonceResponse`)**:
  ```json
  {
    "nonce": "r8K3vN9mQ2xL5pZ1wB4cT7yF0hJ6dG8s",
    "ttl_seconds": 120
  }
  ```

---

### 1.2 `POST /v1/assess`
Consumes a single-use nonce, evaluates passive behavioural telemetry and browser environment signals via ONNX models (`mouse-v1`, `keyboard-v1`) and deterministic rules (`R01..R14`), and returns an access decision (`allow`, `challenge`, or `deny`).

- **Rate Limit**: `RATE_LIMIT_ASSESS_PER_MIN` (default `30/min` per coarse IP bucket and per `session_id`).
- **Max Request Body Size**: `MAX_BODY_BYTES` (`65536` bytes; larger payloads are rejected with `413 payload_too_large` before parsing).
- **Request (`AssessRequest`)**:
  ```json
  {
    "nonce": "r8K3vN9mQ2xL5pZ1wB4cT7yF0hJ6dG8s",
    "action": "otp_request",
    "session_id": "sess-0192f0",
    "env": {
      "ua_family": "Chrome",
      "ua_os": "Windows",
      "platform": "Win32",
      "webdriver": false,
      "plugins_count": 5,
      "viewport_w": 1440,
      "viewport_h": 900,
      "has_mouse": true,
      "has_keyboard": true
    },
    "behaviour": {
      "device_class": "desktop",
      "mouse": {
        "points": [[756.0, 273.0, 191.0], [744.0, 273.0, 199.3]]
      },
      "keys": {
        "events": [["letter", 100.0, 185.0], ["letter", 240.0, 320.0]]
      }
    }
  }
  ```
- **Response (`200 OK`, `AssessResponse`)**:
  - **Low Risk (`allow`)**:
    ```json
    {
      "request_id": "a1b2c3d4-...",
      "decision": "allow",
      "band": "low",
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "challenge": null,
      "degraded": false
    }
    ```
  - **Medium Risk (`challenge`)**:
    ```json
    {
      "request_id": "a1b2c3d4-...",
      "decision": "challenge",
      "band": "medium",
      "token": null,
      "challenge": {
        "id": "8f14e45f-...",
        "type": "press_hold",
        "hold_ms": 1400,
        "target_x": null,
        "target_y": null,
        "ttl_seconds": 120
      },
      "degraded": false
    }
    ```
  - **High Risk (`deny`)**:
    ```json
    {
      "request_id": "a1b2c3d4-...",
      "decision": "deny",
      "band": "high",
      "token": null,
      "challenge": null,
      "degraded": false
    }
    ```
  *(Note: Raw numeric risk scores are intentionally excluded from `AssessResponse`.)*

---

### 1.3 `POST /v1/assess/challenge`
Verifies completion of a step-up challenge (`press_hold` or `tap_target`) issued by `/v1/assess` and issues a single-use `X-Human-Token` (`band="medium"`) upon success.

- **Request (`ChallengeAssessRequest`)**:
  ```json
  {
    "nonce": "k2M9pQ4xT7vL1nZ8wB3cR6yF5hJ0dG2s",
    "challenge_id": "8f14e45f-...",
    "action": "otp_request",
    "hold_start_ms": 1000.0,
    "hold_end_ms": 2450.0
  }
  ```
- **Response (`200 OK`, `ChallengeAssessResponse`)**:
  ```json
  {
    "request_id": "f4e3d2c1-...",
    "decision": "allow",
    "band": "medium",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```

---

### 1.4 `POST /v1/token/verify`
Verifies and atomically consumes a single-use `X-Human-Token` JWT for a specified `expected_action`.

- **Request (`TokenVerifyRequest`)**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expected_action": "otp_request"
  }
  ```
- **Response (`200 OK`, `TokenVerifyResponse`)**:
  ```json
  {
    "valid": true,
    "action": "otp_request",
    "band": "low",
    "reason": null
  }
  ```

---

### 1.5 `GET /v1/health`
Returns liveness, loaded ONNX model versions, store backend status, and database connectivity.

- **Response (`200 OK`, `HealthResponse`)**:
  ```json
  {
    "status": "ok",
    "model_versions": {
      "mouse": "lightgbm-v1",
      "keyboard": "logistic_regression-v1",
      "fusion": "v1"
    },
    "store_backend": "memory",
    "db_ok": true
  }
  ```

---

## 2. Standard Error Envelope (`ErrorResponse`)

All `4xx` / `5xx` errors return:
```json
{
  "error": {
    "code": "invalid_or_expired_nonce",
    "message": "Nonce is missing, expired, or has already been used.",
    "request_id": "req-1234"
  }
}
```

| HTTP Status | Error Code | Description |
|---|---|---|
| `401 Unauthorized` | `invalid_or_expired_nonce` | Nonce missing, expired (`>120s`), or replayed |
| `401 Unauthorized` | `nonce_context_mismatch` | Caller User-Agent or `/24` IP subnet differs from nonce issuance |
| `401 Unauthorized` | `missing_human_token` / `token_expired` / `token_replayed_or_revoked` | Protected portal route called without a valid single-use `X-Human-Token` |
| `403 Forbidden` | `action_mismatch` | Token `act` claim does not match the protected route's `expected_action` |
| `413 Content Too Large` | `payload_too_large` | Request body exceeds `MAX_BODY_BYTES` (`64 KB`) |
| `422 Unprocessable Entity` | `validation_error` | Schema constraint violation (e.g., `>600` mouse points or invalid `key_class`) |
| `429 Too Many Requests` | `rate_limit_exceeded` | Sliding-window rate limit exceeded (includes `Retry-After` header) |


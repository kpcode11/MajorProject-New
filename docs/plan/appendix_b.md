## Appendix B — API contract

### B.1 Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/v1/nonce` | GET | none (rate-limited) | Issue single-use nonce |
| `/v1/assess` | POST | nonce in body | Score session; return decision |
| `/v1/assess/challenge` | POST | nonce + `challenge_id` | Re-score after step-up |
| `/v1/token/verify` | POST | service API key | Optional remote token check |
| `/v1/health` | GET | none | Liveness, model versions |
| `/admin/*` | various | admin API key | Dashboard data |

Error format: `{"error": {"code": "invalid_nonce", "message": "...", "request_id": "..."}}`.

### B.2 Environment signals (`env`)

```json
{
  "webdriver": false,
  "ua_family": "chrome",
  "ua_major": 126,
  "ua_os": "windows",
  "platform": "Win32",
  "hints_brands": ["Chromium", "Google Chrome"],
  "hints_platform": "Windows",
  "languages_count": 2,
  "lang_primary": "en-IN",
  "timezone_offset_min": -330,
  "screen_w_bucket": 1920,
  "screen_h_bucket": 1080,
  "viewport_w": 1280,
  "viewport_h": 720,
  "outer_w": 1296,
  "outer_h": 800,
  "dpr_bucket": 1,
  "hw_concurrency_bucket": 8,
  "device_memory_bucket": 8,
  "webgl_renderer_class": "hardware",
  "plugins_count": 5,
  "max_touch_points": 0,
  "touch_event_supported": false,
  "native_fn_integrity_ok": true,
  "storage_available": true,
  "visibility": "visible"
}
```

All values are coarse/bucketed. No unique fingerprint hash is computed.

### B.3 Behaviour payload (`behaviour`)

```json
{
  "mouse": {
    "points": [[x, y, t_ms], "..."],
    "clicks": [[x, y, down_ms, up_ms], "..."],
    "untrusted_count": 0,
    "wheel_events": 3
  },
  "keys": {
    "events": [["letter", down_ms, up_ms], "..."],
    "paste_events": 0,
    "autofill_suspected": false
  },
  "touch": {
    "gestures": [{"type": "swipe", "points": [[x, y, t_ms, pressure, size], "..."]}]
  },
  "timing": {
    "ms_since_load": 8450,
    "ms_to_first_interaction": 1320,
    "ms_since_nonce": 7900,
    "scroll_events": 4,
    "focus_changes": 2
  },
  "device_class": "desktop"
}
```

Limits: at most 600 mouse points, 300 key events, 20 gestures with 100 points each. Key classes only: `letter | digit | space | punct | modifier | enter | backspace | other`.

### B.4 Responses and token

`POST /v1/assess` request:

```json
{ "nonce": "...", "action": "otp_request", "sdk_version": "1.0.0", "schema_version": 1,
  "client_ts": 1760000000000, "env": { }, "behaviour": { } }
```

Response:

```json
{ "decision": "allow", "band": "low", "token": "eyJ...", "challenge": null,
  "request_id": "uuid", "model_versions": {"mouse": "lgbm-1.0.0", "keyboard": "lgbm-1.0.0", "fusion": "1.0.0"},
  "degraded": false }
```

`decision` is one of `allow`, `challenge`, `deny`. When `challenge`, `challenge` contains `{ "id": "...", "type": "press_hold", "hold_ms": 1100, "expires_in": 60 }` and `token` is null.

Token claims: `iss`, `aud`, `act` (action), `iat`, `exp`, `jti`, `band`.

### B.5 Database schema

```sql
CREATE TABLE assessments (
  id UUID PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_hash TEXT NOT NULL,
  action TEXT NOT NULL,
  device_class TEXT,
  score REAL NOT NULL,
  band TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('allow','challenge','deny')),
  rules_fired TEXT[] NOT NULL DEFAULT '{}',
  top_factors JSONB NOT NULL DEFAULT '[]',
  model_versions JSONB NOT NULL,
  latency_ms REAL,
  degraded BOOLEAN NOT NULL DEFAULT FALSE,
  feedback TEXT CHECK (feedback IN ('fp','fn')),
  features JSONB,                    -- derived features only; optional; TTL-limited
  features_expires_at TIMESTAMPTZ
);
CREATE INDEX assessments_ts_idx ON assessments (ts);
CREATE INDEX assessments_decision_ts_idx ON assessments (decision, ts);

CREATE TABLE challenges (
  id UUID PRIMARY KEY,
  assessment_id UUID REFERENCES assessments(id),
  type TEXT NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  outcome TEXT
);
```

---

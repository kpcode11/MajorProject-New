# Security Checks & Audit Report (`results/system/security_checks.md`)

**Task:** `P10-05` — Replay/tamper/oversize/rate-limit security test suite, `bandit` static analysis, `pip-audit`, and `npm audit`.

---

## 1. Security Test Suite (`72 / 72` Passed)

| Category | Test Module(s) | Tests | Status | Key Verified Controls |
| :--- | :--- | ---: | :--- | :--- |
| `nonce_single_use_and_context_binding` | `backend/tests/test_nonce.py` | 23 | **PASSED** | Single-use atomic get_and_delete prevents nonce replay; Context hash binding (/24 IPv4 or /48 IPv6 bucket + UA) rejects cross-context reuse; Expired nonces rejected with 401 invalid_or_expired_nonce; Daily-rotated salted session hashes prevent cross-day linkage |
| `jwt_tamper_expiry_action_and_jti_replay` | `backend/tests/test_tokens.py` | 11 | **PASSED** | HS256, RS256, and ES256 signature verification rejects tampered payloads/headers; Single-use JTI consumption in Store blocks token replay (401 token_already_used); Action-claim binding (act) rejects cross-endpoint token reuse (401 action_mismatch); Expired tokens rejected (401 expired_token) |
| `sliding_window_rate_limiting` | `backend/tests/test_ratelimit.py` | 5 | **PASSED** | Per-IP-bucket and per-session sliding-window caps on /v1/nonce, /v1/assess, and /v1/assess/challenge; 429 Too Many Requests with Retry-After header when threshold exceeded |
| `oversize_malformed_and_api_hardening` | `backend/tests/test_api.py` | 14 | **PASSED** | MaxBodySizeMiddleware rejects requests > 64 KB with 413 payload_too_large before JSON parsing; Pydantic v2 strict bounds reject >600 mouse points, >300 key events, or raw characters with 422; Graceful fail-safe degradation when Store/Redis or ONNX model is unavailable |
| `stepup_challenge_anti_replay_and_timing_bounds` | `backend/tests/test_challenge.py` | 5 | **PASSED** | Single-use challenge_id deleted on first attempt; Hold duration below server-chosen hold_ms or impossible zero-jitter hold rejected; Expired or unknown challenge_id rejected with 401 |
| `protected_portal_gateway_and_privacy_scans` | `backend/tests/test_portal_api.py, test_privacy_scan.py, test_session_privacy.py, test_loadtest.py` | 14 | **PASSED** | All /portal-api/* routes enforce require_human_token(action); Extra/raw PII fields on portal endpoints rejected with 422 (extra='forbid'); Zero typed characters, form values, full IPs, or persistent IDs in DB tables or logs; 0/460 malicious flood requests reached protected API across 4 loadtest scenarios |

---

## 2. Static Application Security Testing (`bandit -r backend/app`)

- **Lines of code scanned:** `5,557` across `backend/app/*.py`
- **Post-remediation scan result:** **`0 HIGH`, `0 MEDIUM`, `0 LOW`** (`exit_code = 0`)
- **Initial findings triaged & remediated:**
  - B101 (LOW, 2 occurrences in backend/app/tokens.py lines 209 & 288): assert used after P-256 scalar multiplication; replaced with explicit runtime if-check raising InvalidKeyError/ValueError so python -O cannot strip the check.
  - B104 (MEDIUM, 3 occurrences in backend/app/nonce.py lines 113 & 254 and backend/app/ratelimit.py line 84): false positive on fallback IP string literal '0.0.0.0' passed to _coarsen_ip() when client_ip is absent (not a socket bind); annotated with # nosec B104.
  - B105 (LOW, 1 occurrence in backend/app/config.py line 23): development default placeholder _DEFAULT_DEV_JWT_SECRET = 'change-me-in-production' (overridden via JWT_SECRET env var in deployments); annotated with # nosec B105.

---

## 3. Python Dependency Audit (`pip-audit`)

| Package | Installed | Advisory ID | Fix Version | Impact Assessment |
| :--- | :--- | :--- | :--- | :--- |
| `certifi` | `2026.7.22` | `PYSEC-2026-4320` | `2026.10.18` | Transitive dependency of httpx (used only in dev/test). The FastAPI scoring backend makes zero outbound HTTPS requests. |
| `opentelemetry-api` | `1.45.1` | `CVE-2026-126360` | `1.45.2` | Transitive dependency; TraceContextTextMapPropagator.extract() is never called by BotGuard. |

---

## 4. Node.js Dependency Audit (`npm audit`)

| Package Workspace | Production Runtime Deps | Production Vulnerabilities | Dev-Tooling Advisories | Notes |
| :--- | ---: | ---: | ---: | :--- |
| `sdk/` (`@botguard/sdk`) | `0` | **`0`** | `14` | @botguard/sdk has zero runtime dependencies (dependencies: {}). All 14 npm advisories are in dev-only build/lint/test packages (minimatch in eslint/typescript-eslint and picomatch in vite/vitest) and are never shipped in dist/botguard.js or dist/botguard.umd.cjs. |
| `portal/` (`@botguard/portal`) | `3` | **`0`** | `15` | Runtime dependencies (@botguard/sdk, react, react-dom) have 0 vulnerabilities. All 15 advisories are in dev-only Vite/Vitest/ESLint globbing packages (minimatch, picomatch). |

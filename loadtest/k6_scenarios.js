/**
 * k6 load-test scenarios for BotGuard (Phase 10, P10-04).
 *
 * Covers the four required scenarios:
 *  1. `normal_mix`
 *  2. `protected_endpoint_flood`
 *  3. `nonce_flood`
 *  4. `malformed_assess_flood`
 *
 * Safety: Refuses to run against any host outside `127.0.0.1` / `localhost`.
 */
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BOTGUARD_BASE_URL || 'http://127.0.0.1:8000';
if (
  !BASE_URL.startsWith('http://127.0.0.1') &&
  !BASE_URL.startsWith('http://localhost')
) {
  throw new Error(`Refusing non-local loadtest target: ${BASE_URL}`);
}

export const options = {
  scenarios: {
    normal_mix: {
      executor: 'constant-vus',
      vus: 4,
      duration: '10s',
      exec: 'runNormalMix',
    },
    protected_endpoint_flood: {
      executor: 'constant-vus',
      vus: 4,
      duration: '10s',
      exec: 'runProtectedFlood',
    },
    nonce_flood: {
      executor: 'constant-vus',
      vus: 4,
      duration: '10s',
      exec: 'runNonceFlood',
    },
    malformed_assess_flood: {
      executor: 'constant-vus',
      vus: 4,
      duration: '10s',
      exec: 'runMalformedAssessFlood',
    },
  },
};

export function runProtectedFlood() {
  const res = http.post(
    `${BASE_URL}/portal-api/otp/request`,
    JSON.stringify({ action: 'otp_request', identifier_length: 12 }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(res, { 'protected flood rejected with 401': (r) => r.status === 401 });
}

export function runNonceFlood() {
  const res = http.get(`${BASE_URL}/v1/nonce`);
  check(res, { 'nonce flood 200 or 429': (r) => r.status === 200 || r.status === 429 });
}

export function runMalformedAssessFlood() {
  const res = http.post(
    `${BASE_URL}/v1/assess`,
    JSON.stringify({ nonce: 'bad', action: 'otp_request', behaviour: { mouse: { points: [[1]] } } }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(res, { 'malformed assess rejected 4xx': (r) => r.status >= 400 && r.status < 500 });
}

export function runNormalMix() {
  const nRes = http.get(`${BASE_URL}/v1/nonce`);
  check(nRes, { 'nonce 200': (r) => r.status === 200 });
}

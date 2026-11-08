import { describe, expect, it, vi } from 'vitest';
import { HARD_LIMITS, resolveConfig } from '../src/config';
import {
  type AssessResponse,
  BotGuardTransportError,
  buildAssessPayload,
  buildChallengePayload,
  fetchNonce,
  postAssess,
  postChallenge,
  safeAssess,
  safeSubmitChallenge,
  utf8ByteLength,
} from '../src/transport';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const SAMPLE_ALLOW_RESPONSE: AssessResponse = {
  decision: 'allow',
  band: 'low',
  token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test',
  challenge: null,
  request_id: 'req-123',
  model_versions: { mouse: 'lgbm-1.0.0', keyboard: 'lr-1.0.0', fusion: '1.0.0' },
  degraded: false,
};

describe('buildAssessPayload & buildChallengePayload', () => {
  it('populates required schema fields and slices excess trace items', () => {
    const points: [number, number, number][] = Array.from({ length: 700 }, (_, i) => [
      i,
      i,
      i * 10,
    ]);
    const payload = buildAssessPayload(
      {
        nonce: 'nonce-abc',
        action: 'otp_request',
        env: { webdriver: false, ua_family: 'chrome' },
        behaviour: {
          mouse: { points, clicks: [], untrusted_count: 0, wheel_events: 2 },
          device_class: 'desktop',
        },
      },
      () => 1_760_000_000_000,
    );

    expect(payload.nonce).toBe('nonce-abc');
    expect(payload.action).toBe('otp_request');
    expect(payload.sdk_version).toBe('1.0.0');
    expect(payload.schema_version).toBe(1);
    expect(payload.client_ts).toBe(1_760_000_000_000);
    expect(payload.behaviour?.mouse?.points.length).toBe(HARD_LIMITS.maxMousePoints);
    expect(payload.behaviour?.mouse?.points[0]).toEqual([100, 100, 1000]);
    expect(utf8ByteLength(JSON.stringify(payload))).toBeLessThanOrEqual(HARD_LIMITS.maxBodyBytes);
  });

  it('trims trace arrays if the serialised payload exceeds 64 KB', () => {
    // High-precision floats make JSON longer so 600 points + 600 clicks + 300 keys + 20 gestures > 64 KB
    const points: [number, number, number][] = Array.from({ length: 600 }, (_, i) => [
      1234.567890123 + i,
      9876.543210987 + i,
      100000.1234567 + i,
    ]);
    const clicks: [number, number, number, number][] = Array.from({ length: 600 }, (_, i) => [
      1234.567890123 + i,
      9876.543210987 + i,
      100000.1234567 + i,
      100050.7654321 + i,
    ]);
    const keys: ['letter', number, number][] = Array.from({ length: 300 }, (_, i) => [
      'letter',
      100000.1234567 + i,
      100080.7654321 + i,
    ]);
    const payload = buildAssessPayload({
      nonce: 'n-large',
      action: 'login',
      behaviour: {
        mouse: { points, clicks, untrusted_count: 0, wheel_events: 0 },
        keys: { events: keys, paste_events: 0, autofill_suspected: false, untrusted_count: 0 },
      },
    });
    expect(utf8ByteLength(JSON.stringify(payload))).toBeLessThanOrEqual(HARD_LIMITS.maxBodyBytes);
  });

  it('builds challenge payloads with hold start/end timestamps', () => {
    const challengePayload = buildChallengePayload({
      nonce: 'nonce-chal',
      challengeId: 'chal-99',
      action: 'otp_request',
      holdStartMs: 1_000,
      holdEndMs: 2_150,
    });
    expect(challengePayload).toEqual({
      nonce: 'nonce-chal',
      challenge_id: 'chal-99',
      action: 'otp_request',
      sdk_version: '1.0.0',
      hold_start_ms: 1_000,
      hold_end_ms: 2_150,
    });
  });
});

describe('transport requests, retries and timeouts', () => {
  it('fetches a nonce and posts an assessment on the happy path', async () => {
    const config = resolveConfig({ endpoint: 'http://127.0.0.1:8000' });
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-1', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW_RESPONSE));

    const nonceRes = await fetchNonce(config, { fetchImpl: fetchMock });
    expect(nonceRes).toEqual({ nonce: 'n-1', expires_in: 300 });

    const payload = buildAssessPayload({ nonce: nonceRes.nonce, action: 'login' });
    const assessRes = await postAssess(config, payload, { fetchImpl: fetchMock });
    expect(assessRes).toEqual(SAMPLE_ALLOW_RESPONSE);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0]?.[0]).toBe('http://127.0.0.1:8000/v1/nonce');
    expect(fetchMock.mock.calls[1]?.[0]).toBe('http://127.0.0.1:8000/v1/assess');
  });

  it('retries on 503 and 429 with exponential backoff and succeeds', async () => {
    const config = resolveConfig({ maxRetries: 2, retryBaseDelayMs: 100 });
    const delays: number[] = [];
    const sleep = async (ms: number): Promise<void> => {
      delays.push(ms);
    };
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        jsonResponse(
          { error: { code: 'service_unavailable', message: 'busy', request_id: 'r1' } },
          503,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse(
          { error: { code: 'rate_limited', message: 'slow down', request_id: 'r2' } },
          429,
        ),
      )
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-ok', expires_in: 300 }));

    const res = await fetchNonce(config, { fetchImpl: fetchMock, sleep });
    expect(res.nonce).toBe('n-ok');
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(delays).toEqual([100, 200]);
  });

  it('does not retry on 400/422 client validation errors', async () => {
    const config = resolveConfig({ maxRetries: 2, retryBaseDelayMs: 50 });
    const sleep = vi.fn(async () => undefined);
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        jsonResponse(
          { error: { code: 'invalid_nonce', message: 'Nonce expired', request_id: 'req-bad' } },
          400,
        ),
      );

    await expect(
      postAssess(config, buildAssessPayload({ nonce: 'bad', action: 'login' }), {
        fetchImpl: fetchMock,
        sleep,
      }),
    ).rejects.toMatchObject({
      name: 'BotGuardTransportError',
      status: 400,
      code: 'invalid_nonce',
      requestId: 'req-bad',
      retryable: false,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });

  it('aborts hung requests after requestTimeoutMs and retries', async () => {
    const config = resolveConfig({ requestTimeoutMs: 100, maxRetries: 1, retryBaseDelayMs: 0 });
    const fetchMock = vi.fn<typeof fetch>((_input, init) => {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          const abortErr = new Error('The operation was aborted.');
          abortErr.name = 'AbortError';
          reject(abortErr);
        });
      });
    });

    await expect(fetchNonce(config, { fetchImpl: fetchMock })).rejects.toThrowError(
      BotGuardTransportError,
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('posts challenge payloads to /v1/assess/challenge', async () => {
    const config = resolveConfig();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW_RESPONSE));
    const res = await postChallenge(
      config,
      buildChallengePayload({
        nonce: 'n-c',
        challengeId: 'c-1',
        action: 'otp_request',
        holdStartMs: 10,
        holdEndMs: 1120,
      }),
      { fetchImpl: fetchMock },
    );
    expect(res.decision).toBe('allow');
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/v1/assess/challenge');
  });
});

describe('safeAssess & safeSubmitChallenge (non-blocking host guarantees)', () => {
  it('fetches nonce, notifies onNonceIssued, and returns the backend decision', async () => {
    const config = resolveConfig();
    const onNonceIssued = vi.fn();
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-safe', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW_RESPONSE));

    const res = await safeAssess(
      config,
      { action: 'login', onNonceIssued },
      { fetchImpl: fetchMock },
    );
    expect(onNonceIssued).toHaveBeenCalledTimes(1);
    expect(res).toEqual(SAMPLE_ALLOW_RESPONSE);
  });

  it('never throws when network fails; returns degraded fallback response', async () => {
    const config = resolveConfig({ maxRetries: 1, retryBaseDelayMs: 0 });
    const fetchMock = vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed to fetch'));

    const res = await safeAssess(config, { action: 'otp_request' }, { fetchImpl: fetchMock });
    expect(res.degraded).toBe(true);
    expect(res.decision).toBe('deny');
    expect(res.request_id).toContain('network_error');

    const chalRes = await safeSubmitChallenge(
      config,
      { challengeId: 'c-1', action: 'otp_request' },
      { fetchImpl: fetchMock },
    );
    expect(chalRes.degraded).toBe(true);
  });
});

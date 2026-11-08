import { afterEach, describe, expect, it, vi } from 'vitest';
import { type AssessResponse, BotGuard, BotGuardClient, type ChallengeInfo } from '../src/index';

let clock = 0;
const now = (): number => clock;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function fireMouseMove(x: number, y: number): void {
  const ev = new MouseEvent('mousemove', { clientX: x, clientY: y, bubbles: true });
  Object.defineProperty(ev, 'isTrusted', { value: true });
  window.dispatchEvent(ev);
}

function fireKey(type: 'keydown' | 'keyup', key: string, code: string): void {
  const ev = new KeyboardEvent(type, { key, code, bubbles: true });
  Object.defineProperty(ev, 'isTrusted', { value: true });
  window.dispatchEvent(ev);
}

const SAMPLE_ALLOW: AssessResponse = {
  decision: 'allow',
  band: 'low',
  token: 'jwt-allow',
  challenge: null,
  request_id: 'req-1',
  model_versions: { mouse: 'lgbm-1.0.0', keyboard: 'lr-1.0.0', fusion: '1.0.0' },
  degraded: false,
};

const SAMPLE_CHALLENGE_INFO: ChallengeInfo = {
  id: 'chal-42',
  type: 'press_hold',
  hold_ms: 1100,
  expires_in: 60,
};

afterEach(() => {
  BotGuard.stop();
  clock = 0;
});

describe('BotGuard public API & BotGuardClient (P6-07)', () => {
  it('start() and stop() are idempotent and safe to call multiple times', () => {
    expect(BotGuard.running).toBe(false);
    BotGuard.start({ now });
    expect(BotGuard.running).toBe(true);

    // Calling start() again with no args is a no-op and preserves recorded events
    clock = 100;
    fireMouseMove(25, 35);
    BotGuard.start();
    expect(BotGuard.running).toBe(true);

    // Calling stop() multiple times is safe
    BotGuard.stop();
    expect(BotGuard.running).toBe(false);
    BotGuard.stop();
    expect(BotGuard.running).toBe(false);
  });

  it('collects mouse, keyboard, timing and env signals and posts them on assess(action)', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-live', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW));

    BotGuard.start({
      endpoint: 'http://127.0.0.1:8000',
      now,
      transportDeps: { fetchImpl: fetchMock, nowEpochMs: () => 1_760_000_000_000 },
    });

    clock = 250;
    fireMouseMove(100, 200);
    clock = 300;
    fireKey('keydown', 'a', 'KeyA');
    clock = 380;
    fireKey('keyup', 'a', 'KeyA');
    clock = 1_500;

    const result = await BotGuard.assess('otp_request');
    expect(result).toEqual(SAMPLE_ALLOW);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    const assessCall = fetchMock.mock.calls[1];
    expect(assessCall?.[0]).toBe('http://127.0.0.1:8000/v1/assess');
    const sentBody = JSON.parse(String(assessCall?.[1]?.body));
    expect(sentBody.nonce).toBe('n-live');
    expect(sentBody.action).toBe('otp_request');
    expect(sentBody.behaviour.mouse.points).toEqual([[100, 200, 250]]);
    expect(sentBody.behaviour.keys.events).toEqual([['letter', 300, 380]]);
    expect(sentBody.behaviour.timing.ms_to_first_interaction).toBe(250);
    expect(sentBody.behaviour.timing.ms_since_load).toBe(1_500);
    expect(sentBody.env).toBeTypeOf('object');
  });

  it('uses a prefetched single-use nonce once and fetches a new one on subsequent assess()', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-prefetch', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW))
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-second', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW));

    const client = new BotGuardClient({
      now,
      transportDeps: { fetchImpl: fetchMock },
    });
    client.start();
    clock = 100;
    await client.prefetchNonce();

    clock = 900;
    await client.assess('login');
    const firstBody = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body));
    expect(firstBody.nonce).toBe('n-prefetch');
    expect(firstBody.behaviour.timing.ms_since_nonce).toBe(800);

    clock = 1_200;
    await client.assess('login');
    const secondBody = JSON.parse(String(fetchMock.mock.calls[3]?.[1]?.body));
    expect(secondBody.nonce).toBe('n-second');
    client.stop();
  });

  it('runChallenge invokes the registered challengeHandler and posts to /v1/assess/challenge', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-chal', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW));

    const handler = vi.fn(async () => ({ holdStartMs: 500, holdEndMs: 1_650 }));

    BotGuard.start({
      now,
      transportDeps: { fetchImpl: fetchMock },
      challengeHandler: handler,
    });

    const res = await BotGuard.runChallenge(SAMPLE_CHALLENGE_INFO, 'otp_request');
    expect(handler).toHaveBeenCalledWith(SAMPLE_CHALLENGE_INFO, 'otp_request');
    expect(res).toEqual(SAMPLE_ALLOW);

    const chalBody = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body));
    expect(chalBody).toMatchObject({
      nonce: 'n-chal',
      challenge_id: 'chal-42',
      action: 'otp_request',
      hold_start_ms: 500,
      hold_end_ms: 1_650,
    });
  });

  it('runChallenge uses the default challenge UI and returns degraded when cancelled', async () => {
    BotGuard.setChallengeHandler(undefined);
    BotGuard.start({ now });
    const promise = BotGuard.runChallenge(SAMPLE_CHALLENGE_INFO, 'otp_request');
    const cancelBtn = document.querySelector(
      '.botguard-challenge-cancel-btn',
    ) as HTMLButtonElement | null;
    expect(cancelBtn).not.toBeNull();
    cancelBtn?.click();
    const res = await promise;
    expect(res.degraded).toBe(true);
    expect(res.request_id).toContain('challenge_cancelled');
  });
});

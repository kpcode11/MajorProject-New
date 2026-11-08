import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  type AssessResponse,
  BotGuardClient,
  HARD_LIMITS,
  buildAssessPayload,
  createThrottleGate,
  scheduleIdleTask,
  utf8ByteLength,
} from '../src/index';

let clock = 0;
const now = (): number => clock;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const SAMPLE_ALLOW: AssessResponse = {
  decision: 'allow',
  band: 'low',
  token: 'jwt-perf',
  challenge: null,
  request_id: 'req-perf',
  model_versions: { mouse: 'lgbm-1.0.0' },
  degraded: false,
};

afterEach(() => {
  clock = 0;
});

describe('SDK performance controls (P6-10)', () => {
  it('registers all collector listeners with passive: true and removes every listener on stop()', () => {
    const added: { type: string; options: AddEventListenerOptions | boolean | undefined }[] = [];
    const removed: { type: string }[] = [];

    const origAdd = window.addEventListener.bind(window);
    const origRemove = window.removeEventListener.bind(window);

    const addSpy = vi
      .spyOn(window, 'addEventListener')
      .mockImplementation(
        (
          type: string,
          listener: EventListenerOrEventListenerObject,
          options?: boolean | AddEventListenerOptions,
        ) => {
          added.push({ type, options });
          origAdd(type, listener, options);
        },
      );
    const removeSpy = vi
      .spyOn(window, 'removeEventListener')
      .mockImplementation(
        (
          type: string,
          listener: EventListenerOrEventListenerObject,
          options?: boolean | EventListenerOptions,
        ) => {
          removed.push({ type });
          origRemove(type, listener, options);
        },
      );

    const client = new BotGuardClient({ now });
    client.start({ target: window });

    expect(added.length).toBeGreaterThan(0);
    for (const entry of added) {
      expect(typeof entry.options === 'object' && entry.options?.passive === true).toBe(true);
    }

    client.stop();
    expect(removed.map((r) => r.type).sort()).toEqual(added.map((a) => a.type).sort());

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it('uses requestIdleCallback when available and falls back to timeout when busy', async () => {
    const ricSpy = vi.fn((cb: () => void) => {
      cb();
      return 1;
    });
    const fakeWin = { requestIdleCallback: ricSpy } as unknown as Window;

    const result = await scheduleIdleTask(() => 42, { enabled: true, win: fakeWin });
    expect(result).toBe(42);
    expect(ricSpy).toHaveBeenCalledTimes(1);

    // Fallback timer fires even if requestIdleCallback never invokes the callback
    const hungWin = {
      requestIdleCallback: () => 2,
    } as unknown as Window;
    const fallbackResult = await scheduleIdleTask(() => 'fallback-ok', {
      enabled: true,
      timeoutMs: 10,
      win: hungWin,
    });
    expect(fallbackResult).toBe('fallback-ok');
  });

  it('bounds memory and payload size (< 64 KB) under a 10,000-event high-frequency storm', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-storm', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW));

    const client = new BotGuardClient({
      now,
      mouseThrottleMs: 16,
      maxMousePoints: HARD_LIMITS.maxMousePoints,
      maxKeyEvents: HARD_LIMITS.maxKeyEvents,
      transportDeps: { fetchImpl: fetchMock },
    });
    client.start();

    // Dispatch 10,000 mouse moves + 2,000 key press/release pairs
    for (let i = 0; i < 10_000; i += 1) {
      clock = i * 2; // 500 Hz input storm
      const move = new MouseEvent('mousemove', {
        clientX: i % 1920,
        clientY: i % 1080,
        bubbles: true,
      });
      Object.defineProperty(move, 'isTrusted', { value: true });
      window.dispatchEvent(move);

      if (i % 5 === 0) {
        const kd = new KeyboardEvent('keydown', { key: 'a', code: 'KeyA', bubbles: true });
        Object.defineProperty(kd, 'isTrusted', { value: true });
        window.dispatchEvent(kd);
        clock += 1;
        const ku = new KeyboardEvent('keyup', { key: 'a', code: 'KeyA', bubbles: true });
        Object.defineProperty(ku, 'isTrusted', { value: true });
        window.dispatchEvent(ku);
      }
    }

    const snap = client.collectSnapshot();
    expect(snap.behaviour.mouse?.points.length).toBeLessThanOrEqual(HARD_LIMITS.maxMousePoints);
    expect(snap.behaviour.keys?.events.length).toBeLessThanOrEqual(HARD_LIMITS.maxKeyEvents);

    const payload = buildAssessPayload({
      nonce: 'n-storm',
      action: 'otp_request',
      env: snap.env,
      behaviour: snap.behaviour,
    });
    const bytes = utf8ByteLength(JSON.stringify(payload));
    expect(bytes).toBeLessThanOrEqual(HARD_LIMITS.maxBodyBytes);

    await client.assess('otp_request');
    client.stop();

    // After stop(), snapshots have no buffered collector traces
    const afterStop = client.collectSnapshot();
    expect(afterStop.behaviour.mouse).toBeUndefined();
    expect(afterStop.behaviour.keys).toBeUndefined();
  });

  it('createThrottleGate enforces the minimum interval and resets cleanly', () => {
    const gate = createThrottleGate(16);
    expect(gate.allow(0)).toBe(true);
    expect(gate.allow(10)).toBe(false);
    expect(gate.allow(16)).toBe(true);
    gate.reset();
    expect(gate.allow(5)).toBe(true);
  });
});

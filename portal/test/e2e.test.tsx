/**
 * End-to-end portal + SDK flow tests (P7-18).
 *
 * Exercises the full portal React UI + BotGuardProvider DOM telemetry collectors against
 * a stateful scoring + token verification harness:
 *  1. Normal interaction path (mouse curve + keystrokes) -> token -> OTP accepted (200).
 *  2. Headless direct click (navigator.webdriver=true, 0 mouse move points) -> denied -> 401.
 *  3. No token -> 401 Unauthorized on /portal-api/otp/request.
 *  4. Keyboard-only session (Tab + typing + Enter, 0 mouse points) -> never auto-denied ->
 *     passes via the accessible keyboard step-up challenge path -> OTP accepted (200).
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';
import { callPortalEndpoint } from '../src/api';

let container: HTMLDivElement | null = null;
let root: Root | null = null;
const originalFetch = globalThis.fetch;

function setInputValue(input: HTMLInputElement, value: string): void {
  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    'value',
  )?.set;
  nativeSetter?.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}

function createStatefulBackendFetch(options?: { forceWebdriver?: boolean }) {
  const issuedTokens = new Set<string>();
  const assessRequests: Array<Record<string, unknown>> = [];

  const mockFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();

    if (url.endsWith('/v1/nonce')) {
      return new Response(JSON.stringify({ nonce: 'e2e_nonce_12345', expires_in: 120 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url.endsWith('/v1/assess')) {
      const payload = JSON.parse(typeof init?.body === 'string' ? init.body : '{}') as Record<
        string,
        unknown
      >;
      assessRequests.push(payload);
      const env = (payload.env as Record<string, unknown> | undefined) ?? {};
      const behaviour = (payload.behaviour as Record<string, unknown> | undefined) ?? {};
      const mouse = (behaviour.mouse as { points?: unknown[] } | undefined) ?? {};
      const keys = (behaviour.keys as { events?: unknown[] } | undefined) ?? {};
      const mousePointsCount = Array.isArray(mouse.points) ? mouse.points.length : 0;
      const keyEventsCount = Array.isArray(keys.events) ? keys.events.length : 0;
      const isWebdriver = Boolean(options?.forceWebdriver || env.webdriver === true);

      // Headless direct fill + click with webdriver and zero mouse/key telemetry -> deny
      if (isWebdriver && mousePointsCount === 0 && keyEventsCount === 0) {
        return new Response(
          JSON.stringify({
            decision: 'deny',
            band: 'high',
            token: null,
            challenge: null,
            request_id: 'req_deny_1',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      // Keyboard-only session (zero mouse points, >= 1 key event) -> never auto-denied; challenge
      if (mousePointsCount === 0 && keyEventsCount > 0) {
        return new Response(
          JSON.stringify({
            decision: 'challenge',
            band: 'medium',
            token: null,
            challenge: {
              id: 'chal_kb_e2e_1',
              type: 'press_hold',
              hold_ms: 850,
              expires_in: 60,
            },
            request_id: 'req_chal_kb_1',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      const token = 'jwt_valid_e2e_token_999';
      issuedTokens.add(token);
      return new Response(
        JSON.stringify({
          decision: 'allow',
          band: 'low',
          token,
          challenge: null,
          request_id: 'req_allow_1',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    if (url.endsWith('/v1/assess/challenge')) {
      const token = 'jwt_stepup_e2e_token_888';
      issuedTokens.add(token);
      return new Response(
        JSON.stringify({
          decision: 'allow',
          band: 'low',
          token,
          challenge: null,
          request_id: 'req_stepup_allow_1',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    if (url.startsWith('/portal-api/')) {
      const headers = (init?.headers as Record<string, string> | undefined) ?? {};
      const token = headers['X-Human-Token'] ?? headers['x-human-token'];
      if (!token || !issuedTokens.has(token)) {
        return new Response(JSON.stringify({ detail: 'Missing or invalid X-Human-Token header' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(
        JSON.stringify({
          status: 'otp_sent',
          message: 'Synthetic OTP dispatched for verified human session.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    return new Response('{}', { status: 404 });
  }) as typeof fetch;

  return { mockFetch, assessRequests, issuedTokens };
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  if (root) {
    act(() => {
      root?.unmount();
    });
    root = null;
  }
  container?.remove();
  container = null;
});

describe('Portal E2E flows (P7-18)', () => {
  it('normal interaction path -> token -> OTP accepted', async () => {
    const { mockFetch, assessRequests } = createStatefulBackendFetch();
    globalThis.fetch = mockFetch;

    act(() => {
      root?.render(<App initialPage="login" />);
    });

    // Dispatch realistic mousemove and keydown/keyup events captured by BotGuardProvider
    act(() => {
      window.dispatchEvent(
        new MouseEvent('mousemove', { clientX: 120, clientY: 160, bubbles: true }),
      );
      window.dispatchEvent(
        new MouseEvent('mousemove', { clientX: 185, clientY: 220, bubbles: true }),
      );
      window.dispatchEvent(
        new MouseEvent('mousemove', { clientX: 230, clientY: 270, bubbles: true }),
      );
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '9', bubbles: true }));
      window.dispatchEvent(new KeyboardEvent('keyup', { key: '9', bubbles: true }));
    });

    const input = container?.querySelector(
      '[data-testid="identifier-input"]',
    ) as HTMLInputElement | null;
    const sendBtn = container?.querySelector(
      '[data-testid="send-otp-btn"]',
    ) as HTMLButtonElement | null;

    act(() => {
      if (input) setInputValue(input, '999900001234');
    });

    await act(async () => {
      sendBtn?.click();
    });

    expect(assessRequests.length).toBeGreaterThanOrEqual(1);
    const otpResult = container?.querySelector('[data-testid="otp-result"]');
    expect(otpResult?.getAttribute('data-outcome')).toBe('accepted');
    expect(otpResult?.textContent).toContain(
      'Synthetic OTP dispatched for verified human session.',
    );
  });

  it('headless direct click -> denied -> OTP rejected with 401', async () => {
    const { mockFetch } = createStatefulBackendFetch({ forceWebdriver: true });
    globalThis.fetch = mockFetch;

    act(() => {
      root?.render(<App initialPage="login" />);
    });

    const input = container?.querySelector(
      '[data-testid="identifier-input"]',
    ) as HTMLInputElement | null;
    const sendBtn = container?.querySelector(
      '[data-testid="send-otp-btn"]',
    ) as HTMLButtonElement | null;

    // Direct fill + click with zero mouse movements or keydown/keyup events
    act(() => {
      if (input) setInputValue(input, '999900001234');
    });

    await act(async () => {
      sendBtn?.click();
    });

    const otpResult = container?.querySelector('[data-testid="otp-result"]');
    expect(otpResult?.getAttribute('data-outcome')).toBe('rejected');
  });

  it('no token -> 401 Unauthorized at protected portal endpoint', async () => {
    const { mockFetch } = createStatefulBackendFetch();
    const res = await callPortalEndpoint(
      '/portal-api/otp/request',
      { action: 'otp_request', identifier_length: 12 },
      async () => {
        throw new Error('No assessment performed');
      },
      mockFetch,
    );

    expect(res.ok).toBe(false);
    expect(res.status).toBe(401);
    expect(res.message).toContain('Missing or invalid X-Human-Token header');
  });

  it('keyboard-only session (Tab + typing + Enter) is not auto-denied and passes via keyboard step-up', async () => {
    vi.useFakeTimers();
    try {
      const { mockFetch } = createStatefulBackendFetch();
      globalThis.fetch = mockFetch;

      act(() => {
        root?.render(<App initialPage="login" />);
      });

      // Dispatch keyboard-only events (zero mouse movements)
      act(() => {
        const tabDown = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true });
        const tabUp = new KeyboardEvent('keyup', { key: 'Tab', bubbles: true });
        const keyDown = new KeyboardEvent('keydown', { key: '9', bubbles: true });
        const keyUp = new KeyboardEvent('keyup', { key: '9', bubbles: true });
        for (const ev of [tabDown, tabUp, keyDown, keyUp]) {
          Object.defineProperty(ev, 'isTrusted', { value: true });
          window.dispatchEvent(ev);
        }
      });

      const input = container?.querySelector(
        '[data-testid="identifier-input"]',
      ) as HTMLInputElement | null;
      const sendBtn = container?.querySelector(
        '[data-testid="send-otp-btn"]',
      ) as HTMLButtonElement | null;

      act(() => {
        if (input) setInputValue(input, '999900001234');
      });

      act(() => {
        sendBtn?.click();
      });

      await act(async () => {
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      // Step-up dialog appears; activate the keyboard alternative button with Space
      const kbBtn = document.querySelector(
        '[data-testid="stepup-kb-btn"]',
      ) as HTMLButtonElement | null;
      expect(kbBtn).not.toBeNull();

      const spaceEvt = new KeyboardEvent('keydown', {
        key: ' ',
        code: 'Space',
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(spaceEvt, 'isTrusted', { value: true });
      act(() => {
        kbBtn?.dispatchEvent(spaceEvt);
      });

      await act(async () => {
        vi.advanceTimersByTime(900);
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      const otpResult = container?.querySelector('[data-testid="otp-result"]');
      expect(otpResult?.getAttribute('data-outcome')).toBe('accepted');
    } finally {
      vi.useRealTimers();
    }
  });
});

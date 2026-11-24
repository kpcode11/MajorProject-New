/**
 * Keyboard-only E2E test suite for the portal login/OTP flow (P9-10).
 *
 * Verifies that a user navigating and interacting exclusively with a keyboard
 * (zero mouse/pointer/touch events) can:
 *  1. Start on the portal Landing page, Tab through the navigation bar (or service cards)
 *     in DOM tab order, and open the Resident Login page with Enter/Space.
 *  2. Tab to the Mock Resident Identifier input, type a synthetic identifier with
 *     realistic keydown/input/keyup timings, and submit the OTP request with Enter.
 *  3. Complete the login/OTP flow both when passive assessment returns `allow` directly
 *     and when it returns `challenge` (via both the single-press keyboard accessibility
 *     button `stepup-kb-btn` and the physical keyboard hold on `stepup-hold-btn`),
 *     including focus-trap cycling (`Tab` / `Shift+Tab`) and focus restoration on close.
 *  4. Recover from form validation errors using keyboard-only navigation.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';

let container: HTMLDivElement | null = null;
let root: Root | null = null;
const originalFetch = globalThis.fetch;

const KEY_CODES: Record<string, string> = {
  '0': 'Digit0',
  '1': 'Digit1',
  '2': 'Digit2',
  '3': 'Digit3',
  '4': 'Digit4',
  '5': 'Digit5',
  '6': 'Digit6',
  '7': 'Digit7',
  '8': 'Digit8',
  '9': 'Digit9',
  '-': 'Minus',
  Tab: 'Tab',
  Enter: 'Enter',
  ' ': 'Space',
  Escape: 'Escape',
  Backspace: 'Backspace',
};

function getContainer(): HTMLDivElement {
  if (!container) {
    throw new Error('Test container is not initialized');
  }
  return container;
}

/**
 * Return all keyboard-tabbable elements within `scope` in DOM order.
 */
function getTabbableElements(scope: HTMLElement): HTMLElement[] {
  const selector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(',');
  return Array.from(scope.querySelectorAll<HTMLElement>(selector)).filter(
    (el) => !el.hasAttribute('disabled') && el.getAttribute('tabindex') !== '-1',
  );
}

function createTrustedKeyEvent(
  type: 'keydown' | 'keyup',
  key: string,
  options: { shiftKey?: boolean; repeat?: boolean } = {},
): KeyboardEvent {
  const evt = new KeyboardEvent(type, {
    key,
    code: KEY_CODES[key] ?? key,
    shiftKey: options.shiftKey ?? false,
    repeat: options.repeat ?? false,
    bubbles: true,
    cancelable: true,
  });
  Object.defineProperty(evt, 'isTrusted', { value: true });
  return evt;
}

/**
 * Emulate browser-native `Tab` / `Shift+Tab` key press: dispatches `keydown` on the active
 * element, moves focus along the tabbable ring (unless `preventDefault()` was called by a
 * modal focus trap), and dispatches `keyup` on the newly focused element.
 */
function pressTab(scope: HTMLElement, options: { shiftKey?: boolean } = {}): HTMLElement | null {
  const active =
    (document.activeElement instanceof HTMLElement ? document.activeElement : null) ?? scope;
  const downEvt = createTrustedKeyEvent('keydown', 'Tab', options);
  const notCancelled = active.dispatchEvent(downEvt);

  if (notCancelled) {
    const tabbables = getTabbableElements(scope);
    if (tabbables.length > 0) {
      const currentIdx = tabbables.indexOf(active);
      let nextIdx: number;
      if (options.shiftKey) {
        nextIdx = currentIdx <= 0 ? tabbables.length - 1 : currentIdx - 1;
      } else {
        nextIdx = currentIdx < 0 || currentIdx >= tabbables.length - 1 ? 0 : currentIdx + 1;
      }
      tabbables[nextIdx]?.focus();
    }
  }

  const nextActive =
    (document.activeElement instanceof HTMLElement ? document.activeElement : null) ?? scope;
  const upEvt = createTrustedKeyEvent('keyup', 'Tab', options);
  nextActive.dispatchEvent(upEvt);
  return document.activeElement instanceof HTMLElement ? document.activeElement : null;
}

/**
 * Emulate pressing `Enter` or `Space` on the currently focused element, including the
 * standard browser default activation for `<button>`, `<a href>`, and `<input>` inside `<form>`.
 */
function pressActivationKey(key: 'Enter' | ' '): void {
  const target =
    document.activeElement instanceof HTMLElement ? document.activeElement : getContainer();
  const downEvt = createTrustedKeyEvent('keydown', key);
  const notCancelled = target.dispatchEvent(downEvt);

  if (notCancelled) {
    const tag = target.tagName.toUpperCase();
    if (tag === 'BUTTON' || (tag === 'A' && key === 'Enter')) {
      target.click();
    } else if (tag === 'INPUT' && key === 'Enter') {
      const form = (target as HTMLInputElement).form;
      if (form) {
        form.requestSubmit();
      }
    }
  }

  const upTarget = document.activeElement instanceof HTMLElement ? document.activeElement : target;
  const upEvt = createTrustedKeyEvent('keyup', key);
  upTarget.dispatchEvent(upEvt);
}

/**
 * Type a string into the currently focused `<input>` one character at a time using
 * trusted `keydown` -> `input` -> `keyup` events and advancing fake timers between keys.
 */
function typeIntoFocusedInput(text: string, advanceClockMs: (ms: number) => void): void {
  const active = document.activeElement;
  if (!(active instanceof HTMLInputElement)) {
    throw new Error(`Expected activeElement to be HTMLInputElement, got ${active?.tagName}`);
  }
  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    'value',
  )?.set;

  let currentVal = active.value;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text.slice(i, i + 1);
    const downEvt = createTrustedKeyEvent('keydown', ch);
    active.dispatchEvent(downEvt);

    advanceClockMs(18);
    currentVal += ch;
    nativeSetter?.call(active, currentVal);
    active.dispatchEvent(
      new InputEvent('input', { data: ch, inputType: 'insertText', bubbles: true }),
    );

    advanceClockMs(64 + (i % 4) * 11);
    const upEvt = createTrustedKeyEvent('keyup', ch);
    active.dispatchEvent(upEvt);

    advanceClockMs(95 + (i % 3) * 19);
  }
}

function createKeyboardE2EBackendFetch(mode: 'allow_direct' | 'challenge_stepup') {
  const issuedTokens = new Set<string>();
  const assessPayloads: Array<Record<string, unknown>> = [];
  const challengePayloads: Array<Record<string, unknown>> = [];
  const portalPayloads: Array<Record<string, unknown>> = [];

  const mockFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();

    if (url.endsWith('/v1/nonce')) {
      return new Response(JSON.stringify({ nonce: 'kb_e2e_nonce_910', expires_in: 120 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url.endsWith('/v1/assess')) {
      const payload = JSON.parse(typeof init?.body === 'string' ? init.body : '{}') as Record<
        string,
        unknown
      >;
      assessPayloads.push(payload);

      if (mode === 'allow_direct') {
        const token = 'jwt_kb_direct_allow_910';
        issuedTokens.add(token);
        return new Response(
          JSON.stringify({
            decision: 'allow',
            band: 'low',
            token,
            challenge: null,
            request_id: 'req_kb_allow_910',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }

      return new Response(
        JSON.stringify({
          decision: 'challenge',
          band: 'medium',
          token: null,
          challenge: {
            id: 'chal_kb_910',
            type: 'press_hold',
            hold_ms: 850,
            expires_in: 60,
          },
          request_id: 'req_kb_chal_910',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    if (url.endsWith('/v1/assess/challenge')) {
      const payload = JSON.parse(typeof init?.body === 'string' ? init.body : '{}') as Record<
        string,
        unknown
      >;
      challengePayloads.push(payload);
      const token = 'jwt_kb_stepup_allow_910';
      issuedTokens.add(token);
      return new Response(
        JSON.stringify({
          decision: 'allow',
          band: 'low',
          token,
          challenge: null,
          request_id: 'req_kb_stepup_910',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    if (url.startsWith('/portal-api/')) {
      const headers = (init?.headers as Record<string, string> | undefined) ?? {};
      const token = headers['X-Human-Token'] ?? headers['x-human-token'];
      const payload = JSON.parse(typeof init?.body === 'string' ? init.body : '{}') as Record<
        string,
        unknown
      >;
      portalPayloads.push(payload);
      if (!token || !issuedTokens.has(token)) {
        return new Response(JSON.stringify({ detail: 'Missing or invalid X-Human-Token header' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(
        JSON.stringify({
          status: 'otp_sent',
          message: 'Synthetic OTP dispatched for keyboard-only verified session.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }

    return new Response('{}', { status: 404 });
  }) as unknown as typeof fetch;

  return { mockFetch, assessPayloads, challengePayloads, portalPayloads };
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

describe('Keyboard-only Portal Login/OTP E2E (P9-10)', () => {
  it('completes navigation from Landing -> Login -> typing -> Enter submit -> OTP accepted via keyboard only (step-up single-press path)', async () => {
    vi.useFakeTimers();
    let pointerEventsFired = 0;
    const forbidPointer = () => {
      pointerEventsFired += 1;
    };
    window.addEventListener('mousemove', forbidPointer, true);
    window.addEventListener('mousedown', forbidPointer, true);
    window.addEventListener('mouseup', forbidPointer, true);
    window.addEventListener('pointerdown', forbidPointer, true);
    window.addEventListener('touchstart', forbidPointer, true);

    try {
      const { mockFetch, assessPayloads, challengePayloads, portalPayloads } =
        createKeyboardE2EBackendFetch('challenge_stepup');
      globalThis.fetch = mockFetch;

      act(() => {
        root?.render(<App initialPage="landing" />);
      });
      const rootEl = getContainer();
      expect(rootEl.querySelector('[data-testid="page-landing"]')).not.toBeNull();

      // 1. Tab through the header navigation until `nav-login` is focused:
      //    Tab 1: skip-to-main link
      //    Tab 2: nav-landing ("Overview")
      //    Tab 3: nav-login ("Resident login")
      act(() => {
        pressTab(rootEl);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('skip-to-main');

      act(() => {
        pressTab(rootEl);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('theme-toggle');

      act(() => {
        pressTab(rootEl);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('nav-landing');

      act(() => {
        pressTab(rootEl);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('nav-login');

      // 2. Press Enter on the focused "Resident login" nav button to switch pages
      act(() => {
        pressActivationKey('Enter');
      });
      expect(rootEl.querySelector('[data-testid="page-login"]')).not.toBeNull();
      expect(rootEl.querySelector('[data-testid="nav-login"]')?.getAttribute('aria-current')).toBe(
        'page',
      );

      // 3. Continue Tabbing through the remaining nav items into `<main>` to reach the identifier input:
      //    nav-update-details -> nav-centre-search -> nav-admin -> identifier-input
      for (const expectedTestId of [
        'nav-update-details',
        'nav-centre-search',
        'nav-admin',
        'identifier-input',
      ]) {
        act(() => {
          pressTab(rootEl);
        });
        expect(document.activeElement?.getAttribute('data-testid')).toBe(expectedTestId);
      }

      // 4. First test keyboard validation error recovery: press Enter on empty input
      await act(async () => {
        pressActivationKey('Enter');
      });
      expect(rootEl.querySelector('[data-testid="login-validation-error"]')).not.toBeNull();
      expect(document.activeElement?.getAttribute('aria-invalid')).toBe('true');

      // 5. Type synthetic identifier "9999-0000-1234" via keyboard events only
      act(() => {
        typeIntoFocusedInput('9999-0000-1234', (ms) => vi.advanceTimersByTime(ms));
      });

      // 6. Tab from the identifier input to the "Send OTP" submit button and press Enter
      act(() => {
        pressTab(rootEl);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('send-otp-btn');

      await act(async () => {
        pressActivationKey('Enter');
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      // 7. Verify step-up modal opened, focused `stepup-hold-btn`, and traps Tab focus
      const dialog = document.querySelector('[data-testid="stepup-dialog"]') as HTMLElement | null;
      expect(dialog).not.toBeNull();
      if (!dialog) {
        throw new Error('Expected stepup-dialog to be rendered');
      }
      expect(document.activeElement?.getAttribute('data-testid')).toBe('stepup-hold-btn');

      // Tab inside dialog: hold-btn -> kb-btn -> cancel-btn -> wraps to hold-btn
      act(() => {
        pressTab(dialog);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('stepup-kb-btn');

      act(() => {
        pressTab(dialog);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('stepup-cancel-btn');

      act(() => {
        pressTab(dialog);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('stepup-hold-btn');

      // Shift+Tab wraps backwards to cancel-btn, then Shift+Tab to kb-btn
      act(() => {
        pressTab(dialog, { shiftKey: true });
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('stepup-cancel-btn');

      act(() => {
        pressTab(dialog, { shiftKey: true });
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('stepup-kb-btn');

      // 8. Activate the keyboard single-press alternative button with Space
      act(() => {
        const spaceDown = createTrustedKeyEvent('keydown', ' ');
        document.activeElement?.dispatchEvent(spaceDown);
      });

      await act(async () => {
        vi.advanceTimersByTime(900);
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      // 9. Verify modal closed, focus restored to Send OTP button, and OTP was accepted
      expect(document.querySelector('[data-testid="stepup-dialog"]')).toBeNull();
      const otpResult = rootEl.querySelector('[data-testid="otp-result"]');
      expect(otpResult?.getAttribute('data-outcome')).toBe('accepted');
      expect(otpResult?.textContent).toContain(
        'Synthetic OTP dispatched for keyboard-only verified session.',
      );

      // 10. Verify telemetry & privacy invariants on the recorded payloads
      expect(pointerEventsFired).toBe(0);
      expect(assessPayloads.length).toBe(1);
      const behaviour = assessPayloads[0]?.behaviour as {
        mouse: { points: unknown[]; clicks: [number, number, number, number][] };
        keys: { events: [string, number, number][]; autofill_suspected: boolean };
      };
      expect(behaviour.mouse.points).toHaveLength(0);
      expect(behaviour.mouse.clicks.every((c) => c[2] === c[3])).toBe(true);
      expect(behaviour.keys.events.length).toBeGreaterThanOrEqual(14);
      expect(behaviour.keys.autofill_suspected).toBe(false);

      const classesRecorded = new Set(behaviour.keys.events.map((e) => e[0]));
      expect(classesRecorded.has('digit')).toBe(true);
      expect(classesRecorded.has('punct')).toBe(true);
      expect(classesRecorded.has('other')).toBe(true); // Tab navigation keys

      expect(challengePayloads.length).toBe(1);
      expect(portalPayloads).toEqual([{ action: 'otp_request', identifier_length: 14 }]);
      expect(JSON.stringify(assessPayloads)).not.toContain('9999-0000-1234');
      expect(JSON.stringify(portalPayloads)).not.toContain('9999-0000-1234');
    } finally {
      window.removeEventListener('mousemove', forbidPointer, true);
      window.removeEventListener('mousedown', forbidPointer, true);
      window.removeEventListener('mouseup', forbidPointer, true);
      window.removeEventListener('pointerdown', forbidPointer, true);
      window.removeEventListener('touchstart', forbidPointer, true);
      vi.useRealTimers();
    }
  });

  it('completes keyboard-only login via Landing service card + Enter form submit + physical Spacebar hold in step-up challenge', async () => {
    vi.useFakeTimers();
    try {
      const { mockFetch, challengePayloads } = createKeyboardE2EBackendFetch('challenge_stepup');
      globalThis.fetch = mockFetch;

      act(() => {
        root?.render(<App initialPage="landing" />);
      });
      const rootEl = getContainer();

      // Tab through skip link, theme toggle, and the 5 portal nav buttons.
      for (let i = 0; i < 8; i += 1) {
        act(() => {
          pressTab(rootEl);
        });
      }
      expect(document.activeElement?.getAttribute('data-testid')).toBe('goto-login');

      // Activate `goto-login` with Space
      act(() => {
        pressActivationKey(' ');
      });
      expect(rootEl.querySelector('[data-testid="page-login"]')).not.toBeNull();

      // Tab to identifier-input
      while (document.activeElement?.getAttribute('data-testid') !== 'identifier-input') {
        act(() => {
          pressTab(rootEl);
        });
      }

      // Type identifier and submit directly from the input by pressing Enter
      act(() => {
        typeIntoFocusedInput('999900001234', (ms) => vi.advanceTimersByTime(ms));
      });

      await act(async () => {
        pressActivationKey('Enter');
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      // Step-up dialog opens with focus on `stepup-hold-btn`; hold Spacebar for 900 ms and release
      const holdBtn = document.querySelector(
        '[data-testid="stepup-hold-btn"]',
      ) as HTMLButtonElement | null;
      expect(holdBtn).not.toBeNull();
      expect(document.activeElement).toBe(holdBtn);

      act(() => {
        holdBtn?.dispatchEvent(createTrustedKeyEvent('keydown', ' '));
        vi.advanceTimersByTime(300);
        // Auto-repeat keydown events during physical key hold are ignored
        holdBtn?.dispatchEvent(createTrustedKeyEvent('keydown', ' ', { repeat: true }));
        vi.advanceTimersByTime(600);
      });
      expect(holdBtn?.textContent).toBe('Release to Complete');

      await act(async () => {
        holdBtn?.dispatchEvent(createTrustedKeyEvent('keyup', ' '));
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(challengePayloads.length).toBe(1);
      const otpResult = rootEl.querySelector('[data-testid="otp-result"]');
      expect(otpResult?.getAttribute('data-outcome')).toBe('accepted');
    } finally {
      vi.useRealTimers();
    }
  });

  it('completes keyboard-only login/OTP flow directly when passive assessment returns allow', async () => {
    vi.useFakeTimers();
    try {
      const { mockFetch, assessPayloads, challengePayloads, portalPayloads } =
        createKeyboardE2EBackendFetch('allow_direct');
      globalThis.fetch = mockFetch;

      act(() => {
        root?.render(<App initialPage="login" />);
      });
      const rootEl = getContainer();

      // Use skip-to-main link via Tab + Enter, then Tab into identifier-input
      act(() => {
        pressTab(rootEl);
      });
      expect(document.activeElement?.getAttribute('data-testid')).toBe('skip-to-main');

      while (document.activeElement?.getAttribute('data-testid') !== 'identifier-input') {
        act(() => {
          pressTab(rootEl);
        });
      }

      act(() => {
        typeIntoFocusedInput('9999-0000-1234', (ms) => vi.advanceTimersByTime(ms));
      });

      // Submit directly from the identifier input with Enter
      await act(async () => {
        pressActivationKey('Enter');
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(assessPayloads).toHaveLength(1);
      expect(challengePayloads).toHaveLength(0);
      expect(portalPayloads).toEqual([{ action: 'otp_request', identifier_length: 14 }]);
      const otpResult = rootEl.querySelector('[data-testid="otp-result"]');
      expect(otpResult?.getAttribute('data-outcome')).toBe('accepted');
      expect(rootEl.querySelector('[data-testid="last-decision"]')?.textContent).toContain(
        'allow (low)',
      );
    } finally {
      vi.useRealTimers();
    }
  });
});

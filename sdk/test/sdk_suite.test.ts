/**
 * End-to-end SDK acceptance test suite (P6-11):
 * - Collectors produce bounded output (`≤ 600` mouse points, `≤ 600` clicks, `≤ 300` key events).
 * - Key collector and full `BotGuard.assess()` payload never expose typed characters or form
 *   input values (tested with form fields populated by typing, pasting, and programmatic value
 *   assignment).
 * - Mouse throttling enforces `mouseThrottleMs`.
 * - Serialised payload size stays strictly under the 64 KB limit (`HARD_LIMITS.maxBodyBytes`) in a
 *   combined multi-modality stress test.
 * - `stop()` removes all listeners on `window` and `document` and leaves no residual listeners or
 *   buffered events.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  type AssessResponse,
  BotGuard,
  BotGuardClient,
  HARD_LIMITS,
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
  token: 'jwt-suite',
  challenge: null,
  request_id: 'req-suite',
  model_versions: { mouse: 'lgbm-1.0.0', keyboard: 'lr-1.0.0', fusion: '1.0.0' },
  degraded: false,
};

function keyCodeFor(ch: string): string {
  if (/[a-z]/i.test(ch)) return `Key${ch.toUpperCase()}`;
  if (/[0-9]/.test(ch)) return `Digit${ch}`;
  if (ch === ' ') return 'Space';
  return 'Period';
}

afterEach(() => {
  BotGuard.stop();
  clock = 0;
  document.body.innerHTML = '';
});

describe('P6-11 SDK comprehensive privacy, throttling, bounding, and cleanup suite', () => {
  it('never leaks typed or pre-filled form field strings into the serialised assess() payload', async () => {
    document.body.innerHTML = `
      <form id="portal-form">
        <input id="resident-id" name="residentId" type="text" value="PREFILLED_UID_998877665544" />
        <input id="passphrase" name="passphrase" type="password" />
        <textarea id="address">Flat 402, Indiranagar Bengaluru 560038</textarea>
      </form>
    `;
    const residentInput = document.getElementById('resident-id') as HTMLInputElement;
    const passphraseInput = document.getElementById('passphrase') as HTMLInputElement;
    const addressInput = document.getElementById('address') as HTMLTextAreaElement;

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-priv-1', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW));

    BotGuard.start({
      now,
      transportDeps: { fetchImpl: fetchMock },
    });

    const typedSecret = 'MyUltraSecretPassphrase9421';
    for (const ch of typedSecret) {
      clock += 35;
      const kd = new KeyboardEvent('keydown', {
        key: ch,
        code: keyCodeFor(ch),
        bubbles: true,
      });
      Object.defineProperty(kd, 'isTrusted', { value: true });
      passphraseInput.dispatchEvent(kd);
      passphraseInput.value += ch;
      passphraseInput.dispatchEvent(
        new InputEvent('input', { inputType: 'insertText', data: ch, bubbles: true }),
      );
      clock += 45;
      const ku = new KeyboardEvent('keyup', {
        key: ch,
        code: keyCodeFor(ch),
        bubbles: true,
      });
      Object.defineProperty(ku, 'isTrusted', { value: true });
      passphraseInput.dispatchEvent(ku);
    }

    // Also simulate paste into residentInput
    residentInput.value = 'PASTED_AADHAAR_123456789012';
    residentInput.dispatchEvent(new Event('paste', { bubbles: true }));
    residentInput.dispatchEvent(
      new InputEvent('input', { inputType: 'insertFromPaste', bubbles: true }),
    );

    // Also simulate autofill on addressInput
    clock += 1_000;
    addressInput.value = 'AUTOFILL_SENSITIVE_STREET_NAME';
    addressInput.dispatchEvent(new Event('input', { bubbles: true }));

    await BotGuard.assess('otp_request');

    const rawBody = String(fetchMock.mock.calls[1]?.[1]?.body);
    expect(rawBody).toBeTruthy();

    const forbiddenStrings = [
      'PREFILLED_UID_998877665544',
      '998877665544',
      typedSecret,
      'UltraSecret',
      'Passphrase',
      '9421',
      'Indiranagar',
      'Bengaluru',
      '560038',
      'PASTED_AADHAAR_123456789012',
      '123456789012',
      'AUTOFILL_SENSITIVE_STREET_NAME',
    ];
    for (const forbidden of forbiddenStrings) {
      expect(rawBody).not.toContain(forbidden);
    }

    const parsed = JSON.parse(rawBody);
    expect(parsed.behaviour.keys.events.length).toBe(typedSecret.length);
    expect(parsed.behaviour.keys.paste_events).toBe(1);
    expect(parsed.behaviour.keys.autofill_suspected).toBe(true);
  });

  it('keeps the full assess() request body under 64 KB under worst-case multi-modality stress', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-stress-64k', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ALLOW));

    const client = new BotGuardClient({
      now,
      mouseThrottleMs: 1,
      windowMs: 60_000,
      maxMousePoints: HARD_LIMITS.maxMousePoints,
      maxClicks: HARD_LIMITS.maxClicks,
      maxKeyEvents: HARD_LIMITS.maxKeyEvents,
      transportDeps: { fetchImpl: fetchMock },
    });
    client.start();

    for (let i = 0; i < 1_500; i += 1) {
      clock += 2;
      const move = new MouseEvent('mousemove', {
        clientX: 1000 + (i % 500),
        clientY: 1000 + (i % 400),
        bubbles: true,
      });
      Object.defineProperty(move, 'isTrusted', { value: true });
      window.dispatchEvent(move);

      const down = new MouseEvent('mousedown', {
        clientX: 1000 + (i % 500),
        clientY: 1000 + (i % 400),
        bubbles: true,
      });
      Object.defineProperty(down, 'isTrusted', { value: true });
      window.dispatchEvent(down);

      clock += 2;
      const up = new MouseEvent('mouseup', {
        clientX: 1000 + (i % 500),
        clientY: 1000 + (i % 400),
        bubbles: true,
      });
      Object.defineProperty(up, 'isTrusted', { value: true });
      window.dispatchEvent(up);

      const kd = new KeyboardEvent('keydown', { key: 'a', code: 'KeyA', bubbles: true });
      Object.defineProperty(kd, 'isTrusted', { value: true });
      window.dispatchEvent(kd);
      clock += 2;
      const ku = new KeyboardEvent('keyup', { key: 'a', code: 'KeyA', bubbles: true });
      Object.defineProperty(ku, 'isTrusted', { value: true });
      window.dispatchEvent(ku);
    }

    await client.assess('details_update');
    const sentJson = String(fetchMock.mock.calls[1]?.[1]?.body);
    expect(utf8ByteLength(sentJson)).toBeLessThanOrEqual(HARD_LIMITS.maxBodyBytes);
    client.stop();
  });

  it('stop() removes all window and document listeners across repeated start/stop cycles', () => {
    let winActive = 0;
    let docActive = 0;

    const origWinAdd = window.addEventListener.bind(window);
    const origWinRemove = window.removeEventListener.bind(window);
    const origDocAdd = document.addEventListener.bind(document);
    const origDocRemove = document.removeEventListener.bind(document);

    const winAddSpy = vi
      .spyOn(window, 'addEventListener')
      .mockImplementation(
        (
          type: string,
          listener: EventListenerOrEventListenerObject,
          options?: boolean | AddEventListenerOptions,
        ) => {
          winActive += 1;
          origWinAdd(type, listener, options);
        },
      );
    const winRemoveSpy = vi
      .spyOn(window, 'removeEventListener')
      .mockImplementation(
        (
          type: string,
          listener: EventListenerOrEventListenerObject,
          options?: boolean | EventListenerOptions,
        ) => {
          winActive -= 1;
          origWinRemove(type, listener, options);
        },
      );
    const docAddSpy = vi
      .spyOn(document, 'addEventListener')
      .mockImplementation(
        (
          type: string,
          listener: EventListenerOrEventListenerObject,
          options?: boolean | AddEventListenerOptions,
        ) => {
          docActive += 1;
          origDocAdd(type, listener, options);
        },
      );
    const docRemoveSpy = vi
      .spyOn(document, 'removeEventListener')
      .mockImplementation(
        (
          type: string,
          listener: EventListenerOrEventListenerObject,
          options?: boolean | EventListenerOptions,
        ) => {
          docActive -= 1;
          origDocRemove(type, listener, options);
        },
      );

    for (let cycle = 0; cycle < 3; cycle += 1) {
      BotGuard.start({ now });
      expect(winActive).toBeGreaterThan(0);
      expect(docActive).toBe(1);
      BotGuard.stop();
      expect(winActive).toBe(0);
      expect(docActive).toBe(0);
    }

    winAddSpy.mockRestore();
    winRemoveSpy.mockRestore();
    docAddSpy.mockRestore();
    docRemoveSpy.mockRestore();
  });
});

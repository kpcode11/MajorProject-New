import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App, DEMO_DISCLAIMER_TEXT } from '../src/App';

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

describe('Mock portal scaffold and pages (P7-01, P7-02)', () => {
  it('renders the prominent "DEMO — not a government portal" disclaimer and starts BotGuardProvider', () => {
    act(() => {
      root?.render(<App />);
    });

    const banner = container?.querySelector('[data-testid="demo-disclaimer-banner"]');
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toContain(DEMO_DISCLAIMER_TEXT);

    const status = container?.querySelector('[data-testid="botguard-status"]');
    expect(status?.textContent).toContain('Passive BotGuard: Active');
  });

  it('navigates between Landing, Resident login, Update details, and Centre search pages', () => {
    act(() => {
      root?.render(<App />);
    });

    expect(container?.querySelector('[data-testid="page-landing"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="card-login"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="card-update-details"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="card-centre-search"]')).not.toBeNull();

    const gotoLogin = container?.querySelector(
      '[data-testid="goto-login"]',
    ) as HTMLButtonElement | null;
    act(() => {
      gotoLogin?.click();
    });
    expect(container?.querySelector('[data-testid="page-login"]')).not.toBeNull();

    const navUpdate = container?.querySelector(
      '[data-testid="nav-update-details"]',
    ) as HTMLButtonElement | null;
    act(() => {
      navUpdate?.click();
    });
    expect(container?.querySelector('[data-testid="page-update-details"]')).not.toBeNull();

    const navCentres = container?.querySelector(
      '[data-testid="nav-centre-search"]',
    ) as HTMLButtonElement | null;
    act(() => {
      navCentres?.click();
    });
    expect(container?.querySelector('[data-testid="page-centre-search"]')).not.toBeNull();
  });

  it('submits "Resident login" (Send OTP) with X-Human-Token and without sending raw typed identifier', async () => {
    const portalCalls: Array<{ url: string; headers: Record<string, string>; body: string }> = [];

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.endsWith('/v1/nonce')) {
        return new Response(JSON.stringify({ nonce: 'nonce_test_123456', expires_in_s: 120 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.endsWith('/v1/assess')) {
        return new Response(
          JSON.stringify({
            decision: 'allow',
            score: 0.12,
            band: 'low',
            action: 'otp_request',
            token: 'tok_human_login_123',
            reasons: [],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.endsWith('/portal-api/otp/request')) {
        portalCalls.push({
          url,
          headers: (init?.headers as Record<string, string>) ?? {},
          body: typeof init?.body === 'string' ? init.body : '',
        });
        return new Response(
          JSON.stringify({ status: 'ok', message: 'Demo OTP queued for synthetic session.' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      return new Response('{}', { status: 404 });
    }) as typeof fetch;

    act(() => {
      root?.render(<App initialPage="login" />);
    });

    const input = container?.querySelector(
      '[data-testid="identifier-input"]',
    ) as HTMLInputElement | null;
    const sendBtn = container?.querySelector(
      '[data-testid="send-otp-btn"]',
    ) as HTMLButtonElement | null;
    expect(input).not.toBeNull();
    expect(sendBtn?.textContent).toBe('Send OTP');

    const secretIdentifier = '999988887777';
    act(() => {
      if (input) setInputValue(input, secretIdentifier);
    });

    await act(async () => {
      sendBtn?.click();
    });

    expect(portalCalls).toHaveLength(1);
    expect(portalCalls[0]?.headers['X-Human-Token']).toBe('tok_human_login_123');
    expect(portalCalls[0]?.body).not.toContain(secretIdentifier);
    expect(JSON.parse(portalCalls[0]?.body ?? '{}')).toEqual({
      action: 'otp_request',
      identifier_length: 12,
    });

    const otpResult = container?.querySelector('[data-testid="otp-result"]');
    expect(otpResult?.getAttribute('data-outcome')).toBe('accepted');
    expect(otpResult?.textContent).toContain('Demo OTP queued for synthetic session.');
  });

  it('submits "Update details" form and "Centre search" page without leaking typed strings', async () => {
    const portalCalls: Array<{ url: string; headers: Record<string, string>; body: string }> = [];

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString();
      if (url.endsWith('/v1/nonce')) {
        return new Response(JSON.stringify({ nonce: 'nonce_test_654321', expires_in_s: 120 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.endsWith('/v1/assess')) {
        return new Response(
          JSON.stringify({
            decision: 'allow',
            score: 0.08,
            band: 'low',
            action: 'details_update',
            token: 'tok_human_portal_456',
            reasons: [],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      if (url.startsWith('/portal-api/')) {
        portalCalls.push({
          url,
          headers: (init?.headers as Record<string, string>) ?? {},
          body: typeof init?.body === 'string' ? init.body : '',
        });
        return new Response(
          JSON.stringify({ status: 'ok', message: 'Accepted by demo portal API.' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        );
      }
      return new Response('{}', { status: 404 });
    }) as typeof fetch;

    act(() => {
      root?.render(<App initialPage="update-details" />);
    });

    const nameInput = container?.querySelector(
      '[data-testid="detail-name-input"]',
    ) as HTMLInputElement | null;
    const confirmCheckbox = container?.querySelector(
      '[data-testid="detail-confirm-checkbox"]',
    ) as HTMLInputElement | null;
    const submitDetailsBtn = container?.querySelector(
      '[data-testid="submit-details-btn"]',
    ) as HTMLButtonElement | null;

    act(() => {
      if (nameInput) setInputValue(nameInput, 'SecretCitizenName');
      confirmCheckbox?.click();
    });

    await act(async () => {
      submitDetailsBtn?.click();
    });

    expect(portalCalls).toHaveLength(1);
    expect(portalCalls[0]?.url).toBe('/portal-api/details/update');
    expect(portalCalls[0]?.body).not.toContain('SecretCitizenName');

    // Switch to Centre search
    const navCentres = container?.querySelector(
      '[data-testid="nav-centre-search"]',
    ) as HTMLButtonElement | null;
    act(() => {
      navCentres?.click();
    });

    const queryInput = container?.querySelector(
      '[data-testid="centre-query-input"]',
    ) as HTMLInputElement | null;
    const searchBtn = container?.querySelector(
      '[data-testid="search-centres-btn"]',
    ) as HTMLButtonElement | null;

    act(() => {
      if (queryInput) setInputValue(queryInput, '560001-Indiranagar');
    });

    await act(async () => {
      searchBtn?.click();
    });

    expect(portalCalls).toHaveLength(2);
    expect(portalCalls[1]?.url).toBe('/portal-api/centres/search');
    expect(portalCalls[1]?.body).not.toContain('560001-Indiranagar');
    expect(container?.querySelector('[data-testid="centre-results"]')).not.toBeNull();
  });
});

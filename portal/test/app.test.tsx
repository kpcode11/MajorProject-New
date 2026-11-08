import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { App, DEMO_DISCLAIMER_TEXT } from '../src/App';

let container: HTMLDivElement | null = null;
let root: Root | null = null;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  if (root) {
    act(() => {
      root?.unmount();
    });
    root = null;
  }
  container?.remove();
  container = null;
});

describe('Mock portal scaffold (P7-01)', () => {
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
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  BotGuardChallengeCancelledError,
  type ChallengeInfo,
  createChallengeHandler,
  renderPressHoldChallenge,
} from '../src/index';

let clock = 0;
const now = (): number => clock;

const CHALLENGE: ChallengeInfo = {
  id: 'chal-ui-1',
  type: 'press_hold',
  hold_ms: 1000,
  expires_in: 60,
};

function dispatchTrusted(target: EventTarget, event: Event): void {
  Object.defineProperty(event, 'isTrusted', { value: true });
  target.dispatchEvent(event);
}

afterEach(() => {
  clock = 0;
  document.body.innerHTML = '';
  vi.useRealTimers();
});

describe('renderPressHoldChallenge & createChallengeHandler (P6-08)', () => {
  it('renders an accessible dialog and resolves on a mouse hold >= hold_ms', async () => {
    const promise = renderPressHoldChallenge(CHALLENGE, 'otp_request', { now });

    const dialog = document.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    expect(dialog?.getAttribute('aria-modal')).toBe('true');

    const holdBtn = document.querySelector('.botguard-challenge-hold-btn') as HTMLButtonElement;
    expect(holdBtn).not.toBeNull();

    // Early release (< 1000 ms) keeps the dialog open and prompts the user to hold longer
    clock = 100;
    dispatchTrusted(holdBtn, new MouseEvent('mousedown', { bubbles: true }));
    clock = 600;
    dispatchTrusted(holdBtn, new MouseEvent('mouseup', { bubbles: true }));
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    expect(document.querySelector('.botguard-challenge-status')?.textContent).toContain(
      'Released too early',
    );

    // Full hold (>= 1000 ms) resolves and removes the dialog from the DOM
    clock = 1_000;
    dispatchTrusted(holdBtn, new MouseEvent('mousedown', { bubbles: true }));
    clock = 2_150;
    dispatchTrusted(holdBtn, new MouseEvent('mouseup', { bubbles: true }));

    const result = await promise;
    expect(result).toEqual({ holdStartMs: 1_000, holdEndMs: 2_150 });
    expect(document.querySelector('.botguard-challenge-root')).toBeNull();
  });

  it('supports keyboard Space/Enter press-and-hold on the hold button', async () => {
    const handler = createChallengeHandler({ now });
    const promise = handler(CHALLENGE, 'login');

    const holdBtn = document.querySelector('.botguard-challenge-hold-btn') as HTMLButtonElement;
    clock = 200;
    dispatchTrusted(holdBtn, new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
    // Auto-repeat keydown should be ignored
    clock = 500;
    dispatchTrusted(
      holdBtn,
      new KeyboardEvent('keydown', { key: ' ', repeat: true, bubbles: true }),
    );
    clock = 1_300;
    dispatchTrusted(holdBtn, new KeyboardEvent('keyup', { key: ' ', bubbles: true }));

    const result = await promise;
    expect(result).toEqual({ holdStartMs: 200, holdEndMs: 1_300 });
  });

  it('supports the single-activation keyboard accessibility button', async () => {
    vi.useFakeTimers();
    clock = 500;
    const promise = renderPressHoldChallenge(CHALLENGE, 'otp_request', { now });

    const kbBtn = document.querySelector('.botguard-challenge-kb-btn') as HTMLButtonElement;
    expect(kbBtn).not.toBeNull();
    dispatchTrusted(kbBtn, new MouseEvent('click', { bubbles: true }));

    clock = 1_550;
    vi.advanceTimersByTime(1_000);

    const result = await promise;
    expect(result.holdStartMs).toBe(500);
    expect(result.holdEndMs).toBeGreaterThanOrEqual(1_500);
  });

  it('rejects with BotGuardChallengeCancelledError on Cancel click or Escape key', async () => {
    const p1 = renderPressHoldChallenge(CHALLENGE, 'otp_request', { now });
    const cancelBtn = document.querySelector('.botguard-challenge-cancel-btn') as HTMLButtonElement;
    cancelBtn.click();
    await expect(p1).rejects.toThrowError(BotGuardChallengeCancelledError);

    const p2 = renderPressHoldChallenge(CHALLENGE, 'otp_request', { now });
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await expect(p2).rejects.toThrowError(BotGuardChallengeCancelledError);
  });

  it('supports a custom pluggable ChallengeRenderer and calls its cleanup function', async () => {
    const cleanupSpy = vi.fn();
    const result = await renderPressHoldChallenge(CHALLENGE, 'details_update', {
      renderer: (ctx) => {
        const btn = ctx.container.ownerDocument.createElement('button');
        btn.id = 'custom-verify';
        ctx.container.appendChild(btn);
        queueMicrotask(() => ctx.complete({ holdStartMs: 10, holdEndMs: 1210 }));
        return cleanupSpy;
      },
    });
    expect(result).toEqual({ holdStartMs: 10, holdEndMs: 1210 });
    expect(cleanupSpy).toHaveBeenCalledTimes(1);
    expect(document.getElementById('custom-verify')).toBeNull();
  });

  it('meets P7-09 accessibility invariants: labelled controls, focus ring, Tab trap, focus restore, and keyboard Space/Enter path without time pressure', async () => {
    vi.useFakeTimers();
    const triggerBtn = document.createElement('button');
    triggerBtn.id = 'host-submit-btn';
    document.body.appendChild(triggerBtn);
    triggerBtn.focus();
    expect(document.activeElement).toBe(triggerBtn);

    clock = 100;
    const promise = renderPressHoldChallenge(CHALLENGE, 'otp_request', { now });

    const dialog = document.querySelector('[data-testid="stepup-dialog"]') as HTMLElement;
    const holdBtn = document.querySelector('[data-testid="stepup-hold-btn"]') as HTMLButtonElement;
    const kbBtn = document.querySelector('[data-testid="stepup-kb-btn"]') as HTMLButtonElement;
    const cancelBtn = document.querySelector(
      '[data-testid="stepup-cancel-btn"]',
    ) as HTMLButtonElement;
    const progress = document.querySelector('[data-testid="stepup-progress"]') as HTMLElement;
    const status = document.querySelector('[data-testid="stepup-status"]') as HTMLElement;
    const styleTag = dialog.querySelector('style');

    // 1. Labelled controls & ARIA roles
    expect(dialog.getAttribute('role')).toBe('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.getAttribute('aria-labelledby')).toBe('botguard-challenge-title');
    expect(dialog.getAttribute('aria-describedby')).toBe('botguard-challenge-desc');
    expect(holdBtn.getAttribute('aria-label')).toContain('Press and hold');
    expect(kbBtn.getAttribute('aria-label')).toContain('Keyboard accessible');
    expect(cancelBtn.getAttribute('aria-label')).toBe('Cancel verification');
    expect(progress.getAttribute('role')).toBe('progressbar');
    expect(status.getAttribute('role')).toBe('status');
    expect(status.getAttribute('aria-live')).toBe('polite');

    // 2. Visible focus ring CSS rule present
    expect(styleTag?.textContent).toContain(':focus-visible');
    expect(styleTag?.textContent).toContain('outline:3px solid #0284c7');

    // 3. Initial focus on holdBtn and Tab / Shift+Tab focus trap inside modal
    expect(document.activeElement).toBe(holdBtn);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
    expect(document.activeElement).toBe(kbBtn);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
    expect(document.activeElement).toBe(cancelBtn);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
    expect(document.activeElement).toBe(holdBtn);

    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true }),
    );
    expect(document.activeElement).toBe(cancelBtn);

    // Tab back to kbBtn and activate via Space key (no physical hold required)
    document.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true }),
    );
    expect(document.activeElement).toBe(kbBtn);

    dispatchTrusted(kbBtn, new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
    clock = 1_150;
    vi.advanceTimersByTime(1_000);

    const result = await promise;
    expect(result.holdStartMs).toBe(100);
    expect(result.holdEndMs).toBeGreaterThanOrEqual(1_100);

    // 4. Focus restored to original trigger button after modal closes
    expect(document.activeElement).toBe(triggerBtn);
  });

  it('rejects with challenge_expired when expires_in timeout elapses before completion (P7-10)', async () => {
    vi.useFakeTimers();
    const shortChallenge: ChallengeInfo = {
      id: 'chal-timeout-1',
      type: 'press_hold',
      hold_ms: 1000,
      expires_in: 2,
    };
    const promise = renderPressHoldChallenge(shortChallenge, 'otp_request', { now });
    // Attach rejection handler before advancing timers so Node does not flag unhandled rejection
    const assertion = expect(promise).rejects.toThrowError(/challenge_expired/);
    vi.advanceTimersByTime(2_100);
    await assertion;
    expect(document.querySelector('[data-testid="stepup-dialog"]')).toBeNull();
  });
});

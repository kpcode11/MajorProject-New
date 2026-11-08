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
});

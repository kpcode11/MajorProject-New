/**
 * Pluggable step-up challenge UI (P6-08, plus default accessible press-and-hold UI for P7-06).
 *
 * Design:
 * - No image or text puzzles.
 * - Default UI renders an accessible dialog (`role="dialog"`, `aria-modal="true"`) with:
 *   1. A **Press and Hold** button whose hold duration comes from `challenge.hold_ms` (server-chosen
 *      random duration, 800-1500 ms). Supports mouse (`mousedown`/`mouseup`), touch
 *      (`touchstart`/`touchend`), and keyboard hold (`Space`/`Enter` keydown/keyup).
 *   2. An explicit keyboard-accessible single-activation alternative button (**Verify with
 *      Keyboard**) so users who cannot sustain a physical hold can complete the step-up with a
 *      single `Space`/`Enter` activation (waits for `hold_ms` with an accessible status announcement).
 *   3. A **Cancel** button and `Escape` key support.
 * - Pluggable: callers can pass a custom `ChallengeRenderer` to {@link createChallengeHandler} or
 *   register any `ChallengeHandler` via `BotGuard.setChallengeHandler(...)`.
 */
import type { ChallengeInfo } from './transport';

/** Timing result captured during a step-up challenge interaction. */
export interface ChallengeInteractionResult {
  holdStartMs: number;
  holdEndMs: number;
}

/** Function signature invoked by `BotGuardClient.runChallenge`. */
export type ChallengeHandler = (
  challenge: ChallengeInfo,
  action: string,
) => Promise<ChallengeInteractionResult>;

/** Context passed to a custom {@link ChallengeRenderer}. */
export interface ChallengeRenderContext {
  challenge: ChallengeInfo;
  action: string;
  container: HTMLElement;
  /** Resolve the challenge with the captured start/end timestamps (ms). */
  complete: (result: ChallengeInteractionResult) => void;
  /** Reject/cancel the challenge. */
  cancel: (reason?: string) => void;
}

/**
 * Custom renderer function for pluggable challenge UIs.
 * May return a cleanup function that is called when the challenge finishes or is cancelled.
 */
export type ChallengeRenderer = (ctx: ChallengeRenderContext) => (() => void) | undefined;

/** Options for {@link renderPressHoldChallenge} and {@link createChallengeHandler}. */
export interface ChallengeUIOptions {
  /** Parent element where the challenge dialog container is mounted (defaults to `document.body`). */
  mountTarget?: HTMLElement;
  /** Clock in milliseconds; defaults to `performance.now()`. */
  now?: () => number;
  /** Optional custom renderer; when omitted, the built-in press-and-hold dialog is used. */
  renderer?: ChallengeRenderer;
  /** Require `event.isTrusted !== false` on user events (default `true`). */
  requireTrusted?: boolean;
}

/** Error raised when a step-up challenge is cancelled or expires before completion. */
export class BotGuardChallengeCancelledError extends Error {
  constructor(message = 'Step-up challenge was cancelled') {
    super(message);
    this.name = 'BotGuardChallengeCancelledError';
  }
}

const round1 = (v: number): number => Math.round(v * 10) / 10;

function createEl<K extends keyof HTMLElementTagNameMap>(
  doc: Document,
  tag: K,
  attrs: Record<string, string> = {},
  text?: string,
): HTMLElementTagNameMap[K] {
  const el = doc.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, v);
  }
  if (text !== undefined) {
    el.textContent = text;
  }
  return el;
}

/**
 * Built-in accessible press-and-hold step-up challenge renderer.
 */
export function defaultPressHoldRenderer(
  ctx: ChallengeRenderContext,
  options: Pick<ChallengeUIOptions, 'now' | 'requireTrusted'> = {},
): () => void {
  const now = options.now ?? (() => performance.now());
  const requireTrusted = options.requireTrusted ?? true;
  const doc = ctx.container.ownerDocument;
  const holdTargetMs = Math.max(100, ctx.challenge.hold_ms);

  const previousActive = doc.activeElement instanceof HTMLElement ? doc.activeElement : null;

  const backdrop = createEl(doc, 'div', {
    class: 'botguard-challenge-backdrop',
    'data-testid': 'stepup-backdrop',
    style:
      'position:fixed;inset:0;display:flex;align-items:center;justify-content:center;' +
      'background:rgba(15,23,42,0.55);z-index:2147483647;font-family:system-ui,sans-serif;',
  });

  const styleEl = createEl(
    doc,
    'style',
    {},
    '.botguard-challenge-dialog button:focus,' +
      '.botguard-challenge-dialog button:focus-visible{' +
      'outline:3px solid #0284c7;outline-offset:2px;}',
  );

  const dialog = createEl(doc, 'div', {
    role: 'dialog',
    'aria-modal': 'true',
    'aria-labelledby': 'botguard-challenge-title',
    'aria-describedby': 'botguard-challenge-desc',
    'data-testid': 'stepup-dialog',
    'data-hold-ms': String(holdTargetMs),
    class: 'botguard-challenge-dialog',
    style:
      'background:#ffffff;color:#0f172a;border-radius:12px;padding:24px;max-width:380px;' +
      'width:90%;box-shadow:0 20px 25px -5px rgba(0,0,0,0.2);text-align:center;',
  });

  const title = createEl(
    doc,
    'h2',
    {
      id: 'botguard-challenge-title',
      style: 'margin:0 0 8px;font-size:18px;font-weight:600;',
    },
    'Quick Verification Required',
  );

  const secs = (holdTargetMs / 1000).toFixed(1);
  const desc = createEl(
    doc,
    'p',
    {
      id: 'botguard-challenge-desc',
      style: 'margin:0 0 16px;font-size:14px;color:#475569;line-height:1.4;',
    },
    `Please press and hold the button below for ${secs} seconds to continue.`,
  );

  const progressTrack = createEl(doc, 'div', {
    role: 'progressbar',
    'data-testid': 'stepup-progress',
    'aria-label': 'Verification hold progress',
    'aria-valuemin': '0',
    'aria-valuemax': String(holdTargetMs),
    'aria-valuenow': '0',
    style: 'height:8px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin-bottom:16px;',
  });

  const progressFill = createEl(doc, 'div', {
    class: 'botguard-challenge-progress-fill',
    style: 'height:100%;width:0%;background:#2563eb;transition:width 40ms linear;',
  });
  progressTrack.appendChild(progressFill);

  const holdBtn = createEl(
    doc,
    'button',
    {
      type: 'button',
      class: 'botguard-challenge-hold-btn',
      'data-testid': 'stepup-hold-btn',
      'aria-label': `Press and hold for ${secs} seconds to verify`,
      style:
        'width:100%;padding:12px 16px;font-size:15px;font-weight:600;color:#ffffff;' +
        'background:#1d4ed8;border:2px solid transparent;border-radius:8px;cursor:pointer;' +
        'user-select:none;touch-action:none;outline-offset:2px;',
    },
    'Press and Hold to Verify',
  );

  const kbAltBtn = createEl(
    doc,
    'button',
    {
      type: 'button',
      class: 'botguard-challenge-kb-btn',
      'data-testid': 'stepup-kb-btn',
      'aria-label': 'Keyboard accessible single-press verification alternative',
      style:
        'margin-top:10px;width:100%;padding:8px 12px;font-size:13px;color:#1e293b;' +
        'background:#f1f5f9;border:1px solid #cbd5e1;border-radius:6px;cursor:pointer;',
    },
    'Use Keyboard Single-Press Verify',
  );

  const statusLive = createEl(
    doc,
    'div',
    {
      role: 'status',
      'aria-live': 'polite',
      'data-testid': 'stepup-status',
      class: 'botguard-challenge-status',
      style: 'margin-top:10px;min-height:18px;font-size:13px;color:#475569;',
    },
    '',
  );

  const cancelBtn = createEl(
    doc,
    'button',
    {
      type: 'button',
      class: 'botguard-challenge-cancel-btn',
      'data-testid': 'stepup-cancel-btn',
      'aria-label': 'Cancel verification',
      style:
        'margin-top:8px;padding:6px 12px;font-size:12px;color:#64748b;background:transparent;' +
        'border:none;cursor:pointer;text-decoration:underline;',
    },
    'Cancel',
  );

  dialog.append(styleEl, title, desc, progressTrack, holdBtn, kbAltBtn, statusLive, cancelBtn);
  backdrop.appendChild(dialog);
  ctx.container.appendChild(backdrop);

  let holdStart: number | null = null;
  let holdReached = false;
  let kbAutoTimer: ReturnType<typeof setTimeout> | null = null;
  let progressTimer: ReturnType<typeof setInterval> | null = null;
  let expiryTimer: ReturnType<typeof setTimeout> | null = null;
  let finished = false;

  const isTrustedOk = (event: Event): boolean => !requireTrusted || event.isTrusted !== false;

  const clearTimers = (): void => {
    if (kbAutoTimer !== null) {
      clearTimeout(kbAutoTimer);
      kbAutoTimer = null;
    }
    if (progressTimer !== null) {
      clearInterval(progressTimer);
      progressTimer = null;
    }
    if (expiryTimer !== null) {
      clearTimeout(expiryTimer);
      expiryTimer = null;
    }
  };

  const setProgress = (elapsedMs: number): void => {
    const clamped = Math.min(holdTargetMs, Math.max(0, Math.round(elapsedMs)));
    const pct = Math.min(100, Math.round((clamped / holdTargetMs) * 100));
    progressFill.style.width = `${pct}%`;
    progressTrack.setAttribute('aria-valuenow', String(clamped));
  };

  const beginHold = (event: Event): void => {
    if (finished || !isTrustedOk(event) || holdStart !== null) return;
    holdStart = round1(Math.max(0, now()));
    holdReached = false;
    statusLive.textContent = 'Holding… keep pressing.';
    holdBtn.textContent = 'Keep Holding…';
    setProgress(0);

    progressTimer = setInterval(() => {
      if (holdStart === null) return;
      const elapsed = Math.max(0, now() - holdStart);
      setProgress(elapsed);
      if (elapsed >= holdTargetMs && !holdReached) {
        holdReached = true;
        statusLive.textContent = 'Hold complete — release to finish.';
        holdBtn.textContent = 'Release to Complete';
      }
    }, 30);
  };

  const finishHold = (event: Event): void => {
    if (finished || !isTrustedOk(event) || holdStart === null) return;
    const startMs = holdStart;
    const endMs = round1(Math.max(startMs, now()));
    const elapsed = endMs - startMs;
    holdStart = null;
    if (progressTimer !== null) {
      clearInterval(progressTimer);
      progressTimer = null;
    }

    if (elapsed >= holdTargetMs) {
      finished = true;
      clearTimers();
      setProgress(holdTargetMs);
      statusLive.textContent = 'Verification complete.';
      ctx.complete({ holdStartMs: startMs, holdEndMs: endMs });
    } else {
      setProgress(0);
      holdBtn.textContent = 'Press and Hold to Verify';
      statusLive.textContent = `Released too early (${Math.round(elapsed)} ms). Please hold for ${secs} s.`;
    }
  };

  const onHoldKeyDown = (event: KeyboardEvent): void => {
    if (event.repeat) return;
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      beginHold(event);
    }
  };

  const onHoldKeyUp = (event: KeyboardEvent): void => {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      finishHold(event);
    }
  };

  const onKbAltClick = (event: Event): void => {
    if (finished || !isTrustedOk(event) || kbAutoTimer !== null) return;
    const startMs = round1(Math.max(0, now()));
    holdStart = startMs;
    kbAltBtn.setAttribute('disabled', 'true');
    holdBtn.setAttribute('disabled', 'true');
    statusLive.textContent = 'Verifying via keyboard accessibility path…';
    setProgress(holdTargetMs * 0.5);

    kbAutoTimer = setTimeout(() => {
      if (finished) return;
      finished = true;
      clearTimers();
      const endMs = round1(Math.max(startMs + holdTargetMs, now()));
      setProgress(holdTargetMs);
      statusLive.textContent = 'Verification complete.';
      ctx.complete({ holdStartMs: startMs, holdEndMs: endMs });
    }, holdTargetMs);
  };

  const onKbAltKeyDown = (event: KeyboardEvent): void => {
    if (event.repeat) return;
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      onKbAltClick(event);
    }
  };

  const onCancelClick = (): void => {
    if (finished) return;
    finished = true;
    clearTimers();
    ctx.cancel('user_cancelled');
  };

  const focusableButtons = [holdBtn, kbAltBtn, cancelBtn];

  const onDocKeyDown = (event: KeyboardEvent): void => {
    if (event.key === 'Escape' && !finished) {
      finished = true;
      clearTimers();
      ctx.cancel('escape_pressed');
      return;
    }
    if (event.key === 'Tab' && !finished) {
      const enabledBtns = focusableButtons.filter((b) => !b.hasAttribute('disabled'));
      if (enabledBtns.length === 0) return;
      const activeIdx = enabledBtns.indexOf(doc.activeElement as HTMLButtonElement);
      event.preventDefault();
      if (event.shiftKey) {
        const prevIdx = activeIdx <= 0 ? enabledBtns.length - 1 : activeIdx - 1;
        enabledBtns[prevIdx]?.focus();
      } else {
        const nextIdx = activeIdx < 0 || activeIdx >= enabledBtns.length - 1 ? 0 : activeIdx + 1;
        enabledBtns[nextIdx]?.focus();
      }
    }
  };

  holdBtn.addEventListener('mousedown', beginHold);
  holdBtn.addEventListener('mouseup', finishHold);
  holdBtn.addEventListener('touchstart', beginHold, { passive: true });
  holdBtn.addEventListener('touchend', finishHold, { passive: true });
  holdBtn.addEventListener('keydown', onHoldKeyDown);
  holdBtn.addEventListener('keyup', onHoldKeyUp);
  kbAltBtn.addEventListener('click', onKbAltClick);
  kbAltBtn.addEventListener('keydown', onKbAltKeyDown);
  cancelBtn.addEventListener('click', onCancelClick);
  doc.addEventListener('keydown', onDocKeyDown);

  if (ctx.challenge.expires_in > 0) {
    expiryTimer = setTimeout(() => {
      if (!finished) {
        finished = true;
        clearTimers();
        ctx.cancel('challenge_expired');
      }
    }, ctx.challenge.expires_in * 1000);
  }

  try {
    holdBtn.focus();
  } catch {
    /* ignore focus errors in headless environments */
  }

  return () => {
    finished = true;
    clearTimers();
    holdBtn.removeEventListener('mousedown', beginHold);
    holdBtn.removeEventListener('mouseup', finishHold);
    holdBtn.removeEventListener('touchstart', beginHold);
    holdBtn.removeEventListener('touchend', finishHold);
    holdBtn.removeEventListener('keydown', onHoldKeyDown);
    holdBtn.removeEventListener('keyup', onHoldKeyUp);
    kbAltBtn.removeEventListener('click', onKbAltClick);
    kbAltBtn.removeEventListener('keydown', onKbAltKeyDown);
    cancelBtn.removeEventListener('click', onCancelClick);
    doc.removeEventListener('keydown', onDocKeyDown);
    backdrop.remove();
    try {
      if (previousActive && previousActive.isConnected) {
        previousActive.focus();
      }
    } catch {
      /* ignore focus restore errors */
    }
  };
}

/**
 * Render a step-up challenge UI (default or custom renderer) and resolve with
 * `{ holdStartMs, holdEndMs }` when the user completes it.
 */
export function renderPressHoldChallenge(
  challenge: ChallengeInfo,
  action: string,
  options: ChallengeUIOptions = {},
): Promise<ChallengeInteractionResult> {
  if (typeof document === 'undefined' && !options.mountTarget) {
    return Promise.reject(new BotGuardChallengeCancelledError('DOM document is not available'));
  }

  const parent = options.mountTarget ?? document.body;
  const doc = parent.ownerDocument ?? document;
  const container = doc.createElement('div');
  container.className = 'botguard-challenge-root';
  parent.appendChild(container);

  return new Promise<ChallengeInteractionResult>((resolve, reject) => {
    let settled = false;
    const state: { cleanup?: () => void } = {};

    const finish = (cb: () => void): void => {
      if (settled) return;
      settled = true;
      try {
        state.cleanup?.();
      } finally {
        container.remove();
      }
      cb();
    };

    const ctx: ChallengeRenderContext = {
      challenge,
      action,
      container,
      complete: (result) => finish(() => resolve(result)),
      cancel: (reason) => finish(() => reject(new BotGuardChallengeCancelledError(reason))),
    };

    const renderer =
      options.renderer ??
      ((renderCtx: ChallengeRenderContext) => defaultPressHoldRenderer(renderCtx, options));

    state.cleanup = renderer(ctx);
  });
}

/**
 * Create a {@link ChallengeHandler} bound to the given UI options (mount target, custom renderer,
 * clock). Used as the default handler by `BotGuardClient` and customisable by host apps.
 */
export function createChallengeHandler(options: ChallengeUIOptions = {}): ChallengeHandler {
  return (challenge, action) => renderPressHoldChallenge(challenge, action, options);
}

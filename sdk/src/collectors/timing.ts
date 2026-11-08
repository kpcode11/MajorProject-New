/**
 * Page-level timing and focus/visibility collector (Appendix B.3 `behaviour.timing`, P6-05).
 *
 * Tracks:
 * - `ms_since_load`: milliseconds elapsed since page load (`performance.now()`, or relative to the
 *   configured load timestamp).
 * - `ms_to_first_interaction`: milliseconds from page load to the first trusted user interaction
 *   (`mousedown`, `keydown`, `touchstart`, `pointerdown`, `wheel`, `scroll`). Omitted if no
 *   interaction has occurred yet.
 * - `ms_since_nonce`: milliseconds elapsed since the server nonce was issued/received. Omitted if
 *   no nonce timestamp has been recorded.
 * - `scroll_events`: total scroll event count (taken from {@link ScrollCollector} or passed into
 *   `snapshot()`).
 * - `focus_changes`: count of window `focus`/`blur` and document `visibilitychange` transitions.
 *
 * All values are clamped to the backend schema bounds (`0..3_600_000` ms, `0..100_000` scrolls,
 * `0..10_000` focus changes; see `backend/app/schemas.py` `TimingSignals`).
 */
import { ScrollCollector } from './scroll';

/** Page-level timing signals matching `TimingSignals` in `backend/app/schemas.py`. */
export interface TimingSignals {
  ms_since_load?: number;
  ms_to_first_interaction?: number;
  ms_since_nonce?: number;
  scroll_events?: number;
  focus_changes?: number;
}

/** Options for {@link TimingCollector}. */
export interface TimingCollectorOptions {
  /** Clock in milliseconds; defaults to `performance.now()`. */
  now?: () => number;
  /** Optional scroll collector whose count is included in `snapshot()`. */
  scrollCollector?: ScrollCollector;
  /** Optional page-load baseline in the `now()` clock's units; defaults to `0`. */
  loadTimeMs?: number;
}

const MAX_MS = 3_600_000;
const MAX_SCROLL = 100_000;
const MAX_FOCUS = 10_000;

const INTERACTION_EVENTS = [
  'mousedown',
  'keydown',
  'touchstart',
  'pointerdown',
  'wheel',
  'scroll',
] as const;

const FOCUS_EVENTS = ['focus', 'blur'] as const;

const round1 = (v: number): number => Math.round(v * 10) / 10;

function clampMs(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return round1(Math.min(MAX_MS, Math.max(0, v)));
}

export class TimingCollector {
  private readonly now: () => number;
  private readonly scroll: ScrollCollector | null;
  private readonly loadTimeMs: number;
  private target: EventTarget | null = null;
  private docTarget: EventTarget | null = null;
  private firstInteractionMs: number | null = null;
  private nonceIssuedMs: number | null = null;
  private focusChanges = 0;

  private readonly onInteract = (event: Event): void => {
    if (event.isTrusted === false) return;
    if (this.firstInteractionMs === null) {
      this.firstInteractionMs = Math.max(0, this.now() - this.loadTimeMs);
    }
  };

  private readonly onFocusOrVisibility = (): void => {
    this.focusChanges = Math.min(MAX_FOCUS, this.focusChanges + 1);
  };

  constructor(options: TimingCollectorOptions = {}) {
    this.now = options.now ?? (() => performance.now());
    this.scroll = options.scrollCollector ?? null;
    this.loadTimeMs = options.loadTimeMs ?? 0;
  }

  /** True while listeners are attached. */
  get running(): boolean {
    return this.target !== null;
  }

  /**
   * Attach passive listeners to `target` (default `window`) and `visibilitychange` on its
   * document. Also starts the linked {@link ScrollCollector} if one was provided. Idempotent.
   */
  start(target: EventTarget = window): void {
    if (this.target) return;
    this.target = target;
    for (const type of INTERACTION_EVENTS) {
      target.addEventListener(type, this.onInteract, { passive: true, capture: true });
    }
    for (const type of FOCUS_EVENTS) {
      target.addEventListener(type, this.onFocusOrVisibility, { passive: true, capture: true });
    }
    const maybeDoc =
      (target as { document?: EventTarget }).document ??
      (typeof document !== 'undefined' ? document : null);
    if (maybeDoc && typeof maybeDoc.addEventListener === 'function') {
      this.docTarget = maybeDoc;
      maybeDoc.addEventListener('visibilitychange', this.onFocusOrVisibility, { passive: true });
    }
    this.scroll?.start(target);
  }

  /** Remove all listeners and reset state (including any linked {@link ScrollCollector}). */
  stop(): void {
    if (this.target) {
      for (const type of INTERACTION_EVENTS) {
        this.target.removeEventListener(type, this.onInteract, { capture: true });
      }
      for (const type of FOCUS_EVENTS) {
        this.target.removeEventListener(type, this.onFocusOrVisibility, { capture: true });
      }
      this.target = null;
    }
    if (this.docTarget) {
      this.docTarget.removeEventListener('visibilitychange', this.onFocusOrVisibility);
      this.docTarget = null;
    }
    this.scroll?.stop();
    this.reset();
  }

  /** Reset recorded timing/focus state while keeping listeners attached. */
  reset(): void {
    this.firstInteractionMs = null;
    this.nonceIssuedMs = null;
    this.focusChanges = 0;
    this.scroll?.reset();
  }

  /** Record that a nonce was just received (or at timestamp `atMs` in `now()` units). */
  markNonce(atMs: number = this.now()): void {
    if (Number.isFinite(atMs)) {
      this.nonceIssuedMs = atMs;
    }
  }

  /** Build the `TimingSignals` snapshot at the current time. */
  snapshot(scrollEventsOverride?: number): TimingSignals {
    const current = this.now();
    const scrollCount = scrollEventsOverride ?? (this.scroll ? this.scroll.snapshot() : 0);
    const out: TimingSignals = {
      ms_since_load: clampMs(current - this.loadTimeMs),
      scroll_events: Math.min(MAX_SCROLL, Math.max(0, Math.round(scrollCount))),
      focus_changes: this.focusChanges,
    };
    if (this.firstInteractionMs !== null) {
      out.ms_to_first_interaction = clampMs(this.firstInteractionMs);
    }
    if (this.nonceIssuedMs !== null) {
      out.ms_since_nonce = clampMs(current - this.nonceIssuedMs);
    }
    return out;
  }
}

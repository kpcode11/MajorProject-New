/**
 * Scroll collector (Appendix B.3 `behaviour.timing.scroll_events`, P6-05).
 *
 * Counts trusted `scroll` events using a passive capture listener so nested scrollable
 * containers are counted as well. Bounded by the backend's 100,000 cap (`schemas.py`).
 */

/** Backend cap (`schemas.py` `TimingSignals.scroll_events`). */
const MAX_SCROLL = 100_000;

export class ScrollCollector {
  private target: EventTarget | null = null;
  private count = 0;
  private readonly listener = (event: Event): void => {
    if (event.isTrusted === false) return;
    this.count = Math.min(MAX_SCROLL, this.count + 1);
  };

  /** True while the listener is attached. */
  get running(): boolean {
    return this.target !== null;
  }

  /** Total trusted scroll events recorded since `start()` or `reset()`. */
  get scrollEvents(): number {
    return this.count;
  }

  /** Attach a passive capture `scroll` listener to `target` (default `window`). Idempotent. */
  start(target: EventTarget = window): void {
    if (this.target) return;
    this.target = target;
    target.addEventListener('scroll', this.listener, { passive: true, capture: true });
  }

  /** Remove the listener and clear the counter. Safe to call repeatedly. */
  stop(): void {
    if (this.target) {
      this.target.removeEventListener('scroll', this.listener, { capture: true });
      this.target = null;
    }
    this.reset();
  }

  /** Reset the counter while keeping the listener attached. */
  reset(): void {
    this.count = 0;
  }

  /** Return the current scroll count. */
  snapshot(): number {
    return this.count;
  }
}

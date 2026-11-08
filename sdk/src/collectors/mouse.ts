/**
 * Mouse collector (Appendix B.3 `behaviour.mouse`, P6-03).
 *
 * - `mousemove` is throttled (default 16 ms ≈ 60 Hz) and stored in a bounded ring buffer.
 * - `mousedown`/`mouseup` always add a point (segment boundaries) and pair into click records
 *   `[x, y, down_ms, up_ms]`.
 * - A `click` with no preceding trusted press (for example `element.click()`) is recorded as a
 *   zero-dwell click.
 * - `wheel` events are counted only.
 * - Events with `isTrusted === false` are never stored as points or clicks; they are counted in
 *   `untrusted_count` (used by rule R11).
 *
 * Coordinates are viewport pixels (`clientX`/`clientY`) rounded to integers. Time is milliseconds
 * from the page time origin (`performance.now()`), rounded to 0.1 ms. All listeners are passive.
 * Only the most recent `windowMs` of points and clicks is returned by `snapshot()`.
 */
import { RingBuffer } from '../ringbuffer';

/** Mouse part of the behaviour payload; matches `MouseBehaviour` in backend/app/schemas.py. */
export interface MouseBehaviour {
  points: [number, number, number][];
  clicks: [number, number, number, number][];
  untrusted_count: number;
  wheel_events: number;
}

/** Collector settings (a subset of the SDK config). */
export interface MouseCollectorOptions {
  maxMousePoints: number;
  maxClicks: number;
  mouseThrottleMs: number;
  windowMs: number;
  /** Clock in milliseconds; defaults to `performance.now()`. */
  now?: () => number;
}

/** Backend caps (schemas.py): `untrusted_count ≤ 600`, `wheel_events ≤ 10000`. */
const MAX_UNTRUSTED = 600;
const MAX_WHEEL = 10_000;
/** A `click` within this many ms after a trusted `mouseup` belongs to that press. */
const CLICK_PAIR_MS = 100;

const EVENTS = ['mousemove', 'mousedown', 'mouseup', 'click', 'wheel'] as const;

const round1 = (v: number): number => Math.round(v * 10) / 10;

export class MouseCollector {
  private readonly points: RingBuffer<[number, number, number]>;
  private readonly clicks: RingBuffer<[number, number, number, number]> | null;
  private readonly now: () => number;
  private target: EventTarget | null = null;
  private lastMoveT = Number.NEGATIVE_INFINITY;
  private lastUpT = Number.NEGATIVE_INFINITY;
  private pendingDown: { x: number; y: number; t: number } | null = null;
  private untrusted = 0;
  private wheel = 0;
  private readonly listener = (event: Event): void => this.handle(event);

  constructor(private readonly options: MouseCollectorOptions) {
    this.points = new RingBuffer(options.maxMousePoints);
    this.clicks = options.maxClicks > 0 ? new RingBuffer(options.maxClicks) : null;
    this.now = options.now ?? (() => performance.now());
  }

  /** True while listeners are attached. */
  get running(): boolean {
    return this.target !== null;
  }

  /** Attach passive listeners to `target` (default `window`). Calling twice is a no-op. */
  start(target: EventTarget = window): void {
    if (this.target) return;
    this.target = target;
    for (const type of EVENTS) {
      target.addEventListener(type, this.listener, { passive: true, capture: true });
    }
  }

  /** Remove all listeners and clear buffered data. Safe to call repeatedly. */
  stop(): void {
    if (this.target) {
      for (const type of EVENTS) {
        this.target.removeEventListener(type, this.listener, { capture: true });
      }
      this.target = null;
    }
    this.reset();
  }

  /** Clear buffered data but keep listening. */
  reset(): void {
    this.points.clear();
    this.clicks?.clear();
    this.pendingDown = null;
    this.lastMoveT = Number.NEGATIVE_INFINITY;
    this.lastUpT = Number.NEGATIVE_INFINITY;
    this.untrusted = 0;
    this.wheel = 0;
  }

  /** Return the bounded payload for the most recent `windowMs`. Does not clear the buffers. */
  snapshot(): MouseBehaviour {
    const cutoff = this.now() - this.options.windowMs;
    return {
      points: this.points.toArray().filter((p) => p[2] >= cutoff),
      clicks: this.clicks ? this.clicks.toArray().filter((c) => c[3] >= cutoff) : [],
      untrusted_count: this.untrusted,
      wheel_events: this.wheel,
    };
  }

  private handle(event: Event): void {
    if (event.isTrusted === false) {
      this.untrusted = Math.min(MAX_UNTRUSTED, this.untrusted + 1);
      return;
    }
    if (event.type === 'wheel') {
      this.wheel = Math.min(MAX_WHEEL, this.wheel + 1);
      return;
    }
    const me = event as MouseEvent;
    const x = Math.round(me.clientX);
    const y = Math.round(me.clientY);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    const t = round1(Math.max(0, this.now()));

    switch (event.type) {
      case 'mousemove':
        if (t - this.lastMoveT < this.options.mouseThrottleMs) return;
        this.lastMoveT = t;
        this.points.push([x, y, t]);
        return;
      case 'mousedown':
        this.points.push([x, y, t]);
        this.pendingDown = { x, y, t };
        return;
      case 'mouseup':
        this.points.push([x, y, t]);
        if (this.pendingDown) {
          const d = this.pendingDown;
          this.clicks?.push([d.x, d.y, d.t, Math.max(t, d.t)]);
          this.pendingDown = null;
        }
        this.lastUpT = t;
        return;
      case 'click':
        if (t - this.lastUpT > CLICK_PAIR_MS) {
          this.clicks?.push([x, y, t, t]);
        }
        return;
    }
  }
}

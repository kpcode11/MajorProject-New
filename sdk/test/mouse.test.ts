import { afterEach, describe, expect, it } from 'vitest';
import { MouseCollector } from '../src/collectors/mouse';
import { RingBuffer } from '../src/ringbuffer';

let clock = 0;
const now = (): number => clock;

function makeCollector(overrides: Partial<ConstructorParameters<typeof MouseCollector>[0]> = {}) {
  return new MouseCollector({
    maxMousePoints: 600,
    maxClicks: 50,
    mouseThrottleMs: 16,
    windowMs: 10_000,
    now,
    ...overrides,
  });
}

/** Dispatch a mouse event marked as trusted (happy-dom marks dispatched events untrusted). */
function fire(target: EventTarget, type: string, x = 0, y = 0, trusted = true): void {
  const event =
    type === 'wheel'
      ? new WheelEvent(type, { clientX: x, clientY: y, bubbles: true })
      : new MouseEvent(type, { clientX: x, clientY: y, bubbles: true });
  Object.defineProperty(event, 'isTrusted', { value: trusted });
  target.dispatchEvent(event);
}

let collector: MouseCollector | null = null;
afterEach(() => {
  collector?.stop();
  collector = null;
  clock = 0;
});

describe('RingBuffer', () => {
  it('keeps only the newest items up to capacity', () => {
    const rb = new RingBuffer<number>(3);
    [1, 2, 3, 4, 5].forEach((v) => rb.push(v));
    expect(rb.size).toBe(3);
    expect(rb.toArray()).toEqual([3, 4, 5]);
    rb.clear();
    expect(rb.toArray()).toEqual([]);
    expect(() => new RingBuffer(0)).toThrow(RangeError);
  });
});

describe('MouseCollector', () => {
  it('records throttled moves as [x, y, t_ms]', () => {
    collector = makeCollector();
    collector.start(window);
    for (let i = 0; i < 10; i += 1) {
      clock = i * 5; // 5 ms apart -> only every 4th sample passes a 16 ms throttle
      fire(window, 'mousemove', 10 + i, 20.6);
    }
    const { points } = collector.snapshot();
    expect(points).toEqual([
      [10, 21, 0],
      [14, 21, 20],
      [18, 21, 40],
    ]);
  });

  it('pairs down/up into clicks and adds boundary points', () => {
    collector = makeCollector();
    collector.start(window);
    clock = 100;
    fire(window, 'mousedown', 50, 60);
    clock = 180;
    fire(window, 'mouseup', 51, 60);
    clock = 181;
    fire(window, 'click', 51, 60);
    const snap = collector.snapshot();
    expect(snap.clicks).toEqual([[50, 60, 100, 180]]);
    expect(snap.points).toEqual([
      [50, 60, 100],
      [51, 60, 180],
    ]);
  });

  it('records a programmatic-style click without a press as zero dwell', () => {
    collector = makeCollector();
    collector.start(window);
    clock = 500;
    fire(window, 'click', 5, 5);
    expect(collector.snapshot().clicks).toEqual([[5, 5, 500, 500]]);
  });

  it('counts untrusted events without storing them, and counts wheel events', () => {
    collector = makeCollector();
    collector.start(window);
    fire(window, 'mousemove', 1, 1, false);
    fire(window, 'click', 1, 1, false);
    fire(window, 'wheel');
    fire(window, 'wheel');
    const snap = collector.snapshot();
    expect(snap.points).toEqual([]);
    expect(snap.clicks).toEqual([]);
    expect(snap.untrusted_count).toBe(2);
    expect(snap.wheel_events).toBe(2);
  });

  it('stays bounded under a long stream and keeps only the recent window', () => {
    collector = makeCollector({ maxMousePoints: 100, windowMs: 1_000 });
    collector.start(window);
    for (let i = 0; i < 5_000; i += 1) {
      clock = i * 20;
      fire(window, 'mousemove', i % 800, i % 600);
    }
    const { points } = collector.snapshot();
    expect(points.length).toBeLessThanOrEqual(51); // 1000 ms window at 20 ms spacing
    expect(points.every((p) => p[2] >= clock - 1_000)).toBe(true);

    collector = makeCollector({ maxMousePoints: 100, windowMs: 60_000 });
    collector.start(document);
    for (let i = 0; i < 5_000; i += 1) {
      clock = 100_000 + i * 20;
      fire(document, 'mousemove', 1, 1);
    }
    expect(collector.snapshot().points.length).toBe(100);
    collector.stop();
  });

  it('stop() removes listeners and clears data; start() is idempotent', () => {
    collector = makeCollector();
    collector.start(window);
    collector.start(window);
    fire(window, 'mousemove', 1, 1);
    expect(collector.snapshot().points.length).toBe(1);
    collector.stop();
    expect(collector.running).toBe(false);
    expect(collector.snapshot().points).toEqual([]);
    clock = 1_000;
    fire(window, 'mousemove', 2, 2);
    expect(collector.snapshot().points).toEqual([]);
    collector.stop();
  });

  it('serialises to the backend MouseBehaviour shape', () => {
    collector = makeCollector();
    collector.start(window);
    fire(window, 'mousemove', 3, 4);
    const json = JSON.parse(JSON.stringify(collector.snapshot()));
    expect(Object.keys(json).sort()).toEqual([
      'clicks',
      'points',
      'untrusted_count',
      'wheel_events',
    ]);
  });
});

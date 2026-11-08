import { afterEach, describe, expect, it } from 'vitest';
import { ScrollCollector } from '../src/collectors/scroll';
import { TimingCollector } from '../src/collectors/timing';

let clock = 0;
const now = (): number => clock;

function dispatch(target: EventTarget, type: string, trusted = true, bubbles = true): void {
  const event = new Event(type, { bubbles });
  Object.defineProperty(event, 'isTrusted', { value: trusted });
  target.dispatchEvent(event);
}

let scrollCollector: ScrollCollector | null = null;
let timingCollector: TimingCollector | null = null;

afterEach(() => {
  timingCollector?.stop();
  scrollCollector?.stop();
  timingCollector = null;
  scrollCollector = null;
  clock = 0;
  document.body.innerHTML = '';
});

describe('ScrollCollector', () => {
  it('counts trusted scroll events including nested elements and ignores untrusted', () => {
    document.body.innerHTML = '<div id="box"></div>';
    const box = document.getElementById('box') as HTMLDivElement;

    scrollCollector = new ScrollCollector();
    scrollCollector.start(window);
    scrollCollector.start(window); // idempotent
    expect(scrollCollector.running).toBe(true);

    dispatch(window, 'scroll', true);
    dispatch(box, 'scroll', true);
    dispatch(window, 'scroll', false); // untrusted ignored

    expect(scrollCollector.scrollEvents).toBe(2);
    expect(scrollCollector.snapshot()).toBe(2);

    scrollCollector.stop();
    expect(scrollCollector.running).toBe(false);
    expect(scrollCollector.snapshot()).toBe(0);

    dispatch(window, 'scroll', true);
    expect(scrollCollector.snapshot()).toBe(0);
  });
});

describe('TimingCollector', () => {
  it('records ms_since_load, ms_to_first_interaction, ms_since_nonce, scroll_events and focus_changes', () => {
    scrollCollector = new ScrollCollector();
    timingCollector = new TimingCollector({ now, scrollCollector });
    timingCollector.start(window);

    clock = 500;
    timingCollector.markNonce();

    // Untrusted interaction must not set ms_to_first_interaction
    clock = 800;
    dispatch(window, 'mousedown', false);
    expect(timingCollector.snapshot().ms_to_first_interaction).toBeUndefined();

    // First trusted interaction at 1320 ms
    clock = 1_320;
    dispatch(window, 'mousedown', true);

    // Later interactions must not overwrite the first interaction timestamp
    clock = 2_000;
    dispatch(window, 'keydown', true);

    // Scroll events and focus/visibility transitions
    dispatch(window, 'scroll', true);
    dispatch(window, 'scroll', true);
    dispatch(window, 'blur', true, false);
    dispatch(window, 'focus', true, false);
    dispatch(document, 'visibilitychange', true);

    clock = 8_450;
    const snap = timingCollector.snapshot();
    expect(snap).toEqual({
      ms_since_load: 8_450,
      ms_to_first_interaction: 1_320,
      ms_since_nonce: 7_950,
      scroll_events: 2,
      focus_changes: 3,
    });
  });

  it('omits optional fields when no interaction or nonce has occurred', () => {
    timingCollector = new TimingCollector({ now });
    timingCollector.start(window);
    clock = 400;
    const snap = timingCollector.snapshot();
    expect(snap).toEqual({
      ms_since_load: 400,
      scroll_events: 0,
      focus_changes: 0,
    });
    expect('ms_to_first_interaction' in snap).toBe(false);
    expect('ms_since_nonce' in snap).toBe(false);
  });

  it('counts focus/blur transitions on child elements and window', () => {
    document.body.innerHTML = '<input id="f" />';
    const input = document.getElementById('f') as HTMLInputElement;
    timingCollector = new TimingCollector({ now });
    timingCollector.start(window);

    dispatch(input, 'focus', true, false);
    dispatch(input, 'blur', true, false);
    expect(timingCollector.snapshot().focus_changes).toBe(2);

    dispatch(window, 'blur', true, false);
    expect(timingCollector.snapshot().focus_changes).toBe(3);
  });

  it('clamps durations to the backend 3,600,000 ms maximum and supports stop()/reset()', () => {
    scrollCollector = new ScrollCollector();
    timingCollector = new TimingCollector({ now, scrollCollector, loadTimeMs: 100 });
    timingCollector.start(window);

    clock = 10_000_000;
    expect(timingCollector.snapshot(250_000)).toEqual({
      ms_since_load: 3_600_000,
      scroll_events: 100_000,
      focus_changes: 0,
    });

    timingCollector.stop();
    expect(timingCollector.running).toBe(false);
    expect(scrollCollector.running).toBe(false);

    clock = 500;
    dispatch(window, 'mousedown', true);
    dispatch(window, 'focus', true, false);
    expect(timingCollector.snapshot().ms_to_first_interaction).toBeUndefined();
    expect(timingCollector.snapshot().focus_changes).toBe(0);
  });
});

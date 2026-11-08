import { afterEach, describe, expect, it } from 'vitest';
import { KeyboardCollector, keyClass } from '../src/collectors/keyboard';

let clock = 0;
const now = (): number => clock;

function makeCollector(
  overrides: Partial<ConstructorParameters<typeof KeyboardCollector>[0]> = {},
) {
  return new KeyboardCollector({ maxKeyEvents: 300, windowMs: 10_000, now, ...overrides });
}

/** Physical `code` for a printable character on a US layout (test helper only). */
function codeFor(ch: string): string {
  if (/[a-z]/i.test(ch)) return `Key${ch.toUpperCase()}`;
  if (/[0-9]/.test(ch)) return `Digit${ch}`;
  if (ch === ' ') return 'Space';
  if (ch === '@') return 'Digit2';
  if (ch === '.') return 'Period';
  return 'Unidentified';
}

function key(
  target: EventTarget,
  type: 'keydown' | 'keyup',
  k: string,
  code: string,
  opts: { trusted?: boolean; repeat?: boolean } = {},
): void {
  const event = new KeyboardEvent(type, {
    key: k,
    code,
    repeat: opts.repeat ?? false,
    bubbles: true,
  });
  Object.defineProperty(event, 'isTrusted', { value: opts.trusted ?? true });
  target.dispatchEvent(event);
}

/** Simulate typing `text` into `el`, also writing it into the field value like a browser would. */
function typeInto(el: HTMLInputElement, text: string, start = 0, dwell = 80, flight = 60): number {
  let t = start;
  for (const ch of text) {
    clock = t;
    key(el, 'keydown', ch, codeFor(ch));
    el.value += ch;
    const input = new InputEvent('input', { inputType: 'insertText', data: ch, bubbles: true });
    el.dispatchEvent(input);
    clock = t + dwell;
    key(el, 'keyup', ch, codeFor(ch));
    t += dwell + flight;
  }
  return t;
}

let collector: KeyboardCollector | null = null;
afterEach(() => {
  collector?.stop();
  collector = null;
  clock = 0;
  document.body.innerHTML = '';
});

describe('keyClass', () => {
  it.each([
    [{ key: 'a', code: 'KeyA' }, 'letter'],
    [{ key: 'Q', code: 'KeyQ' }, 'letter'],
    [{ key: '7', code: 'Digit7' }, 'digit'],
    [{ key: '7', code: 'Numpad7' }, 'digit'],
    [{ key: ' ', code: 'Space' }, 'space'],
    [{ key: ',', code: 'Comma' }, 'punct'],
    [{ key: 'Shift', code: 'ShiftLeft' }, 'modifier'],
    [{ key: 'Control', code: 'ControlRight' }, 'modifier'],
    [{ key: 'Enter', code: 'NumpadEnter' }, 'enter'],
    [{ key: 'Backspace', code: 'Backspace' }, 'backspace'],
    [{ key: 'Tab', code: 'Tab' }, 'other'],
    [{ key: 'ArrowLeft', code: 'ArrowLeft' }, 'other'],
    [{ key: 'é', code: '' }, 'letter'],
    [{ key: '५', code: 'Unidentified' }, 'digit'],
    [{ key: '?', code: '' }, 'punct'],
    [{ key: 'Unidentified', code: '' }, 'other'],
  ])('%o -> %s', (ev, expected) => {
    expect(keyClass(ev)).toBe(expected);
  });
});

describe('KeyboardCollector', () => {
  it('records [key_class, down_ms, up_ms] and ignores auto-repeat', () => {
    collector = makeCollector();
    collector.start(window);
    clock = 100;
    key(window, 'keydown', 'a', 'KeyA');
    clock = 150;
    key(window, 'keydown', 'a', 'KeyA', { repeat: true });
    clock = 180;
    key(window, 'keyup', 'a', 'KeyA');
    clock = 200;
    key(window, 'keydown', ' ', 'Space');
    clock = 260;
    key(window, 'keyup', ' ', 'Space');
    expect(collector.snapshot().events).toEqual([
      ['letter', 100, 180],
      ['space', 200, 260],
    ]);
  });

  it('pairs overlapping presses (rollover) by class without key identity', () => {
    collector = makeCollector();
    collector.start(window);
    clock = 0;
    key(window, 'keydown', 'Shift', 'ShiftLeft');
    clock = 50;
    key(window, 'keydown', 'H', 'KeyH');
    clock = 120;
    key(window, 'keyup', 'H', 'KeyH');
    clock = 140;
    key(window, 'keyup', 'Shift', 'ShiftLeft');
    expect(collector.snapshot().events).toEqual([
      ['letter', 50, 120],
      ['modifier', 0, 140],
    ]);
  });

  it('counts untrusted key events without storing them', () => {
    collector = makeCollector();
    collector.start(window);
    key(window, 'keydown', 'a', 'KeyA', { trusted: false });
    key(window, 'keyup', 'a', 'KeyA', { trusted: false });
    const snap = collector.snapshot();
    expect(snap.events).toEqual([]);
    expect(snap.untrusted_count).toBe(2);
  });

  it('counts paste events and flags autofill-like input without key presses', () => {
    document.body.innerHTML =
      '<input id="f" type="text" /><select id="s"><option>a</option></select>';
    const field = document.getElementById('f') as HTMLInputElement;
    const select = document.getElementById('s') as HTMLSelectElement;
    collector = makeCollector();
    collector.start(window);

    clock = 1_000;
    field.dispatchEvent(new Event('paste', { bubbles: true }));
    field.dispatchEvent(new InputEvent('input', { inputType: 'insertFromPaste', bubbles: true }));
    expect(collector.snapshot()).toMatchObject({ paste_events: 1, autofill_suspected: false });

    clock = 5_000;
    select.dispatchEvent(new Event('input', { bubbles: true }));
    expect(collector.snapshot().autofill_suspected).toBe(false);

    clock = 9_000;
    field.dispatchEvent(new Event('input', { bubbles: true }));
    expect(collector.snapshot().autofill_suspected).toBe(true);
  });

  it('never exposes typed characters or field values in the serialised payload', () => {
    document.body.innerHTML = '<input id="aadhaar" type="text" />';
    const field = document.getElementById('aadhaar') as HTMLInputElement;
    const secret = 'Zq9x secret.user@example 4821';
    collector = makeCollector();
    collector.start(window);
    typeInto(field, secret);
    expect(field.value).toBe(secret);

    const json = JSON.stringify(collector.snapshot());
    expect(json).not.toContain(secret);
    for (const word of secret.split(/[\s@.]/).filter((w) => w.length >= 2)) {
      expect(json).not.toContain(word);
    }
    expect(json).not.toMatch(/Key[A-Z]|Digit\d|"code"|"key"/);
    const parsed = JSON.parse(json) as { events: [string, number, number][] };
    const allowed = [
      'letter',
      'digit',
      'space',
      'punct',
      'modifier',
      'enter',
      'backspace',
      'other',
    ];
    expect(parsed.events.length).toBe([...secret].length);
    expect(parsed.events.every((e) => allowed.includes(e[0]))).toBe(true);
  });

  it('stays bounded and keeps only the recent window', () => {
    document.body.innerHTML = '<input id="f" type="text" />';
    const field = document.getElementById('f') as HTMLInputElement;
    collector = makeCollector({ maxKeyEvents: 50, windowMs: 2_000 });
    collector.start(window);
    const end = typeInto(field, 'a'.repeat(1_000));
    const { events } = collector.snapshot();
    expect(events.length).toBeLessThanOrEqual(50);
    expect(events.every((e) => e[2] >= end - 60 - 2_000)).toBe(true);
  });

  it('stop() removes listeners and clears data; start() is idempotent', () => {
    collector = makeCollector();
    collector.start(window);
    collector.start(window);
    key(window, 'keydown', 'a', 'KeyA');
    clock = 10;
    key(window, 'keyup', 'a', 'KeyA');
    expect(collector.snapshot().events.length).toBe(1);
    collector.stop();
    expect(collector.running).toBe(false);
    key(window, 'keydown', 'b', 'KeyB');
    key(window, 'keyup', 'b', 'KeyB');
    expect(collector.snapshot().events).toEqual([]);
  });
});

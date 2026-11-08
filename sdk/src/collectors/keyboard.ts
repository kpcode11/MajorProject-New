/**
 * Keyboard timing collector (Appendix B.3 `behaviour.keys`, P6-04).
 *
 * Privacy rules (hard, see AGENTS.md):
 * - Only the key **class** is kept: `letter | digit | space | punct | modifier | enter |
 *   backspace | other`. `event.key` / `event.code` are read once inside {@link keyClass} and
 *   never stored, buffered or sent.
 * - Key-down/key-up pairing uses the class only (first-in-first-out per class), so no key
 *   identity is held even transiently.
 * - Input values are never read. Paste and autofill produce counts/flags only.
 *
 * Time is milliseconds from the page time origin (`performance.now()`), rounded to 0.1 ms.
 * Auto-repeat key-downs are ignored. Events with `isTrusted === false` are counted only.
 */
import { RingBuffer } from '../ringbuffer';

/** Key classes accepted by the backend (schemas.py `KEY_CLASSES`). */
export type KeyClass =
  'letter' | 'digit' | 'space' | 'punct' | 'modifier' | 'enter' | 'backspace' | 'other';

/** Keyboard part of the behaviour payload; matches `KeyBehaviour` in backend/app/schemas.py. */
export interface KeyBehaviour {
  events: [KeyClass, number, number][];
  paste_events: number;
  autofill_suspected: boolean;
  untrusted_count: number;
}

/** Collector settings (a subset of the SDK config). */
export interface KeyboardCollectorOptions {
  maxKeyEvents: number;
  windowMs: number;
  /** Clock in milliseconds; defaults to `performance.now()`. */
  now?: () => number;
}

const MODIFIER_KEYS = new Set([
  'Shift',
  'Control',
  'Alt',
  'AltGraph',
  'Meta',
  'OS',
  'CapsLock',
  'Fn',
]);
const PUNCT_CODES = new Set([
  'Minus',
  'Equal',
  'BracketLeft',
  'BracketRight',
  'Backslash',
  'Semicolon',
  'Quote',
  'Backquote',
  'Comma',
  'Period',
  'Slash',
  'IntlBackslash',
  'IntlRo',
  'IntlYen',
  'NumpadAdd',
  'NumpadSubtract',
  'NumpadMultiply',
  'NumpadDivide',
  'NumpadDecimal',
  'NumpadComma',
  'NumpadEqual',
]);

/**
 * Map a keyboard event to its class. The identity is used only inside this function.
 * `code` (physical key) is preferred; `key` is the fallback for virtual keyboards.
 */
export function keyClass(event: Pick<KeyboardEvent, 'key' | 'code'>): KeyClass {
  const code = typeof event.code === 'string' ? event.code : '';
  const key = typeof event.key === 'string' ? event.key : '';
  if (code === 'Backspace' || key === 'Backspace') return 'backspace';
  if (code === 'Enter' || code === 'NumpadEnter' || key === 'Enter') return 'enter';
  if (code === 'Space' || key === ' ') return 'space';
  if (MODIFIER_KEYS.has(key) || /^(Shift|Control|Alt|Meta|OS)(Left|Right)$/.test(code)) {
    return 'modifier';
  }
  if (code === 'CapsLock') return 'modifier';
  if (/^Key[A-Z]$/.test(code)) return 'letter';
  if (/^(Digit|Numpad)[0-9]$/.test(code)) return 'digit';
  if (PUNCT_CODES.has(code)) return 'punct';
  if (code === '' || code === 'Unidentified') {
    if ([...key].length === 1) {
      if (/\p{L}/u.test(key)) return 'letter';
      if (/\p{N}/u.test(key)) return 'digit';
      if (/\s/u.test(key)) return 'space';
      return 'punct';
    }
  }
  return 'other';
}

/** Backend caps (schemas.py). */
const MAX_PASTE = 1_000;
const MAX_PENDING = 16;
/** Key-downs without a key-up after this long are discarded (ms). */
const PENDING_TTL_MS = 5_000;
/** An `input` event within this many ms after a key-down is attributed to typing. */
const TYPING_INPUT_MS = 150;

const EVENTS = ['keydown', 'keyup', 'paste', 'input', 'blur'] as const;

const round1 = (v: number): number => Math.round(v * 10) / 10;

const TEXT_INPUT_TYPES = new Set(['text', 'email', 'tel', 'password', 'search', 'url', 'number']);

/** True for text-entry elements (checks the element kind only, never its value). */
function isTextField(target: EventTarget | null): boolean {
  const el = target as { tagName?: unknown; type?: unknown; isContentEditable?: unknown } | null;
  if (!el || typeof el.tagName !== 'string') return false;
  const tag = el.tagName.toUpperCase();
  if (tag === 'TEXTAREA') return true;
  if (tag === 'INPUT') return TEXT_INPUT_TYPES.has(String(el.type || 'text').toLowerCase());
  return el.isContentEditable === true;
}

export class KeyboardCollector {
  private readonly events: RingBuffer<[KeyClass, number, number]>;
  private readonly now: () => number;
  private target: EventTarget | null = null;
  private pending: { cls: KeyClass; down: number }[] = [];
  private lastKeyDownT = Number.NEGATIVE_INFINITY;
  private lastPasteT = Number.NEGATIVE_INFINITY;
  private paste = 0;
  private autofill = false;
  private untrusted = 0;
  private readonly listener = (event: Event): void => this.handle(event);

  constructor(private readonly options: KeyboardCollectorOptions) {
    this.events = new RingBuffer(options.maxKeyEvents);
    this.now = options.now ?? (() => performance.now());
  }

  /** True while listeners are attached. */
  get running(): boolean {
    return this.target !== null;
  }

  /** Attach passive capture listeners to `target` (default `window`). Idempotent. */
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
    this.events.clear();
    this.pending = [];
    this.lastKeyDownT = Number.NEGATIVE_INFINITY;
    this.lastPasteT = Number.NEGATIVE_INFINITY;
    this.paste = 0;
    this.autofill = false;
    this.untrusted = 0;
  }

  /** Return the bounded payload for the most recent `windowMs`. Does not clear the buffers. */
  snapshot(): KeyBehaviour {
    const cutoff = this.now() - this.options.windowMs;
    return {
      events: this.events.toArray().filter((e) => e[2] >= cutoff),
      paste_events: this.paste,
      autofill_suspected: this.autofill,
      untrusted_count: this.untrusted,
    };
  }

  private handle(event: Event): void {
    const t = round1(Math.max(0, this.now()));
    switch (event.type) {
      case 'keydown':
      case 'keyup': {
        if (event.isTrusted === false) {
          this.untrusted = Math.min(this.options.maxKeyEvents, this.untrusted + 1);
          return;
        }
        const ke = event as KeyboardEvent;
        if (event.type === 'keydown') {
          if (ke.repeat) return;
          this.onDown(keyClass(ke), t);
        } else {
          this.onUp(keyClass(ke), t);
        }
        return;
      }
      case 'paste':
        this.paste = Math.min(MAX_PASTE, this.paste + 1);
        this.lastPasteT = t;
        return;
      case 'input':
        this.onInput(event, t);
        return;
      case 'blur':
        // Focus left the target or window: key-ups may never arrive.
        if (event.target === this.target) this.pending = [];
        return;
    }
  }

  private onDown(cls: KeyClass, t: number): void {
    this.lastKeyDownT = t;
    this.pending = this.pending.filter((p) => t - p.down <= PENDING_TTL_MS);
    if (this.pending.length >= MAX_PENDING) this.pending.shift();
    this.pending.push({ cls, down: t });
  }

  private onUp(cls: KeyClass, t: number): void {
    const i = this.pending.findIndex((p) => p.cls === cls);
    if (i < 0) return;
    const [p] = this.pending.splice(i, 1);
    if (p) this.events.push([cls, p.down, Math.max(t, p.down)]);
  }

  private onInput(event: Event, t: number): void {
    // Only event metadata and the element kind are inspected; the field value is never read.
    if (!isTextField(event.target)) return;
    const inputType = (event as InputEvent).inputType;
    const typed = t - this.lastKeyDownT <= TYPING_INPUT_MS;
    const pasted = t - this.lastPasteT <= TYPING_INPUT_MS || inputType === 'insertFromPaste';
    if (typed || pasted) return;
    if (inputType === undefined || inputType === '' || inputType === 'insertReplacementText') {
      this.autofill = true;
    }
  }
}

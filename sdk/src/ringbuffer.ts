/**
 * Fixed-capacity ring buffer. When full, pushing overwrites the oldest item, so memory use is
 * bounded by `capacity` regardless of how long the page stays open.
 */
export class RingBuffer<T> {
  private readonly items: (T | undefined)[];
  private start = 0;
  private count = 0;

  constructor(readonly capacity: number) {
    if (!Number.isInteger(capacity) || capacity < 1) {
      throw new RangeError(`capacity must be a positive integer, got ${capacity}`);
    }
    this.items = new Array<T | undefined>(capacity);
  }

  /** Number of stored items (≤ capacity). */
  get size(): number {
    return this.count;
  }

  /** Append an item, overwriting the oldest one when the buffer is full. */
  push(item: T): void {
    const end = (this.start + this.count) % this.capacity;
    this.items[end] = item;
    if (this.count < this.capacity) {
      this.count += 1;
    } else {
      this.start = (this.start + 1) % this.capacity;
    }
  }

  /** Items from oldest to newest. */
  toArray(): T[] {
    const out: T[] = [];
    for (let i = 0; i < this.count; i += 1) {
      out.push(this.items[(this.start + i) % this.capacity] as T);
    }
    return out;
  }

  /** Remove every item and release references. */
  clear(): void {
    this.items.fill(undefined);
    this.start = 0;
    this.count = 0;
  }
}

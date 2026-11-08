/**
 * SDK performance controls (P6-10):
 * - Non-blocking aggregation via `requestIdleCallback` (with bounded timeout fallback to `setTimeout`
 *   so aggregation yields to the browser event loop without starving when the tab is busy).
 * - Optional inline Web Worker off-thread payload serialisation/trimming when `Worker` and `Blob`
 *   are available and enabled, with automatic main-thread fallback.
 */

export interface IdleScheduleOptions {
  /** Whether to defer work to an idle slice (default `true`). */
  enabled?: boolean;
  /** Maximum delay in milliseconds before running the task if no idle slice occurs (default `50`). */
  timeoutMs?: number;
  /** Window object providing `requestIdleCallback` (defaults to global `window`). */
  win?: Window;
}

type IdleCallbackFn = (cb: () => void, opts?: { timeout: number }) => unknown;

/**
 * Schedule `compute` inside `requestIdleCallback` when available and `enabled` is true;
 * otherwise resolves synchronously via `Promise.resolve()`.
 */
export function scheduleIdleTask<T>(
  compute: () => T,
  options: IdleScheduleOptions = {},
): Promise<T> {
  const enabled = options.enabled ?? true;
  if (!enabled) {
    return Promise.resolve(compute());
  }
  const w = options.win ?? (typeof window !== 'undefined' ? window : undefined);
  const ric = (w as (Window & { requestIdleCallback?: IdleCallbackFn }) | undefined)
    ?.requestIdleCallback;
  if (typeof ric !== 'function') {
    return Promise.resolve(compute());
  }
  const timeout = options.timeoutMs ?? 50;
  return new Promise<T>((resolve, reject) => {
    let settled = false;
    const run = (): void => {
      if (settled) return;
      settled = true;
      clearTimeout(fallbackTimer);
      try {
        resolve(compute());
      } catch (err) {
        reject(err);
      }
    };
    const fallbackTimer = setTimeout(run, timeout + 10);
    ric(run, { timeout });
  });
}

/**
 * Create a high-frequency throttle predicate returning `true` at most once per `intervalMs`.
 */
export function createThrottleGate(intervalMs: number): {
  allow: (nowMs: number) => boolean;
  reset: () => void;
} {
  let lastAllowed = Number.NEGATIVE_INFINITY;
  return {
    allow(nowMs: number): boolean {
      if (nowMs - lastAllowed < intervalMs) return false;
      lastAllowed = nowMs;
      return true;
    },
    reset(): void {
      lastAllowed = Number.NEGATIVE_INFINITY;
    },
  };
}

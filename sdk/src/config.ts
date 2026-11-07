/**
 * SDK configuration: defaults, hard limits and validation.
 *
 * Hard limits mirror the backend contract (Appendix B.3 and backend/app/schemas.py):
 * at most 600 mouse points, 300 key events, 20 touch gestures of 100 points each,
 * and a 64 KB request body. User overrides may lower these limits but never raise them.
 *
 * Units: all durations are milliseconds.
 */

/** SDK version sent as `sdk_version` in every assess request. */
export const SDK_VERSION = '1.0.0';

/** Payload schema version sent as `schema_version` (backend accepts 1). */
export const SCHEMA_VERSION = 1;

/** Contract limits enforced by the backend. These are upper bounds for any config. */
export const HARD_LIMITS = Object.freeze({
  maxMousePoints: 600,
  maxClicks: 600,
  maxKeyEvents: 300,
  maxGestures: 20,
  maxGesturePoints: 100,
  maxBodyBytes: 64 * 1024,
});

/** Paths of the backend endpoints, relative to `endpoint`. */
export interface EndpointPaths {
  nonce: string;
  assess: string;
  challenge: string;
}

/** Full SDK configuration after defaults have been applied. */
export interface BotGuardConfig {
  /** Base URL of the scoring backend, e.g. `http://127.0.0.1:8000`. Empty means same origin. */
  endpoint: string;
  /** Endpoint paths appended to `endpoint`. */
  paths: EndpointPaths;
  /** Length of the behaviour window kept in memory and sent to the backend (ms). */
  windowMs: number;
  /** Maximum mouse points kept in the ring buffer (≤ 600). */
  maxMousePoints: number;
  /** Maximum click records kept (≤ 600). */
  maxClicks: number;
  /** Maximum key timing events kept (≤ 300). */
  maxKeyEvents: number;
  /** Minimum interval between recorded `mousemove` samples (ms); 16 ms ≈ 60 Hz. */
  mouseThrottleMs: number;
  /** Timeout for each backend request (ms). */
  requestTimeoutMs: number;
  /** Number of retries after the first failed attempt for retryable errors. */
  maxRetries: number;
  /** Base delay for exponential backoff between retries (ms). */
  retryBaseDelayMs: number;
  /** Defer non-urgent aggregation to `requestIdleCallback` when available. */
  useIdleCallback: boolean;
  /** Emit debug messages through `console.debug`. Never logs payload contents. */
  debug: boolean;
}

/** Partial configuration accepted from the host page. */
export type BotGuardOptions = Partial<Omit<BotGuardConfig, 'paths'>> & {
  paths?: Partial<EndpointPaths>;
};

/** Default configuration (Phase 6 plan, P6-01). */
export const DEFAULT_CONFIG: Readonly<BotGuardConfig> = Object.freeze({
  endpoint: '',
  paths: Object.freeze({
    nonce: '/v1/nonce',
    assess: '/v1/assess',
    challenge: '/v1/assess/challenge',
  }),
  windowMs: 10_000,
  maxMousePoints: HARD_LIMITS.maxMousePoints,
  maxClicks: 50,
  maxKeyEvents: HARD_LIMITS.maxKeyEvents,
  mouseThrottleMs: 16,
  requestTimeoutMs: 3_000,
  maxRetries: 2,
  retryBaseDelayMs: 250,
  useIdleCallback: true,
  debug: false,
});

/** Raised when a configuration value is invalid. */
export class BotGuardConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'BotGuardConfigError';
  }
}

function checkInt(name: string, value: number, min: number, max: number): number {
  if (!Number.isFinite(value) || !Number.isInteger(value) || value < min || value > max) {
    throw new BotGuardConfigError(`${name} must be an integer in [${min}, ${max}], got ${value}`);
  }
  return value;
}

function checkPath(name: string, value: string): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.length > 256) {
    throw new BotGuardConfigError(`paths.${name} must be a string starting with '/'`);
  }
  return value;
}

/**
 * Merge host options over the defaults, validate every value, and return a frozen config.
 *
 * Limits above the backend contract are rejected rather than silently clamped so that
 * integration mistakes surface during development.
 */
export function resolveConfig(options: BotGuardOptions = {}): Readonly<BotGuardConfig> {
  const merged: BotGuardConfig = {
    ...DEFAULT_CONFIG,
    ...options,
    paths: { ...DEFAULT_CONFIG.paths, ...(options.paths ?? {}) },
  };

  if (typeof merged.endpoint !== 'string') {
    throw new BotGuardConfigError('endpoint must be a string');
  }
  const endpoint = merged.endpoint.replace(/\/+$/, '');
  if (endpoint !== '' && !/^https?:\/\//i.test(endpoint)) {
    throw new BotGuardConfigError('endpoint must be empty (same origin) or an http(s) URL');
  }

  const config: BotGuardConfig = {
    endpoint,
    paths: Object.freeze({
      nonce: checkPath('nonce', merged.paths.nonce),
      assess: checkPath('assess', merged.paths.assess),
      challenge: checkPath('challenge', merged.paths.challenge),
    }),
    windowMs: checkInt('windowMs', merged.windowMs, 1_000, 60_000),
    maxMousePoints: checkInt(
      'maxMousePoints',
      merged.maxMousePoints,
      1,
      HARD_LIMITS.maxMousePoints,
    ),
    maxClicks: checkInt('maxClicks', merged.maxClicks, 0, HARD_LIMITS.maxClicks),
    maxKeyEvents: checkInt('maxKeyEvents', merged.maxKeyEvents, 1, HARD_LIMITS.maxKeyEvents),
    mouseThrottleMs: checkInt('mouseThrottleMs', merged.mouseThrottleMs, 0, 1_000),
    requestTimeoutMs: checkInt('requestTimeoutMs', merged.requestTimeoutMs, 100, 60_000),
    maxRetries: checkInt('maxRetries', merged.maxRetries, 0, 5),
    retryBaseDelayMs: checkInt('retryBaseDelayMs', merged.retryBaseDelayMs, 0, 10_000),
    useIdleCallback: Boolean(merged.useIdleCallback),
    debug: Boolean(merged.debug),
  };
  return Object.freeze(config);
}

/** Build an absolute or same-origin URL for one of the configured endpoints. */
export function endpointUrl(config: Readonly<BotGuardConfig>, key: keyof EndpointPaths): string {
  return `${config.endpoint}${config.paths[key]}`;
}

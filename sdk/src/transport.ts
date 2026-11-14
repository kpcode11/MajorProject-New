/**
 * SDK transport layer (Appendix B.1 / B.3 / B.4, P6-06).
 *
 * Responsibilities:
 * - Fetch single-use nonces from `GET /v1/nonce` (`fetchNonce`).
 * - Build bounded, schema-valid payloads for `POST /v1/assess` (`buildAssessPayload`) and
 *   `POST /v1/assess/challenge` (`buildChallengePayload`), trimming points/events if needed so the
 *   serialised JSON body stays under the 64 KB backend cap (`HARD_LIMITS.maxBodyBytes`).
 * - Send requests with per-attempt timeouts (`AbortController` + `requestTimeoutMs`) and
 *   exponential backoff retries (`maxRetries`, `retryBaseDelayMs`) on transient errors (network
 *   failures, timeouts, HTTP 429 and 5xx).
 * - Never block the host page: `safeAssess` and `safeSubmitChallenge` catch transport failures and
 *   return a degraded client-side fallback response (`degraded: true`) so host forms can decide how
 *   to proceed without uncaught promise rejections.
 */
import type { EnvSignals } from './collectors/env';
import type { KeyBehaviour } from './collectors/keyboard';
import type { MouseBehaviour } from './collectors/mouse';
import type { TimingSignals } from './collectors/timing';
import {
  type BotGuardConfig,
  HARD_LIMITS,
  SCHEMA_VERSION,
  SDK_VERSION,
  endpointUrl,
} from './config';

/** Touch gesture point `[x, y, t_ms, pressure?, size?]` (Appendix B.3, Phase 8). */
export type TouchPointTuple =
  | [number, number, number]
  | [number, number, number, number | null]
  | [number, number, number, number | null, number | null];

/** Single touch gesture (Appendix B.3). */
export interface TouchGesture {
  type: 'tap' | 'swipe' | 'drag' | 'other';
  points: TouchPointTuple[];
}

/** Touch behaviour payload (Appendix B.3). */
export interface TouchBehaviour {
  gestures: TouchGesture[];
}

/** Device class values accepted by `BehaviourPayload` (`backend/app/schemas.py`). */
export type DeviceClass = 'desktop' | 'mobile' | 'tablet' | 'unknown';

/** Combined behaviour payload (`backend/app/schemas.py` `BehaviourPayload`). */
export interface BehaviourPayload {
  mouse?: MouseBehaviour;
  keys?: KeyBehaviour;
  touch?: TouchBehaviour;
  timing?: TimingSignals;
  device_class?: DeviceClass;
}

/** Request body for `POST /v1/assess` (`backend/app/schemas.py` `AssessRequest`). */
export interface AssessRequestPayload {
  nonce: string;
  action: string;
  sdk_version: string;
  schema_version: number;
  client_ts: number;
  env?: EnvSignals;
  behaviour?: BehaviourPayload;
}

/** Request body for `POST /v1/assess/challenge` (`ChallengeAssessRequest`). */
export interface ChallengeAssessRequestPayload {
  nonce: string;
  challenge_id: string;
  action: string;
  sdk_version: string;
  hold_start_ms?: number;
  hold_end_ms?: number;
  env?: EnvSignals;
  behaviour?: BehaviourPayload;
}

/** Response from `GET /v1/nonce` (`NonceResponse`). */
export interface NonceResponse {
  nonce: string;
  expires_in: number;
}

/** Challenge parameters inside `AssessResponse` (`ChallengeInfo`). */
export interface ChallengeInfo {
  id: string;
  type: 'press_hold';
  hold_ms: number;
  expires_in: number;
}

/** Loaded model version strings in `AssessResponse` (`ModelVersions`). */
export interface ModelVersions {
  mouse?: string | null;
  keyboard?: string | null;
  touch?: string | null;
  fusion?: string | null;
}

/** Response from `POST /v1/assess` or `POST /v1/assess/challenge` (`AssessResponse`). */
export interface AssessResponse {
  decision: 'allow' | 'challenge' | 'deny';
  band: 'low' | 'medium' | 'high';
  token: string | null;
  challenge: ChallengeInfo | null;
  request_id: string;
  model_versions: ModelVersions;
  degraded: boolean;
}

/** Structured error returned by the backend on 4xx/5xx (`ErrorResponse`). */
export interface BackendErrorDetail {
  code: string;
  message: string;
  request_id?: string | null;
}

/** Error raised by transport calls when all retries are exhausted or a non-retryable 4xx occurs. */
export class BotGuardTransportError extends Error {
  readonly status?: number;
  readonly code: string;
  readonly requestId?: string | null;
  readonly retryable: boolean;

  constructor(
    message: string,
    options: {
      status?: number;
      code?: string;
      requestId?: string | null;
      retryable?: boolean;
    } = {},
  ) {
    super(message);
    this.name = 'BotGuardTransportError';
    this.status = options.status;
    this.code = options.code ?? 'transport_error';
    this.requestId = options.requestId;
    this.retryable = options.retryable ?? false;
  }
}

/** Optional overrides for testable transport calls. */
export interface TransportDeps {
  fetchImpl?: typeof fetch;
  sleep?: (ms: number) => Promise<void>;
  nowEpochMs?: () => number;
  sessionId?: string;
}

/** Input passed to {@link buildAssessPayload}. */
export interface BuildAssessPayloadInput {
  nonce: string;
  action: string;
  env?: EnvSignals;
  behaviour?: BehaviourPayload;
  clientTs?: number;
  sdkVersion?: string;
  schemaVersion?: number;
}

/** Input passed to {@link buildChallengePayload}. */
export interface BuildChallengePayloadInput {
  nonce: string;
  challengeId: string;
  action: string;
  holdStartMs?: number;
  holdEndMs?: number;
  env?: EnvSignals;
  behaviour?: BehaviourPayload;
  sdkVersion?: string;
}

const UTF8_ENCODER = typeof TextEncoder !== 'undefined' ? new TextEncoder() : null;

/** Measure the UTF-8 byte length of a string. */
export function utf8ByteLength(text: string): number {
  if (UTF8_ENCODER) return UTF8_ENCODER.encode(text).byteLength;
  return text.length;
}

function cloneBehaviour(b: BehaviourPayload | undefined): BehaviourPayload | undefined {
  if (!b) return undefined;
  const copy: BehaviourPayload = { ...b };
  if (b.mouse) {
    copy.mouse = {
      ...b.mouse,
      points: b.mouse.points.slice(-HARD_LIMITS.maxMousePoints),
      clicks: b.mouse.clicks.slice(-HARD_LIMITS.maxClicks),
    };
  }
  if (b.keys) {
    copy.keys = {
      ...b.keys,
      events: b.keys.events.slice(-HARD_LIMITS.maxKeyEvents),
    };
  }
  if (b.touch) {
    copy.touch = {
      gestures: b.touch.gestures.slice(-HARD_LIMITS.maxGestures).map((g) => ({
        type: g.type,
        points: g.points.slice(-HARD_LIMITS.maxGesturePoints),
      })),
    };
  }
  return copy;
}

/** Halve the oldest buffered traces in-place until the JSON fits within `maxBodyBytes`. */
function trimToBodyLimit<T extends { behaviour?: BehaviourPayload }>(payload: T): T {
  for (let step = 0; step < 8; step += 1) {
    if (utf8ByteLength(JSON.stringify(payload)) <= HARD_LIMITS.maxBodyBytes) {
      return payload;
    }
    const beh = payload.behaviour;
    if (!beh) break;
    let trimmed = false;
    if (beh.mouse && beh.mouse.points.length > 0) {
      beh.mouse.points = beh.mouse.points.slice(Math.ceil(beh.mouse.points.length / 2));
      trimmed = true;
    }
    if (beh.mouse && beh.mouse.clicks.length > 0) {
      beh.mouse.clicks = beh.mouse.clicks.slice(Math.ceil(beh.mouse.clicks.length / 2));
      trimmed = true;
    }
    if (beh.keys && beh.keys.events.length > 0) {
      beh.keys.events = beh.keys.events.slice(Math.ceil(beh.keys.events.length / 2));
      trimmed = true;
    }
    if (beh.touch && beh.touch.gestures.length > 0) {
      beh.touch.gestures = beh.touch.gestures.slice(Math.ceil(beh.touch.gestures.length / 2));
      trimmed = true;
    }
    if (!trimmed) break;
  }
  return payload;
}

/**
 * Build a schema-valid `POST /v1/assess` payload and ensure its serialised size is ≤ 64 KB.
 */
export function buildAssessPayload(
  input: BuildAssessPayloadInput,
  nowEpochMs: () => number = () => Date.now(),
): AssessRequestPayload {
  const payload: AssessRequestPayload = {
    nonce: input.nonce,
    action: input.action,
    sdk_version: input.sdkVersion ?? SDK_VERSION,
    schema_version: input.schemaVersion ?? SCHEMA_VERSION,
    client_ts: input.clientTs ?? Math.max(0, Math.round(nowEpochMs())),
  };
  if (input.env !== undefined) {
    payload.env = { ...input.env };
  }
  const beh = cloneBehaviour(input.behaviour);
  if (beh !== undefined) {
    payload.behaviour = beh;
  }
  return trimToBodyLimit(payload);
}

/**
 * Build a schema-valid `POST /v1/assess/challenge` payload within the 64 KB body limit.
 */
export function buildChallengePayload(
  input: BuildChallengePayloadInput,
): ChallengeAssessRequestPayload {
  const payload: ChallengeAssessRequestPayload = {
    nonce: input.nonce,
    challenge_id: input.challengeId,
    action: input.action,
    sdk_version: input.sdkVersion ?? SDK_VERSION,
  };
  if (input.holdStartMs !== undefined) {
    payload.hold_start_ms = Math.max(0, input.holdStartMs);
  }
  if (input.holdEndMs !== undefined) {
    payload.hold_end_ms = Math.max(0, input.holdEndMs);
  }
  if (input.env !== undefined) {
    payload.env = { ...input.env };
  }
  const beh = cloneBehaviour(input.behaviour);
  if (beh !== undefined) {
    payload.behaviour = beh;
  }
  return trimToBodyLimit(payload);
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function isRetryableStatus(status: number): boolean {
  return status === 408 || status === 429 || (status >= 500 && status <= 599);
}

async function parseErrorDetail(response: Response): Promise<BackendErrorDetail | null> {
  try {
    const data = (await response.json()) as { error?: BackendErrorDetail };
    if (data && typeof data === 'object' && data.error && typeof data.error.code === 'string') {
      return {
        code: data.error.code,
        message: typeof data.error.message === 'string' ? data.error.message : response.statusText,
        request_id: data.error.request_id ?? null,
      };
    }
  } catch {
    /* ignore non-JSON body */
  }
  return null;
}

async function requestJson<T>(
  url: string,
  init: RequestInit,
  config: Readonly<BotGuardConfig>,
  deps: TransportDeps = {},
): Promise<T> {
  const fetchFn = deps.fetchImpl ?? fetch;
  const sleep = deps.sleep ?? defaultSleep;
  const maxAttempts = Math.max(1, config.maxRetries + 1);
  let lastError: BotGuardTransportError | null = null;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (attempt > 0 && config.retryBaseDelayMs > 0) {
      const delay = config.retryBaseDelayMs * 2 ** (attempt - 1);
      await sleep(delay);
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), config.requestTimeoutMs);
    try {
      const response = await fetchFn(url, {
        ...init,
        signal: controller.signal,
        headers: {
          Accept: 'application/json',
          ...(init.body ? { 'Content-Type': 'application/json' } : {}),
          ...(deps.sessionId ? { 'X-Session-Id': deps.sessionId } : {}),
          ...(init.headers ?? {}),
        },
      });

      if (response.ok) {
        return (await response.json()) as T;
      }

      const detail = await parseErrorDetail(response);
      const retryable = isRetryableStatus(response.status);
      lastError = new BotGuardTransportError(detail?.message ?? `HTTP ${response.status}`, {
        status: response.status,
        code: detail?.code ?? `http_${response.status}`,
        requestId: detail?.request_id ?? null,
        retryable,
      });
      if (!retryable) {
        throw lastError;
      }
    } catch (err) {
      if (err instanceof BotGuardTransportError) {
        lastError = err;
        if (!err.retryable) throw err;
      } else {
        const isAbort =
          err instanceof Error && (err.name === 'AbortError' || /abort/i.test(err.message));
        lastError = new BotGuardTransportError(
          isAbort
            ? `Request timed out after ${config.requestTimeoutMs} ms`
            : 'Network request failed',
          {
            code: isAbort ? 'timeout' : 'network_error',
            retryable: true,
          },
        );
      }
    } finally {
      clearTimeout(timer);
    }
  }

  throw (
    lastError ??
    new BotGuardTransportError('Transport request failed', {
      code: 'transport_error',
      retryable: false,
    })
  );
}

/** Fetch a single-use nonce from `GET /v1/nonce`. */
export async function fetchNonce(
  config: Readonly<BotGuardConfig>,
  deps: TransportDeps = {},
): Promise<NonceResponse> {
  return requestJson<NonceResponse>(endpointUrl(config, 'nonce'), { method: 'GET' }, config, deps);
}

/** Submit an assessment payload to `POST /v1/assess`. */
export async function postAssess(
  config: Readonly<BotGuardConfig>,
  payload: AssessRequestPayload,
  deps: TransportDeps = {},
): Promise<AssessResponse> {
  return requestJson<AssessResponse>(
    endpointUrl(config, 'assess'),
    { method: 'POST', body: JSON.stringify(payload) },
    config,
    deps,
  );
}

/** Submit a step-up challenge payload to `POST /v1/assess/challenge`. */
export async function postChallenge(
  config: Readonly<BotGuardConfig>,
  payload: ChallengeAssessRequestPayload,
  deps: TransportDeps = {},
): Promise<AssessResponse> {
  return requestJson<AssessResponse>(
    endpointUrl(config, 'challenge'),
    { method: 'POST', body: JSON.stringify(payload) },
    config,
    deps,
  );
}

/** Build a non-throwing degraded fallback response when the backend cannot be reached. */
export function degradedFallbackResponse(reasonCode = 'transport_unavailable'): AssessResponse {
  return {
    decision: 'deny',
    band: 'high',
    token: null,
    challenge: null,
    request_id: `client-degraded-${reasonCode}`,
    model_versions: {},
    degraded: true,
  };
}

/**
 * Non-throwing wrapper around `fetchNonce` + `buildAssessPayload` + `postAssess`.
 * Never rejects: on any transport failure, logs in debug mode and returns a degraded response.
 */
export async function safeAssess(
  config: Readonly<BotGuardConfig>,
  input: Omit<BuildAssessPayloadInput, 'nonce'> & {
    nonce?: string;
    onNonceIssued?: () => void;
  },
  deps: TransportDeps = {},
): Promise<AssessResponse> {
  try {
    let nonce = input.nonce;
    if (!nonce) {
      const nonceRes = await fetchNonce(config, deps);
      nonce = nonceRes.nonce;
      input.onNonceIssued?.();
    }
    const payload = buildAssessPayload(
      {
        nonce,
        action: input.action,
        env: input.env,
        behaviour: input.behaviour,
        clientTs: input.clientTs,
        sdkVersion: input.sdkVersion,
        schemaVersion: input.schemaVersion,
      },
      deps.nowEpochMs,
    );
    return await postAssess(config, payload, deps);
  } catch (err) {
    if (config.debug && typeof console !== 'undefined') {
      console.debug('[BotGuard] assess failed, returning degraded fallback', err);
    }
    const code = err instanceof BotGuardTransportError ? err.code : 'transport_error';
    return degradedFallbackResponse(code);
  }
}

/**
 * Non-throwing wrapper around `fetchNonce` (when needed) + `buildChallengePayload` +
 * `postChallenge`. Never rejects.
 */
export async function safeSubmitChallenge(
  config: Readonly<BotGuardConfig>,
  input: Omit<BuildChallengePayloadInput, 'nonce'> & {
    nonce?: string;
  },
  deps: TransportDeps = {},
): Promise<AssessResponse> {
  try {
    const nonce = input.nonce ?? (await fetchNonce(config, deps)).nonce;
    const payload = buildChallengePayload({ ...input, nonce });
    return await postChallenge(config, payload, deps);
  } catch (err) {
    if (config.debug && typeof console !== 'undefined') {
      console.debug('[BotGuard] challenge submit failed, returning degraded fallback', err);
    }
    const code = err instanceof BotGuardTransportError ? err.code : 'transport_error';
    return degradedFallbackResponse(code);
  }
}

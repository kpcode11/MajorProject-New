/**
 * BotGuard browser SDK entry point and public API (P6-07).
 *
 * Exposes both an instantiable {@link BotGuardClient} class and the singleton {@link BotGuard}
 * facade (`BotGuard.start()`, `BotGuard.assess(action)`, `BotGuard.runChallenge(...)`,
 * `BotGuard.stop()`).
 *
 * Guarantees:
 * - `start()` and `stop()` are idempotent and safe to call multiple times.
 * - `assess(action)` and `runChallenge(...)` never throw or block the host page; when the backend
 *   cannot be reached, a degraded response (`degraded: true`) is returned.
 * - When `useIdleCallback` is enabled and `requestIdleCallback` is available, snapshot assembly yields
 *   to an idle callback (with a 50 ms timeout) so UI frames are not delayed.
 */
import {
  BotGuardChallengeCancelledError,
  type ChallengeHandler,
  type ChallengeInteractionResult,
  type ChallengeRenderContext,
  type ChallengeRenderer,
  type ChallengeUIOptions,
  createChallengeHandler,
  defaultPressHoldRenderer,
  renderPressHoldChallenge,
} from './challenge';
import { type CollectEnvOptions, type EnvSignals, collectEnv, deviceClass } from './collectors/env';
import {
  type KeyBehaviour,
  type KeyClass,
  KeyboardCollector,
  type KeyboardCollectorOptions,
  keyClass,
} from './collectors/keyboard';
import {
  type MouseBehaviour,
  MouseCollector,
  type MouseCollectorOptions,
} from './collectors/mouse';
import { ScrollCollector } from './collectors/scroll';
import {
  TimingCollector,
  type TimingCollectorOptions,
  type TimingSignals,
} from './collectors/timing';
import {
  type BotGuardConfig,
  BotGuardConfigError,
  type BotGuardOptions,
  DEFAULT_CONFIG,
  type EndpointPaths,
  HARD_LIMITS,
  SCHEMA_VERSION,
  SDK_VERSION,
  endpointUrl,
  resolveConfig,
} from './config';
import { RingBuffer } from './ringbuffer';
import {
  type AssessRequestPayload,
  type AssessResponse,
  type BackendErrorDetail,
  type BehaviourPayload,
  BotGuardTransportError,
  type BuildAssessPayloadInput,
  type BuildChallengePayloadInput,
  type ChallengeAssessRequestPayload,
  type ChallengeInfo,
  type DeviceClass,
  type ModelVersions,
  type NonceResponse,
  type TouchBehaviour,
  type TouchGesture,
  type TouchPointTuple,
  type TransportDeps,
  buildAssessPayload,
  buildChallengePayload,
  degradedFallbackResponse,
  fetchNonce,
  postAssess,
  postChallenge,
  safeAssess,
  safeSubmitChallenge,
  utf8ByteLength,
} from './transport';

export {
  BotGuardChallengeCancelledError,
  BotGuardConfigError,
  BotGuardTransportError,
  DEFAULT_CONFIG,
  HARD_LIMITS,
  KeyboardCollector,
  MouseCollector,
  RingBuffer,
  SCHEMA_VERSION,
  SDK_VERSION,
  ScrollCollector,
  TimingCollector,
  buildAssessPayload,
  buildChallengePayload,
  collectEnv,
  createChallengeHandler,
  defaultPressHoldRenderer,
  degradedFallbackResponse,
  deviceClass,
  endpointUrl,
  fetchNonce,
  keyClass,
  postAssess,
  postChallenge,
  renderPressHoldChallenge,
  resolveConfig,
  safeAssess,
  safeSubmitChallenge,
  utf8ByteLength,
};
export type {
  AssessRequestPayload,
  AssessResponse,
  BackendErrorDetail,
  BehaviourPayload,
  BotGuardConfig,
  BotGuardOptions,
  BuildAssessPayloadInput,
  BuildChallengePayloadInput,
  ChallengeAssessRequestPayload,
  ChallengeHandler,
  ChallengeInfo,
  ChallengeInteractionResult,
  ChallengeRenderContext,
  ChallengeRenderer,
  ChallengeUIOptions,
  CollectEnvOptions,
  DeviceClass,
  EndpointPaths,
  EnvSignals,
  KeyBehaviour,
  KeyClass,
  KeyboardCollectorOptions,
  ModelVersions,
  MouseBehaviour,
  MouseCollectorOptions,
  NonceResponse,
  TimingCollectorOptions,
  TimingSignals,
  TouchBehaviour,
  TouchGesture,
  TouchPointTuple,
  TransportDeps,
};

/** Options accepted by `BotGuard.start()` and `new BotGuardClient()`. */
export interface BotGuardStartOptions extends BotGuardOptions {
  /** Event target for listeners (defaults to `window`). */
  target?: EventTarget;
  /** Window used for `collectEnv` (defaults to `window`). */
  envWindow?: Window;
  /** Options forwarded to `collectEnv`. */
  envOptions?: CollectEnvOptions;
  /** Clock in milliseconds for collectors; defaults to `performance.now()`. */
  now?: () => number;
  /** Custom transport dependencies (fetch, sleep, epoch clock). */
  transportDeps?: TransportDeps;
  /** Optional custom challenge UI handler (P6-08). */
  challengeHandler?: ChallengeHandler;
  /** Pre-fetch a nonce on `start()` so `ms_since_nonce` reflects user dwell time. Default `false`. */
  prefetchNonce?: boolean;
}

/** Options accepted by `runChallenge`. */
export interface RunChallengeOptions {
  /** Override hold start timestamp (ms) when the caller ran the UI directly. */
  holdStartMs?: number;
  /** Override hold end timestamp (ms) when the caller ran the UI directly. */
  holdEndMs?: number;
  /** Optional pre-fetched single-use nonce for the challenge submission. */
  nonce?: string;
  /** Optional challenge UI handler for this call. */
  handler?: ChallengeHandler;
}

type IdleCallbackFn = (cb: () => void, opts?: { timeout: number }) => unknown;

function runInIdle<T>(enabled: boolean, compute: () => T): Promise<T> {
  if (!enabled || typeof window === 'undefined') {
    return Promise.resolve(compute());
  }
  const ric = (window as Window & { requestIdleCallback?: IdleCallbackFn }).requestIdleCallback;
  if (typeof ric !== 'function') {
    return Promise.resolve(compute());
  }
  return new Promise<T>((resolve) => {
    ric(
      () => {
        resolve(compute());
      },
      { timeout: 50 },
    );
  });
}

/**
 * Stateful SDK client managing collectors, cached nonce, and backend assessment calls.
 */
export class BotGuardClient {
  private config: Readonly<BotGuardConfig> = DEFAULT_CONFIG;
  private mouse: MouseCollector | null = null;
  private keyboard: KeyboardCollector | null = null;
  private scroll: ScrollCollector | null = null;
  private timing: TimingCollector | null = null;
  private isRunning = false;
  private cachedNonce: string | null = null;
  private envWindow: Window | undefined;
  private envOptions: CollectEnvOptions | undefined;
  private transportDeps: TransportDeps = {};
  private challengeHandler: ChallengeHandler | undefined;
  private nowFn: () => number = () => performance.now();

  constructor(options?: BotGuardStartOptions) {
    if (options) {
      this.applyOptions(options);
    }
  }

  /** True when collectors are actively listening. */
  get running(): boolean {
    return this.isRunning;
  }

  /** Current resolved configuration. */
  get currentConfig(): Readonly<BotGuardConfig> {
    return this.config;
  }

  /** Register or replace the step-up challenge UI handler (P6-08). */
  setChallengeHandler(handler: ChallengeHandler | undefined): void {
    this.challengeHandler = handler;
  }

  /**
   * Start passive signal collection. Idempotent: calling `start()` while already running with no
   * new options is a no-op; calling with new options updates the config cleanly.
   */
  start(options?: BotGuardStartOptions): this {
    if (this.isRunning && !options) {
      return this;
    }
    if (this.isRunning && options) {
      this.stop();
    }
    if (options) {
      this.applyOptions(options);
    }

    const target = options?.target ?? (typeof window !== 'undefined' ? window : undefined);

    this.mouse = new MouseCollector({
      maxMousePoints: this.config.maxMousePoints,
      maxClicks: this.config.maxClicks,
      mouseThrottleMs: this.config.mouseThrottleMs,
      windowMs: this.config.windowMs,
      now: this.nowFn,
    });
    this.keyboard = new KeyboardCollector({
      maxKeyEvents: this.config.maxKeyEvents,
      windowMs: this.config.windowMs,
      now: this.nowFn,
    });
    this.scroll = new ScrollCollector();
    this.timing = new TimingCollector({
      now: this.nowFn,
      scrollCollector: this.scroll,
    });

    if (target) {
      this.mouse.start(target);
      this.keyboard.start(target);
      this.timing.start(target);
    }
    this.isRunning = true;

    if (options?.prefetchNonce) {
      void this.prefetchNonce();
    }
    return this;
  }

  /**
   * Stop all collectors, remove every event listener, and clear buffered signals.
   * Safe and idempotent to call multiple times.
   */
  stop(): void {
    this.mouse?.stop();
    this.keyboard?.stop();
    this.timing?.stop();
    this.scroll?.stop();
    this.mouse = null;
    this.keyboard = null;
    this.timing = null;
    this.scroll = null;
    this.cachedNonce = null;
    this.isRunning = false;
  }

  /** Collect the current environment and behaviour snapshot without sending a network request. */
  collectSnapshot(): { env: EnvSignals; behaviour: BehaviourPayload } {
    const win = this.envWindow ?? (typeof window !== 'undefined' ? window : undefined);
    const env = win ? collectEnv(win, this.envOptions) : {};
    const behaviour: BehaviourPayload = {
      device_class: deviceClass(env),
    };
    if (this.mouse) {
      behaviour.mouse = this.mouse.snapshot();
    }
    if (this.keyboard) {
      behaviour.keys = this.keyboard.snapshot();
    }
    if (this.timing) {
      behaviour.timing = this.timing.snapshot();
    }
    return { env, behaviour };
  }

  /** Pre-fetch and cache a single-use nonce, marking the nonce timestamp on the timing collector. */
  async prefetchNonce(): Promise<string | null> {
    try {
      const res = await fetchNonce(this.config, this.transportDeps);
      this.cachedNonce = res.nonce;
      this.timing?.markNonce(this.nowFn());
      return res.nonce;
    } catch {
      return null;
    }
  }

  /**
   * Assess the current session for `action` (e.g. `'login'`, `'otp_request'`).
   * Automatically starts collectors if `start()` was not called yet. Never throws.
   */
  async assess(action: string): Promise<AssessResponse> {
    if (!this.isRunning) {
      this.start();
    }
    let nonce = this.cachedNonce ?? undefined;
    this.cachedNonce = null;

    if (!nonce) {
      try {
        const nonceRes = await fetchNonce(this.config, this.transportDeps);
        nonce = nonceRes.nonce;
        this.timing?.markNonce(this.nowFn());
      } catch (err) {
        const code = err instanceof BotGuardTransportError ? err.code : 'transport_error';
        return degradedFallbackResponse(code);
      }
    }

    const { env, behaviour } = await runInIdle(this.config.useIdleCallback, () =>
      this.collectSnapshot(),
    );

    return safeAssess(
      this.config,
      {
        nonce,
        action,
        env,
        behaviour,
      },
      this.transportDeps,
    );
  }

  /**
   * Execute and submit a step-up challenge (`POST /v1/assess/challenge`).
   *
   * Uses explicit `holdStartMs`/`holdEndMs` in `options` if provided, otherwise invokes the
   * configured `challengeHandler` (from `options.handler` or `start({ challengeHandler })`).
   * Never throws.
   */
  async runChallenge(
    challenge: ChallengeInfo,
    action: string,
    options: RunChallengeOptions = {},
  ): Promise<AssessResponse> {
    let holdStartMs = options.holdStartMs;
    let holdEndMs = options.holdEndMs;

    if (holdStartMs === undefined || holdEndMs === undefined) {
      const handler =
        options.handler ?? this.challengeHandler ?? createChallengeHandler({ now: this.nowFn });
      try {
        const interaction = await handler(challenge, action);
        holdStartMs = interaction.holdStartMs;
        holdEndMs = interaction.holdEndMs;
      } catch {
        return degradedFallbackResponse('challenge_cancelled');
      }
    }

    const { env, behaviour } = await runInIdle(this.config.useIdleCallback, () =>
      this.collectSnapshot(),
    );

    return safeSubmitChallenge(
      this.config,
      {
        nonce: options.nonce,
        challengeId: challenge.id,
        action,
        holdStartMs,
        holdEndMs,
        env,
        behaviour,
      },
      this.transportDeps,
    );
  }

  private applyOptions(options: BotGuardStartOptions): void {
    const {
      target: _target,
      envWindow,
      envOptions,
      now,
      transportDeps,
      challengeHandler,
      prefetchNonce: _prefetch,
      ...configOpts
    } = options;
    void _target;
    void _prefetch;
    this.config = resolveConfig(configOpts);
    if (envWindow !== undefined) this.envWindow = envWindow;
    if (envOptions !== undefined) this.envOptions = envOptions;
    if (now !== undefined) this.nowFn = now;
    if (transportDeps !== undefined) this.transportDeps = transportDeps;
    if (challengeHandler !== undefined || 'challengeHandler' in options) {
      this.challengeHandler = challengeHandler;
    }
  }
}

const defaultClient = new BotGuardClient();

/**
 * Default singleton SDK facade (`BotGuard.start()`, `BotGuard.assess(action)`,
 * `BotGuard.runChallenge(...)`, `BotGuard.stop()`).
 */
export const BotGuard = Object.freeze({
  start(options?: BotGuardStartOptions): BotGuardClient {
    return defaultClient.start(options);
  },
  assess(action: string): Promise<AssessResponse> {
    return defaultClient.assess(action);
  },
  runChallenge(
    challenge: ChallengeInfo,
    action: string,
    options?: RunChallengeOptions,
  ): Promise<AssessResponse> {
    return defaultClient.runChallenge(challenge, action, options);
  },
  stop(): void {
    defaultClient.stop();
  },
  setChallengeHandler(handler: ChallengeHandler | undefined): void {
    defaultClient.setChallengeHandler(handler);
  },
  get running(): boolean {
    return defaultClient.running;
  },
  get config(): Readonly<BotGuardConfig> {
    return defaultClient.currentConfig;
  },
});

export default BotGuard;

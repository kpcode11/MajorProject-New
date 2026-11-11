/**
 * React wrapper for the BotGuard browser SDK (`@botguard/sdk/react`, P6-09).
 *
 * Provides {@link BotGuardProvider} and the {@link useBotGuard} hook for React portals and forms.
 * Manages the `BotGuardClient` lifecycle (`start()` on mount, `stop()` on unmount) and exposes
 * helpers for passive assessment, automatic step-up challenge execution, and state tracking.
 */
import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  type AssessResponse,
  BotGuardClient,
  type BotGuardStartOptions,
  type ChallengeInfo,
  type RunChallengeOptions,
} from '../index';

/** Value exposed by {@link useBotGuard}. */
export interface BotGuardContextValue {
  /** Underlying SDK client instance. */
  client: BotGuardClient;
  /** True while the SDK collectors are actively listening. */
  running: boolean;
  /** True while an `assess` or `runChallenge` call is in flight. */
  assessing: boolean;
  /** Most recent assessment response (or `null` before the first call). */
  lastResponse: AssessResponse | null;
  /** Run a passive assessment for `action` (`POST /v1/assess`). */
  assess: (action: string) => Promise<AssessResponse>;
  /** Run a step-up challenge for `challenge` (`POST /v1/assess/challenge`). */
  runChallenge: (
    challenge: ChallengeInfo,
    action: string,
    options?: RunChallengeOptions,
  ) => Promise<AssessResponse>;
  /**
   * Assess `action` and, if the backend returns `decision === 'challenge'`, automatically invoke
   * `runChallenge` and return the final assessment response.
   */
  assessWithStepUp: (
    action: string,
    challengeOptions?: RunChallengeOptions,
  ) => Promise<AssessResponse>;
}

const BotGuardContext = createContext<BotGuardContextValue | null>(null);

/** Props for {@link BotGuardProvider}. */
export interface BotGuardProviderProps {
  /** Optional SDK start options; ignored when an explicit `client` instance is passed. */
  options?: BotGuardStartOptions;
  /** Optional pre-constructed `BotGuardClient` instance (useful for tests or shared instances). */
  client?: BotGuardClient;
  /** Automatically call `client.start()` on mount and `client.stop()` on unmount (default `true`). */
  autoStart?: boolean;
  children?: ReactNode;
}

/**
 * React context provider that starts passive signal collection on mount and cleans up on unmount.
 */
export function BotGuardProvider({
  options,
  client: externalClient,
  autoStart = true,
  children,
}: BotGuardProviderProps): ReactNode {
  const clientRef = useRef<BotGuardClient | null>(null);
  if (!clientRef.current) {
    clientRef.current = externalClient ?? new BotGuardClient(options);
  }
  const activeClient = externalClient ?? clientRef.current;

  const [running, setRunning] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [lastResponse, setLastResponse] = useState<AssessResponse | null>(null);

  useEffect(() => {
    if (!autoStart) return undefined;
    activeClient.start(externalClient ? undefined : options);
    setRunning(activeClient.running);
    return () => {
      activeClient.stop();
      setRunning(false);
    };
  }, [activeClient, autoStart, externalClient, options]);

  const assess = useCallback(
    async (action: string): Promise<AssessResponse> => {
      setAssessing(true);
      try {
        const res = await activeClient.assess(action);
        setLastResponse(res);
        return res;
      } finally {
        setAssessing(false);
      }
    },
    [activeClient],
  );

  const runChallenge = useCallback(
    async (
      challenge: ChallengeInfo,
      action: string,
      challengeOptions?: RunChallengeOptions,
    ): Promise<AssessResponse> => {
      setAssessing(true);
      try {
        const res = await activeClient.runChallenge(challenge, action, challengeOptions);
        setLastResponse(res);
        return res;
      } finally {
        setAssessing(false);
      }
    },
    [activeClient],
  );

  const assessWithStepUp = useCallback(
    async (action: string, challengeOptions?: RunChallengeOptions): Promise<AssessResponse> => {
      const initial = await assess(action);
      if (initial.decision === 'challenge' && initial.challenge) {
        return runChallenge(initial.challenge, action, challengeOptions);
      }
      return initial;
    },
    [assess, runChallenge],
  );

  const value = useMemo<BotGuardContextValue>(
    () => ({
      client: activeClient,
      running,
      assessing,
      lastResponse,
      assess,
      runChallenge,
      assessWithStepUp,
    }),
    [activeClient, running, assessing, lastResponse, assess, runChallenge, assessWithStepUp],
  );

  return <BotGuardContext.Provider value={value}>{children}</BotGuardContext.Provider>;
}

/**
 * Access the active {@link BotGuardContextValue} inside a {@link BotGuardProvider}.
 * Throws an error if called outside a provider.
 */
export function useBotGuard(): BotGuardContextValue {
  const ctx = useContext(BotGuardContext);
  if (!ctx) {
    throw new Error('useBotGuard() must be used within a <BotGuardProvider>');
  }
  return ctx;
}

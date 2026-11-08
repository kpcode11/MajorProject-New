/**
 * BotGuard browser SDK entry point.
 *
 * The public API (`BotGuard.start()`, `assess()`, `runChallenge()`, `stop()`) is added in P6-07.
 */
export {
  BotGuardConfigError,
  DEFAULT_CONFIG,
  HARD_LIMITS,
  SCHEMA_VERSION,
  SDK_VERSION,
  endpointUrl,
  resolveConfig,
} from './config';
export type { BotGuardConfig, BotGuardOptions, EndpointPaths } from './config';
export { collectEnv, deviceClass } from './collectors/env';
export type { EnvSignals } from './collectors/env';
export { MouseCollector } from './collectors/mouse';
export type { MouseBehaviour, MouseCollectorOptions } from './collectors/mouse';
export { KeyboardCollector, keyClass } from './collectors/keyboard';
export type { KeyBehaviour, KeyClass, KeyboardCollectorOptions } from './collectors/keyboard';
export { ScrollCollector } from './collectors/scroll';
export { TimingCollector } from './collectors/timing';
export type { TimingCollectorOptions, TimingSignals } from './collectors/timing';
export {
  BotGuardTransportError,
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
export type {
  AssessRequestPayload,
  AssessResponse,
  BackendErrorDetail,
  BehaviourPayload,
  BuildAssessPayloadInput,
  BuildChallengePayloadInput,
  ChallengeAssessRequestPayload,
  ChallengeInfo,
  DeviceClass,
  ModelVersions,
  NonceResponse,
  TouchBehaviour,
  TouchGesture,
  TouchPointTuple,
  TransportDeps,
} from './transport';

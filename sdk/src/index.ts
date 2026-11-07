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


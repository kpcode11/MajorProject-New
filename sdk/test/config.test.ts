import { describe, expect, it } from 'vitest';
import {
  BotGuardConfigError,
  DEFAULT_CONFIG,
  HARD_LIMITS,
  endpointUrl,
  resolveConfig,
} from '../src/config';

describe('resolveConfig', () => {
  it('returns the documented defaults', () => {
    const config = resolveConfig();
    expect(config.windowMs).toBe(10_000);
    expect(config.maxMousePoints).toBe(600);
    expect(config.maxKeyEvents).toBe(300);
    expect(config.mouseThrottleMs).toBe(16);
    expect(config.paths).toEqual({
      nonce: '/v1/nonce',
      assess: '/v1/assess',
      challenge: '/v1/assess/challenge',
    });
    expect(Object.isFrozen(config)).toBe(true);
  });

  it('merges partial overrides including nested paths', () => {
    const config = resolveConfig({
      endpoint: 'http://127.0.0.1:8000/',
      maxMousePoints: 300,
      paths: { assess: '/custom/assess' },
    });
    expect(config.endpoint).toBe('http://127.0.0.1:8000');
    expect(config.maxMousePoints).toBe(300);
    expect(config.paths.assess).toBe('/custom/assess');
    expect(config.paths.nonce).toBe('/v1/nonce');
  });

  it('does not mutate the defaults', () => {
    resolveConfig({ windowMs: 5_000, paths: { nonce: '/n' } });
    expect(DEFAULT_CONFIG.windowMs).toBe(10_000);
    expect(DEFAULT_CONFIG.paths.nonce).toBe('/v1/nonce');
  });

  it.each([
    ['maxMousePoints', HARD_LIMITS.maxMousePoints + 1],
    ['maxKeyEvents', HARD_LIMITS.maxKeyEvents + 1],
    ['maxClicks', HARD_LIMITS.maxClicks + 1],
    ['windowMs', 0],
    ['mouseThrottleMs', -1],
    ['maxRetries', 1.5],
    ['requestTimeoutMs', Number.NaN],
  ])('rejects invalid %s = %s', (key, value) => {
    expect(() => resolveConfig({ [key]: value })).toThrow(BotGuardConfigError);
  });

  it('rejects non-http endpoints and relative paths', () => {
    expect(() => resolveConfig({ endpoint: 'javascript:alert(1)' })).toThrow(BotGuardConfigError);
    expect(() => resolveConfig({ paths: { nonce: 'v1/nonce' } })).toThrow(BotGuardConfigError);
  });

  it('builds endpoint URLs', () => {
    expect(endpointUrl(resolveConfig(), 'nonce')).toBe('/v1/nonce');
    expect(endpointUrl(resolveConfig({ endpoint: 'http://localhost:8000' }), 'challenge')).toBe(
      'http://localhost:8000/v1/assess/challenge',
    );
  });
});

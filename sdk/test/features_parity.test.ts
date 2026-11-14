import { describe, expect, it, vi } from 'vitest';
import {
  type AssessResponse,
  BotGuardClient,
  type EnvSignals,
  KEYBOARD_FEATURE_NAMES,
  type KeyBehaviour,
  type MouseBehaviour,
  extractKeyboardFeatureDict,
  extractMouseFeatureWindows,
  serializeFeatureMap,
} from '../src/index';
import goldenFixtures from './fixtures/golden_feature_fixtures.json';

const REL_TOL = 1e-9;
const ABS_TOL = 1e-9;

function assertFeatureMapsClose(
  actual: Record<string, number | null>,
  expected: Record<string, number | null>,
  label: string,
): void {
  const actualKeys = Object.keys(actual).sort();
  const expectedKeys = Object.keys(expected).sort();
  expect(actualKeys, `${label}: feature keys mismatch`).toEqual(expectedKeys);

  for (const key of expectedKeys) {
    const a = actual[key];
    const e = expected[key];
    if (e === null || e === undefined) {
      expect(a, `${label}.${key} expected null (NaN), got ${a}`).toBeNull();
    } else {
      expect(a, `${label}.${key} expected ${e}, got null`).not.toBeNull();
      const diff = Math.abs((a as number) - e);
      const tol = Math.max(ABS_TOL, REL_TOL * Math.abs(e));
      expect(diff, `${label}.${key}: |${a} - ${e}| = ${diff} > ${tol}`).toBeLessThanOrEqual(tol);
    }
  }
}

describe('P9-08 Golden Parity: TypeScript vs Python feature extraction', () => {
  for (const fixture of goldenFixtures.mouse_fixtures) {
    it(`matches Python mouse feature extraction within 1e-9 on fixture '${fixture.name}' (120 & 104 features)`, () => {
      const mouse = fixture.mouse as unknown as MouseBehaviour;
      const env = fixture.env as unknown as EnvSignals;

      const tsWins120 = extractMouseFeatureWindows(mouse, env, {
        includeShortcutFeatures: true,
      }).map(serializeFeatureMap);
      expect(tsWins120.length).toBe(fixture.expected_windows_120.length);
      for (let i = 0; i < tsWins120.length; i += 1) {
        const win120 = tsWins120[i] ?? {};
        expect(Object.keys(win120).length).toBe(120);
        assertFeatureMapsClose(
          win120,
          fixture.expected_windows_120[i] as Record<string, number | null>,
          `mouse[${fixture.name}].win120[${i}]`,
        );
      }

      const tsWins104 = extractMouseFeatureWindows(mouse, env, {
        includeShortcutFeatures: false,
      }).map(serializeFeatureMap);
      expect(tsWins104.length).toBe(fixture.expected_windows_104.length);
      for (let i = 0; i < tsWins104.length; i += 1) {
        const win104 = tsWins104[i] ?? {};
        expect(Object.keys(win104).length).toBe(104);
        assertFeatureMapsClose(
          win104,
          fixture.expected_windows_104[i] as Record<string, number | null>,
          `mouse[${fixture.name}].win104[${i}]`,
        );
      }
    });
  }

  for (const fixture of goldenFixtures.keyboard_fixtures) {
    it(`matches Python keyboard feature extraction within 1e-9 on fixture '${fixture.name}' (31 features)`, () => {
      const keys = fixture.keys as unknown as KeyBehaviour;
      const rawFeats = extractKeyboardFeatureDict(keys);
      expect(rawFeats).not.toBeNull();
      const serialized = serializeFeatureMap(rawFeats ?? {});
      expect(Object.keys(serialized).length).toBe(KEYBOARD_FEATURE_NAMES.length);
      assertFeatureMapsClose(
        serialized,
        fixture.expected_features as Record<string, number | null>,
        `keyboard[${fixture.name}]`,
      );
    });
  }

  it('omits raw trace arrays and sends local features when sendRawTrace=false', async () => {
    let clock = 0;
    const now = (): number => clock;
    const sampleAllow: AssessResponse = {
      decision: 'allow',
      band: 'low',
      token: 'jwt-local-ok',
      challenge: null,
      request_id: 'req-local-1',
      model_versions: { mouse: 'lightgbm-v1', keyboard: 'logistic_regression-v1', fusion: 'v1' },
      degraded: false,
    };

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ nonce: 'n-local', expires_in: 300 }), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(sampleAllow), { status: 200 }));

    const client = new BotGuardClient({
      sendRawTrace: false,
      useIdleCallback: false,
      now,
      transportDeps: { fetchImpl: fetchMock },
    });
    client.start();

    // Dispatch 12 mouse move events (>= MIN_MOUSE_MOVE_POINTS = 8)
    for (let i = 0; i < 12; i += 1) {
      clock += 25;
      const ev = new MouseEvent('mousemove', {
        clientX: 100 + i * 15,
        clientY: 200 + Math.round(Math.sin(i) * 12),
        bubbles: true,
      });
      Object.defineProperty(ev, 'isTrusted', { value: true });
      window.dispatchEvent(ev);
    }

    // Dispatch 3 key press/release pairs (>= MIN_KEYBOARD_EVENTS = 2)
    for (let i = 0; i < 3; i += 1) {
      clock += 60;
      const kd = new KeyboardEvent('keydown', { key: 'a', code: 'KeyA', bubbles: true });
      Object.defineProperty(kd, 'isTrusted', { value: true });
      window.dispatchEvent(kd);
      clock += 75;
      const ku = new KeyboardEvent('keyup', { key: 'a', code: 'KeyA', bubbles: true });
      Object.defineProperty(ku, 'isTrusted', { value: true });
      window.dispatchEvent(ku);
    }

    const res = await client.assess('login');
    expect(res.decision).toBe('allow');
    const sentBody = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body));

    // Raw traces must be empty arrays
    expect(sentBody.behaviour.mouse.points).toEqual([]);
    expect(sentBody.behaviour.mouse.clicks).toEqual([]);
    expect(sentBody.behaviour.keys.events).toEqual([]);

    // Local derived features must be populated
    expect(sentBody.behaviour.mouse.features).toBeTypeOf('object');
    expect(sentBody.behaviour.mouse.feature_windows?.length).toBe(1);
    expect(sentBody.behaviour.mouse.features.path_length_mean).toBeGreaterThan(20);
    expect(sentBody.behaviour.keys.features).toBeTypeOf('object');
    expect(sentBody.behaviour.keys.features.n_keys).toBe(3);

    client.stop();
  });
});

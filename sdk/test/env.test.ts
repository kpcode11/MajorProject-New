import { describe, expect, it } from 'vitest';
import {
  classifyRenderer,
  collectEnv,
  deviceClass,
  floorBucket,
  nativeIntegrityOk,
  nearestBucket,
  parseUserAgent,
  screenBucket,
} from '../src/collectors/env';

const CHROME_WIN_UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.127 Safari/537.36';

interface FakeOptions {
  ua?: string;
  webdriver?: boolean;
  renderer?: string | null;
  storageThrows?: boolean;
  touch?: boolean;
}

/** Minimal window stand-in exposing only what collectEnv reads. */
function fakeWindow(o: FakeOptions = {}): Window {
  const store = new Map<string, string>();
  const gl = {
    RENDERER: 0x1f01,
    getExtension: (name: string) =>
      name === 'WEBGL_debug_renderer_info'
        ? { UNMASKED_RENDERER_WEBGL: 0x9246 }
        : name === 'WEBGL_lose_context'
          ? { loseContext: () => undefined }
          : null,
    getParameter: () => o.renderer ?? null,
  };
  const win: Record<string, unknown> = {
    navigator: {
      webdriver: o.webdriver ?? false,
      userAgent: o.ua ?? CHROME_WIN_UA,
      platform: 'Win32',
      userAgentData: {
        brands: [
          { brand: 'Not/A)Brand', version: '8' },
          { brand: 'Chromium', version: '126' },
          { brand: 'Google Chrome', version: '126' },
        ],
        platform: 'Windows',
      },
      languages: ['en-IN', 'en'],
      language: 'en-IN',
      hardwareConcurrency: 12,
      deviceMemory: 8,
      plugins: { length: 5 },
      maxTouchPoints: 0,
    },
    screen: { width: 1920, height: 1080 },
    innerWidth: 1280,
    innerHeight: 720,
    outerWidth: 1296,
    outerHeight: 800,
    devicePixelRatio: 1.1,
    localStorage: {
      setItem: (k: string, v: string) => {
        if (o.storageThrows) throw new Error('denied');
        store.set(k, v);
      },
      removeItem: (k: string) => store.delete(k),
    },
    document: {
      visibilityState: 'visible',
      createElement: () => ({ getContext: () => (o.renderer === undefined ? null : gl) }),
    },
  };
  if (o.touch) win.ontouchstart = null;
  return win as unknown as Window;
}

describe('bucketing helpers', () => {
  it('snaps to nearest and floor buckets', () => {
    expect(nearestBucket(1.1, [1, 1.5, 2])).toBe(1);
    expect(nearestBucket(1.8, [1, 1.5, 2])).toBe(2);
    expect(floorBucket(12, [1, 2, 4, 8, 16])).toBe(8);
    expect(floorBucket(0.5, [1, 2])).toBe(1);
    expect(nearestBucket(Number.NaN, [1])).toBeUndefined();
    expect(screenBucket(1918, 'w')).toBe(1920);
    expect(screenBucket(1079, 'h')).toBe(1080);
  });
});

describe('parseUserAgent', () => {
  it.each([
    [CHROME_WIN_UA, 'chrome', 126, 'windows'],
    [
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 Edg/126.0',
      'edge',
      126,
      'windows',
    ],
    [
      'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',
      'firefox',
      128,
      'linux',
    ],
    [
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
      'safari',
      17,
      'macos',
    ],
    [
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
      'safari',
      17,
      'ios',
    ],
    [
      'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36',
      'chrome',
      126,
      'android',
    ],
    [
      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/126.0 Safari/537.36',
      'chrome',
      126,
      'linux',
    ],
  ])('classifies %s', (ua, family, major, os) => {
    expect(parseUserAgent(ua)).toEqual({ family, major, os });
  });

  it('falls back to other', () => {
    expect(parseUserAgent('curl/8.0')).toEqual({ family: 'other', os: 'other' });
  });
});

describe('classifyRenderer', () => {
  it.each([
    ['ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)', 'software'],
    ['llvmpipe (LLVM 15.0.7, 256 bits)', 'software'],
    ['VMware SVGA 3D', 'virtual'],
    ['ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'hardware'],
    [null, 'unknown'],
  ])('%s -> %s', (renderer, expected) => {
    expect(classifyRenderer(renderer)).toBe(expected);
  });
});

describe('nativeIntegrityOk', () => {
  it('accepts built-ins and rejects overridden functions', () => {
    expect(nativeIntegrityOk([Math.max, JSON.stringify])).toBe(true);
    expect(nativeIntegrityOk([Math.max, () => 1])).toBe(false);
    expect(nativeIntegrityOk([undefined])).toBeUndefined();
  });
});

describe('collectEnv', () => {
  it('produces the coarse Appendix B.2 snapshot for normal Chrome on Windows', () => {
    const env = collectEnv(fakeWindow({ renderer: 'ANGLE (NVIDIA GeForce)' }), {
      integrityTargets: [Math.max],
    });
    expect(env).toMatchObject({
      webdriver: false,
      ua_family: 'chrome',
      ua_major: 126,
      ua_os: 'windows',
      platform: 'Win32',
      hints_brands: ['Chromium', 'Google Chrome'],
      hints_platform: 'Windows',
      languages_count: 2,
      lang_primary: 'en-IN',
      screen_w_bucket: 1920,
      screen_h_bucket: 1080,
      viewport_w: 1280,
      viewport_h: 720,
      outer_w: 1296,
      outer_h: 800,
      dpr_bucket: 1,
      hw_concurrency_bucket: 8,
      device_memory_bucket: 8,
      webgl_renderer_class: 'hardware',
      plugins_count: 5,
      max_touch_points: 0,
      touch_event_supported: false,
      native_fn_integrity_ok: true,
      storage_available: true,
      visibility: 'visible',
    });
    expect(typeof env.timezone_offset_min).toBe('number');
    expect(deviceClass(env)).toBe('desktop');
  });

  it('flags automation-like environments', () => {
    const env = collectEnv(
      fakeWindow({ webdriver: true, renderer: 'SwiftShader', storageThrows: true }),
      { integrityTargets: [() => 0] },
    );
    expect(env.webdriver).toBe(true);
    expect(env.webgl_renderer_class).toBe('software');
    expect(env.native_fn_integrity_ok).toBe(false);
    expect(env.storage_available).toBe(false);
  });

  it('never exposes raw high-entropy strings or hashes', () => {
    const renderer = 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11)';
    const json = JSON.stringify(collectEnv(fakeWindow({ renderer }), { integrityTargets: [] }));
    expect(json).not.toContain('Mozilla');
    expect(json).not.toContain('RTX 3060');
    expect(json).not.toMatch(/hash|fingerprint/i);
  });

  it('detects touch-capable mobile devices', () => {
    const ua =
      'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36';
    const win = fakeWindow({ ua, touch: true });
    (win.screen as { width: number; height: number }).width = 412;
    (win.screen as { width: number; height: number }).height = 915;
    const env = collectEnv(win, { skipWebgl: true });
    expect(env.touch_event_supported).toBe(true);
    expect(env.webgl_renderer_class).toBe('unknown');
    expect(deviceClass(env)).toBe('mobile');
  });

  it('does not throw on the real (happy-dom) window', () => {
    const env = collectEnv(window);
    expect(env.ua_family).toBeTypeOf('string');
    expect(env.storage_available).toBeTypeOf('boolean');
  });
});

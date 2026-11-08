/**
 * Environment snapshot collector (Appendix B.2, P6-02).
 *
 * Privacy rules:
 * - Every value is coarse: categorical labels, counts, or values snapped to buckets.
 * - The raw user-agent string, WebGL renderer string, plugin names, fonts and canvas data are
 *   never returned. They are only classified in memory.
 * - No fingerprint hash or other persistent identifier is computed.
 *
 * Field names match `EnvSignals` in backend/app/schemas.py exactly.
 */

/** Environment signals sent as `env` in the assess request. All fields are optional. */
export interface EnvSignals {
  webdriver?: boolean;
  ua_family?: string;
  ua_major?: number;
  ua_os?: string;
  platform?: string;
  hints_brands?: string[];
  hints_platform?: string;
  languages_count?: number;
  lang_primary?: string;
  timezone_offset_min?: number;
  screen_w_bucket?: number;
  screen_h_bucket?: number;
  viewport_w?: number;
  viewport_h?: number;
  outer_w?: number;
  outer_h?: number;
  dpr_bucket?: number;
  hw_concurrency_bucket?: number;
  device_memory_bucket?: number;
  webgl_renderer_class?: 'hardware' | 'software' | 'virtual' | 'unknown';
  plugins_count?: number;
  max_touch_points?: number;
  touch_event_supported?: boolean;
  native_fn_integrity_ok?: boolean;
  storage_available?: boolean;
  visibility?: string;
}

const MAX_STR = 128;
const MAX_BRANDS = 10;
const MAX_DIM = 32_768;

const COMMON_WIDTHS = [
  320, 360, 375, 390, 412, 414, 768, 800, 1024, 1280, 1366, 1440, 1536, 1600, 1680, 1920, 2048,
  2560, 2880, 3440, 3840, 5120,
];
const COMMON_HEIGHTS = [
  568, 600, 640, 667, 720, 768, 800, 844, 864, 900, 915, 1024, 1050, 1080, 1200, 1440, 1600, 1800,
  2160, 2880,
];
const DPR_BUCKETS = [1, 1.25, 1.5, 2, 2.5, 3, 4];
const HW_BUCKETS = [1, 2, 4, 8, 16, 32, 64];
const MEMORY_BUCKETS = [0.25, 0.5, 1, 2, 4, 8, 16];

/** Return the bucket value closest to `value` (ties go to the smaller bucket). */
export function nearestBucket(value: number, buckets: readonly number[]): number | undefined {
  if (!Number.isFinite(value) || value <= 0 || buckets.length === 0) return undefined;
  let best = buckets[0] as number;
  for (const b of buckets) {
    if (Math.abs(b - value) < Math.abs(best - value)) best = b;
  }
  return best;
}

/** Return the largest bucket not above `value` (or the smallest bucket). */
export function floorBucket(value: number, buckets: readonly number[]): number | undefined {
  if (!Number.isFinite(value) || value <= 0 || buckets.length === 0) return undefined;
  let best = buckets[0] as number;
  for (const b of buckets) if (b <= value) best = b;
  return best;
}

/** Snap a screen dimension to the nearest common resolution value. */
export function screenBucket(value: number, axis: 'w' | 'h'): number | undefined {
  return nearestBucket(value, axis === 'w' ? COMMON_WIDTHS : COMMON_HEIGHTS);
}

function clampInt(value: unknown, min: number, max: number): number | undefined {
  if (typeof value !== 'number' || !Number.isFinite(value)) return undefined;
  return Math.min(max, Math.max(min, Math.round(value)));
}

function shortStr(value: unknown): string | undefined {
  if (typeof value !== 'string' || value.length === 0) return undefined;
  return value.slice(0, MAX_STR);
}

/** Coarse browser family, major version and OS family parsed from a user-agent string. */
export interface ParsedUA {
  family: string;
  major?: number;
  os: string;
}

/** Classify a user-agent string. The string itself is never stored or sent. */
export function parseUserAgent(ua: string): ParsedUA {
  const s = ua || '';
  let family = 'other';
  let major: number | undefined;
  const rules: [string, RegExp][] = [
    ['edge', /Edg(?:e|A|iOS)?\/(\d+)/],
    ['opera', /(?:OPR|Opera)\/(\d+)/],
    ['samsung', /SamsungBrowser\/(\d+)/],
    ['firefox', /(?:Firefox|FxiOS)\/(\d+)/],
    ['chrome', /(?:HeadlessChrome|Chrome|CriOS)\/(\d+)/],
    ['safari', /Version\/(\d+)[^ ]* (?:Mobile\/\S+ )?Safari\//],
  ];
  for (const [name, re] of rules) {
    const m = re.exec(s);
    if (m) {
      family = name;
      major = clampInt(Number(m[1]), 0, 9999);
      break;
    }
  }
  let os = 'other';
  if (/iPhone|iPad|iPod/.test(s)) os = 'ios';
  else if (/Android/.test(s)) os = 'android';
  else if (/CrOS/.test(s)) os = 'chromeos';
  else if (/Windows/.test(s)) os = 'windows';
  else if (/Mac OS X|Macintosh/.test(s)) os = 'macos';
  else if (/Linux|X11/.test(s)) os = 'linux';
  return major === undefined ? { family, os } : { family, major, os };
}

/** Classify an unmasked WebGL renderer string into a coarse class. */
export function classifyRenderer(
  renderer: string | null | undefined,
): EnvSignals['webgl_renderer_class'] {
  if (!renderer) return 'unknown';
  const r = renderer.toLowerCase();
  if (/swiftshader|llvmpipe|softpipe|software|basic render|mesa offscreen/.test(r))
    return 'software';
  if (/virtualbox|vmware|parallels|hyper-v|qxl|virgl|svga3d/.test(r)) return 'virtual';
  return 'hardware';
}

/** True when every function's source text is the browser's `[native code]` placeholder. */
export function nativeIntegrityOk(fns: readonly unknown[]): boolean | undefined {
  const fnToString = Function.prototype.toString;
  let checked = 0;
  try {
    if (!/\[native code\]/.test(fnToString.call(fnToString))) return false;
    for (const fn of fns) {
      if (typeof fn !== 'function') continue;
      checked += 1;
      if (!/\{\s*\[native code\]\s*\}\s*$/.test(fnToString.call(fn))) return false;
    }
  } catch {
    return false;
  }
  return checked > 0 ? true : undefined;
}

function defaultIntegrityTargets(win: Window): unknown[] {
  const targets: unknown[] = [];
  try {
    const nav = Object.getPrototypeOf(win.navigator) as object | null;
    const desc = nav ? Object.getOwnPropertyDescriptor(nav, 'webdriver') : undefined;
    targets.push(desc?.get);
    targets.push(win.document?.createElement);
    targets.push(
      (win as Window & { HTMLCanvasElement?: typeof HTMLCanvasElement }).HTMLCanvasElement
        ?.prototype?.toDataURL,
    );
    targets.push(win.navigator?.permissions?.query);
  } catch {
    /* ignore: missing APIs are skipped */
  }
  return targets;
}

function webglRendererClass(win: Window): EnvSignals['webgl_renderer_class'] {
  try {
    const canvas = win.document.createElement('canvas');
    const gl = (canvas.getContext('webgl') ??
      canvas.getContext('experimental-webgl')) as WebGLRenderingContext | null;
    if (!gl || typeof gl.getExtension !== 'function') return 'unknown';
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const value = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    const cls = classifyRenderer(typeof value === 'string' ? value : null);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return cls;
  } catch {
    return 'unknown';
  }
}

function storageAvailable(win: Window): boolean {
  try {
    const key = '__bg_probe__';
    win.localStorage.setItem(key, '1');
    win.localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

interface UADataLike {
  brands?: { brand?: unknown }[];
  platform?: unknown;
}

/** Options for {@link collectEnv}; mainly for tests. */
export interface CollectEnvOptions {
  /** Functions whose `toString()` must look native; defaults to a small built-in list. */
  integrityTargets?: readonly unknown[];
  /** Skip the WebGL probe (returns `unknown`). */
  skipWebgl?: boolean;
}

/**
 * Take one environment snapshot. Never throws; unavailable values are omitted.
 *
 * @param win the window to inspect (defaults to the global window).
 */
export function collectEnv(win: Window = window, options: CollectEnvOptions = {}): EnvSignals {
  const env: EnvSignals = {};
  const nav = win.navigator;
  const safe = (fn: () => void): void => {
    try {
      fn();
    } catch {
      /* omit the field */
    }
  };

  safe(() => {
    env.webdriver = nav.webdriver === true;
  });
  safe(() => {
    const ua = parseUserAgent(nav.userAgent);
    env.ua_family = ua.family;
    if (ua.major !== undefined) env.ua_major = ua.major;
    env.ua_os = ua.os;
  });
  safe(() => {
    const p = shortStr(nav.platform);
    if (p) env.platform = p;
  });
  safe(() => {
    const uad = (nav as Navigator & { userAgentData?: UADataLike }).userAgentData;
    if (!uad) return;
    const brands = (uad.brands ?? [])
      .map((b) => (typeof b.brand === 'string' ? b.brand.trim() : ''))
      .filter((b) => b.length > 0 && !/not.?a.?brand/i.test(b))
      .slice(0, MAX_BRANDS)
      .map((b) => b.slice(0, MAX_STR));
    if (brands.length) env.hints_brands = brands;
    const hp = shortStr(uad.platform);
    if (hp) env.hints_platform = hp;
  });
  safe(() => {
    const langs = nav.languages ?? [];
    env.languages_count = clampInt(langs.length, 0, 100);
    const primary = shortStr(langs[0] ?? nav.language);
    if (primary) env.lang_primary = primary;
  });
  safe(() => {
    const off = clampInt(new Date().getTimezoneOffset(), -840, 840);
    if (off !== undefined) env.timezone_offset_min = off;
  });
  safe(() => {
    const w = screenBucket(win.screen.width, 'w');
    const h = screenBucket(win.screen.height, 'h');
    if (w !== undefined) env.screen_w_bucket = w;
    if (h !== undefined) env.screen_h_bucket = h;
  });
  safe(() => {
    const dims: [keyof EnvSignals, unknown][] = [
      ['viewport_w', win.innerWidth],
      ['viewport_h', win.innerHeight],
      ['outer_w', win.outerWidth],
      ['outer_h', win.outerHeight],
    ];
    for (const [k, v] of dims) {
      const n = clampInt(v, 0, MAX_DIM);
      if (n !== undefined) (env as Record<string, unknown>)[k] = n;
    }
  });
  safe(() => {
    const d = nearestBucket(win.devicePixelRatio, DPR_BUCKETS);
    if (d !== undefined) env.dpr_bucket = d;
  });
  safe(() => {
    const hw = floorBucket(nav.hardwareConcurrency, HW_BUCKETS);
    if (hw !== undefined) env.hw_concurrency_bucket = hw;
  });
  safe(() => {
    const mem = (nav as Navigator & { deviceMemory?: number }).deviceMemory;
    const m = typeof mem === 'number' ? nearestBucket(mem, MEMORY_BUCKETS) : undefined;
    if (m !== undefined) env.device_memory_bucket = m;
  });
  env.webgl_renderer_class = options.skipWebgl ? 'unknown' : webglRendererClass(win);
  safe(() => {
    const n = clampInt(nav.plugins?.length, 0, 500);
    if (n !== undefined) env.plugins_count = n;
  });
  safe(() => {
    const n = clampInt(nav.maxTouchPoints, 0, 100);
    if (n !== undefined) env.max_touch_points = n;
    env.touch_event_supported = 'ontouchstart' in win;
  });
  safe(() => {
    const ok = nativeIntegrityOk(options.integrityTargets ?? defaultIntegrityTargets(win));
    if (ok !== undefined) env.native_fn_integrity_ok = ok;
  });
  env.storage_available = storageAvailable(win);
  safe(() => {
    const v = shortStr(win.document.visibilityState);
    if (v) env.visibility = v;
  });
  return env;
}

/** Derive the coarse device class used in the behaviour payload. */
export function deviceClass(env: EnvSignals): 'desktop' | 'mobile' | 'tablet' | 'unknown' {
  if (env.ua_os === 'android' || env.ua_os === 'ios') {
    const w = env.screen_w_bucket ?? 0;
    const h = env.screen_h_bucket ?? 0;
    return Math.min(w, h) >= 768 ? 'tablet' : 'mobile';
  }
  if (env.ua_os && env.ua_os !== 'other') return 'desktop';
  return 'unknown';
}

/**
 * Local behavioural feature extraction in TypeScript (P9-08).
 *
 * Exact mathematical port of:
 * - `botguard_ml.features.windowing.window_events`
 * - `botguard_ml.features.mouse.extract_segment_features` & `extract_window_features`
 * - `botguard_ml.features.keyboard.keyboard_features`
 * - `backend/app/scoring.py` (`extract_mouse_feature_windows`, `extract_keyboard_feature_dict`)
 *
 * Used when `sendRawTrace: false` is enabled in {@link BotGuardConfig} so that raw coordinate
 * points and keystroke timing tuples never leave the browser.
 */
import type { EnvSignals } from './collectors/env';
import type { KeyBehaviour } from './collectors/keyboard';
import type { MouseBehaviour } from './collectors/mouse';

export const SEGMENT_FEATURE_NAMES = [
  'speed_mean',
  'speed_std',
  'speed_max',
  'speed_p25',
  'speed_p50',
  'speed_p75',
  'speed_p95',
  'acc_mean',
  'acc_std',
  'acc_max_abs',
  'acc_sign_change_rate',
  'jerk_mean_abs',
  'jerk_std',
  'ang_vel_mean_abs',
  'ang_vel_std',
  'curvature_mean_abs',
  'curvature_std',
  'path_length',
  'displacement',
  'straightness',
  'n_direction_changes',
  'direction_change_rate',
  'bbox_area_norm',
  'tail_reversal_ratio',
  'duration_ms',
  'n_points',
  'dt_mean',
  'dt_std',
  'dt_cv',
  'dt_mode_fraction',
  'pause_count',
  'pause_total_ms',
  'speed_peak_position',
  'accel_phase_ratio',
  'click_dwell_mean',
  'click_dwell_std',
  'pre_click_slowdown',
] as const;

export const KEYBOARD_FEATURE_NAMES = [
  'n_keys',
  'typing_speed_cps',
  'dwell_mean',
  'dwell_std',
  'dwell_median',
  'dwell_mad',
  'dwell_cv',
  'dwell_skew',
  'dwell_kurt',
  'flight_mean',
  'flight_std',
  'flight_median',
  'flight_mad',
  'flight_cv',
  'flight_skew',
  'flight_kurt',
  'flight_min',
  'flight_p5',
  'flight_p95',
  'dd_mean',
  'dd_std',
  'rollover_ratio',
  'burst_count',
  'burst_len_mean',
  'pause_count',
  'pause_mean',
  'lag1_autocorr_flight',
  'dwell_flight_corr',
  'identical_interval_fraction',
  'backspace_ratio',
  'paste_events',
] as const;

const SHORTCUT_FEATURES = new Set<string>([
  'n_points',
  'duration_ms',
  'dt_mean',
  'dt_mode_fraction',
]);

const WINDOW_SHORTCUT_FEATURES = new Set<string>([
  'window_n_points',
  'window_duration_ms',
  'window_dt_mean',
  'window_dt_mode_fraction',
]);

const HEADING_CHANGE_RAD = (10.0 * Math.PI) / 180.0;
const DT_ROUND_MS = 1.0;
const PRE_CLICK_MS = 100.0;
export const MIN_MOUSE_MOVE_POINTS = 8;
export const MIN_KEYBOARD_EVENTS = 2;

export interface CanonicalMouseEvent {
  event: 'move' | 'down' | 'up' | 'click';
  x: number;
  y: number;
  t_ms: number;
  screen_w?: number;
  screen_h?: number;
}

export interface CanonicalKeyEvent {
  key_class: string;
  down_ms: number;
  up_ms: number;
}

/** Round half to even (matches Python `round()` and NumPy `np.round()`). */
function roundHalfToEven(value: number): number {
  const floor = Math.floor(value);
  const diff = value - floor;
  if (Math.abs(diff - 0.5) < 1e-12) {
    return floor % 2 === 0 ? floor : floor + 1;
  }
  return Math.round(value);
}

function mean(values: readonly number[]): number {
  if (values.length === 0) return Number.NaN;
  let sum = 0;
  for (const v of values) sum += v;
  return sum / values.length;
}

/** Sample standard deviation (`ddof = 1`), matching `_std` in `botguard_ml.features.mouse`. */
function sampleStd(values: readonly number[]): number {
  const n = values.length;
  if (n < 2) return Number.NaN;
  const m = mean(values);
  let sq = 0;
  for (const v of values) {
    const d = v - m;
    sq += d * d;
  }
  return Math.sqrt(sq / (n - 1));
}

/** Population standard deviation (`ddof = 0`), matching `np.std` in `botguard_ml.features.keyboard`. */
function popStd(values: readonly number[]): number {
  const n = values.length;
  if (n === 0) return Number.NaN;
  const m = mean(values);
  let sq = 0;
  for (const v of values) {
    const d = v - m;
    sq += d * d;
  }
  return Math.sqrt(sq / n);
}

function maxVal(values: readonly number[]): number {
  if (values.length === 0) return Number.NaN;
  let best = values[0] ?? Number.NaN;
  for (let i = 1; i < values.length; i += 1) {
    const cur = values[i] ?? Number.NaN;
    if (cur > best) best = cur;
  }
  return best;
}

function minVal(values: readonly number[]): number {
  if (values.length === 0) return Number.NaN;
  let best = values[0] ?? Number.NaN;
  for (let i = 1; i < values.length; i += 1) {
    const cur = values[i] ?? Number.NaN;
    if (cur < best) best = cur;
  }
  return best;
}

/** Linear percentile matching `np.percentile(values, q, method="linear")`. */
function percentile(values: readonly number[], q: number): number {
  const n = values.length;
  if (n === 0) return Number.NaN;
  const sorted = [...values].sort((a, b) => a - b);
  if (n === 1) return sorted[0] ?? Number.NaN;
  const pos = (q / 100.0) * (n - 1);
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  const frac = pos - lo;
  const loVal = sorted[lo] ?? 0;
  const hiVal = sorted[hi] ?? loVal;
  return loVal + frac * (hiVal - loVal);
}

function safeDiv(num: number, den: number): number {
  if (!Number.isFinite(num) || !Number.isFinite(den) || den === 0) {
    return Number.NaN;
  }
  return num / den;
}

function wrapDelta(delta: number): number {
  return Math.atan2(Math.sin(delta), Math.cos(delta));
}

function copysignOne(x: number): number {
  return x < 0 || Object.is(x, -0) ? -1.0 : 1.0;
}

function signChangeRate(values: readonly number[]): number {
  if (values.length === 0) return Number.NaN;
  const signs: number[] = [];
  for (const v of values) {
    if (v !== 0) signs.push(copysignOne(v));
  }
  if (signs.length < 2) return 0.0;
  let changes = 0;
  for (let i = 0; i < signs.length - 1; i += 1) {
    if (signs[i] !== signs[i + 1]) changes += 1;
  }
  return changes / (signs.length - 1);
}

function deduplicateMouseEvents(events: readonly CanonicalMouseEvent[]): CanonicalMouseEvent[] {
  const ordered = [...events].sort((a, b) => a.t_ms - b.t_ms);
  const result: CanonicalMouseEvent[] = [];
  const seen = new Set<string>();
  for (const ev of ordered) {
    const key = `${ev.t_ms}|${ev.x}|${ev.y}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push({ ...ev });
  }
  return result;
}

export function windowMouseEvents(
  events: readonly CanonicalMouseEvent[],
  options: { windowS?: number; hopS?: number; minMoves?: number } = {},
): CanonicalMouseEvent[][] {
  const windowS = options.windowS ?? 10.0;
  const hopS = options.hopS ?? 5.0;
  const minMoves = options.minMoves ?? 20;
  const cleaned = deduplicateMouseEvents(events);
  if (cleaned.length === 0) return [];

  const windowMs = windowS * 1000.0;
  const hopMs = hopS * 1000.0;
  const times = cleaned.map((e) => e.t_ms);
  const firstT = times[0] ?? 0;
  const lastT = times[times.length - 1] ?? 0;
  const nEvents = cleaned.length;
  const windows: CanonicalMouseEvent[][] = [];
  let stepIdx = 0;
  let left = 0;

  while (true) {
    const start = firstT + stepIdx * hopMs;
    if (start > lastT) break;
    while (left < nEvents && (times[left] ?? 0) < start) {
      left += 1;
    }
    if (left >= nEvents) break;
    const end = start + windowMs;
    const leftT = times[left] ?? 0;
    if (leftT >= end && minMoves > 0) {
      const jump = Math.floor((leftT - firstT - windowMs) / hopMs) + 1;
      stepIdx = Math.max(stepIdx + 1, jump);
      continue;
    }
    let right = left;
    while (right < nEvents && (times[right] ?? 0) < end) {
      right += 1;
    }
    let moveCount = 0;
    for (let i = left; i < right; i += 1) {
      if (cleaned[i]?.event === 'move') moveCount += 1;
    }
    if (moveCount >= minMoves) {
      windows.push(cleaned.slice(left, right).map((e) => ({ ...e })));
    }
    stepIdx += 1;
  }
  return windows;
}

function pathLengthPx(events: readonly CanonicalMouseEvent[]): number {
  let length = 0.0;
  let prev: [number, number] | null = null;
  for (const ev of events) {
    if (prev !== null) {
      length += Math.hypot(ev.x - prev[0], ev.y - prev[1]);
    }
    prev = [ev.x, ev.y];
  }
  return length;
}

export function segmentMouseTrajectory(
  events: readonly CanonicalMouseEvent[],
  options: { pauseMs?: number; minPoints?: number; minPathPx?: number } = {},
): CanonicalMouseEvent[][] {
  const pauseMs = options.pauseMs ?? 100.0;
  const minPoints = options.minPoints ?? 8;
  const minPathPx = options.minPathPx ?? 20.0;
  const cleaned = deduplicateMouseEvents(events);
  const segments: CanonicalMouseEvent[][] = [];
  let current: CanonicalMouseEvent[] = [];
  let lastMoveT: number | null = null;

  const flush = (): void => {
    if (current.length >= minPoints && pathLengthPx(current) >= minPathPx) {
      segments.push(current);
    }
    current = [];
  };

  for (const item of cleaned) {
    const tMs = item.t_ms;
    const kind = item.event;
    const paused = current.length > 0 && lastMoveT !== null && tMs - lastMoveT >= pauseMs;
    if (paused) {
      flush();
      lastMoveT = null;
    }
    if (kind === 'down' || kind === 'up' || kind === 'click') {
      current.push({ ...item });
      flush();
      lastMoveT = null;
      continue;
    }
    current.push({ ...item });
    if (kind === 'move') {
      lastMoveT = tMs;
    }
  }
  flush();
  return segments;
}

type CoordTuple = [number, number, number]; // [t_ms, x, y]

function coordinatePoints(events: readonly CanonicalMouseEvent[]): CoordTuple[] {
  const pts: CoordTuple[] = events.map((e) => [e.t_ms, e.x, e.y]);
  pts.sort((a, b) => a[0] - b[0]);
  return pts;
}

function positiveIntervals(points: readonly CoordTuple[]): {
  dtMs: number[];
  speeds: number[];
  speedEndT: number[];
  headings: number[];
  headingEndT: number[];
  headingSteps: number[];
} {
  const dtMs: number[] = [];
  const speeds: number[] = [];
  const speedEndT: number[] = [];
  const headings: number[] = [];
  const headingEndT: number[] = [];
  const headingSteps: number[] = [];

  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i];
    const p1 = points[i + 1];
    if (!p0 || !p1) continue;
    const [t0, x0, y0] = p0;
    const [t1, x1, y1] = p1;
    const deltaT = t1 - t0;
    if (deltaT <= 0) continue;
    const dx = x1 - x0 === 0 ? 0.0 : x1 - x0;
    const dy = y1 - y0 === 0 ? 0.0 : y1 - y0;
    const step = Math.hypot(dx, dy);
    dtMs.push(deltaT);
    speeds.push(step / (deltaT / 1000.0));
    speedEndT.push(t1);
    if (step > 0) {
      headings.push(Math.atan2(dy, dx));
      headingEndT.push(t1);
      headingSteps.push(step);
    }
  }
  return { dtMs, speeds, speedEndT, headings, headingEndT, headingSteps };
}

function derivative(
  values: readonly number[],
  timesMs: readonly number[],
): { derived: number[]; derivedT: number[] } {
  const derived: number[] = [];
  const derivedT: number[] = [];
  for (let i = 0; i < values.length - 1; i += 1) {
    const t0 = timesMs[i] ?? 0;
    const t1 = timesMs[i + 1] ?? 0;
    const v0 = values[i] ?? 0;
    const v1 = values[i + 1] ?? 0;
    const dtS = (t1 - t0) / 1000.0;
    if (dtS <= 0) continue;
    derived.push((v1 - v0) / dtS);
    derivedT.push(t1);
  }
  return { derived, derivedT };
}

function modeFraction(dtMs: readonly number[], roundMs = DT_ROUND_MS): number {
  if (dtMs.length === 0) return Number.NaN;
  const counts = new Map<number, number>();
  let maxCount = 0;
  for (const val of dtMs) {
    const r = roundHalfToEven(val / roundMs) * roundMs;
    const c = (counts.get(r) ?? 0) + 1;
    counts.set(r, c);
    if (c > maxCount) maxCount = c;
  }
  return maxCount / dtMs.length;
}

function screenArea(events: readonly CanonicalMouseEvent[]): number {
  for (const ev of events) {
    if (ev.screen_w !== undefined && ev.screen_h !== undefined) {
      const area = ev.screen_w * ev.screen_h;
      if (area > 0 && Number.isFinite(area)) return area;
    }
  }
  return Number.NaN;
}

function tailReversalRatio(points: readonly CoordTuple[], pathLen: number): number {
  const lastPt = points[points.length - 1];
  if (points.length < 2 || pathLen <= 0 || !lastPt) return Number.NaN;
  const [, endX, endY] = lastPt;
  let closestIdx = 0;
  let bestDist = Infinity;
  for (let i = 0; i < points.length - 1; i += 1) {
    const pt = points[i];
    if (!pt) continue;
    const d = Math.hypot(pt[1] - endX, pt[2] - endY);
    if (d < bestDist) {
      bestDist = d;
      closestIdx = i;
    }
  }
  let tail = 0.0;
  for (let i = closestIdx; i < points.length - 1; i += 1) {
    const p0 = points[i];
    const p1 = points[i + 1];
    if (!p0 || !p1) continue;
    tail += Math.hypot(p1[1] - p0[1], p1[2] - p0[2]);
  }
  return tail / pathLen;
}

function clickDwells(events: readonly CanonicalMouseEvent[]): number[] {
  const dwells: number[] = [];
  let downT: number | null = null;
  for (const ev of events) {
    if (ev.event === 'down') {
      downT = ev.t_ms;
    } else if (ev.event === 'up' && downT !== null) {
      const dwell = ev.t_ms - downT;
      if (dwell >= 0) dwells.push(dwell);
      downT = null;
    }
  }
  return dwells;
}

interface TimingSummary {
  duration_ms: number;
  n_points: number;
  dt_mean: number;
  dt_std: number;
  dt_cv: number;
  dt_mode_fraction: number;
  pause_count: number;
  pause_total_ms: number;
}

function timingFeatures(
  points: readonly CoordTuple[],
  dtMs: readonly number[],
  pauseMs: number,
): TimingSummary {
  const firstPt = points[0];
  const lastPt = points[points.length - 1];
  const durationMs = points.length >= 2 && firstPt && lastPt ? lastPt[0] - firstPt[0] : 0.0;
  const pauses = dtMs.filter((v) => v > pauseMs);
  const dtMean = mean(dtMs);
  const dtStd = sampleStd(dtMs);
  let pauseTotal = 0.0;
  for (const p of pauses) pauseTotal += p;
  return {
    duration_ms: durationMs,
    n_points: points.length,
    dt_mean: dtMean,
    dt_std: dtStd,
    dt_cv: safeDiv(dtStd, dtMean),
    dt_mode_fraction: modeFraction(dtMs),
    pause_count: pauses.length,
    pause_total_ms: pauseTotal,
  };
}

export function extractSegmentFeatures(
  events: readonly CanonicalMouseEvent[],
  options: { pauseMs?: number; headingChangeRad?: number } = {},
): Record<string, number> {
  const pauseMs = options.pauseMs ?? 100.0;
  const headingChangeRad = options.headingChangeRad ?? HEADING_CHANGE_RAD;
  const points = coordinatePoints(events);
  const firstPt = points[0];
  const lastPt = points[points.length - 1];
  if (points.length < 2 || !firstPt || !lastPt) {
    const empty: Record<string, number> = {};
    for (const name of SEGMENT_FEATURE_NAMES) empty[name] = Number.NaN;
    return empty;
  }

  const { dtMs, speeds, speedEndT, headings, headingEndT, headingSteps } =
    positiveIntervals(points);
  const { derived: accelerations, derivedT: accT } = derivative(speeds, speedEndT);
  const { derived: jerks } = derivative(accelerations, accT);

  const angularVelocities: number[] = [];
  const curvatures: number[] = [];
  const headingDeltas: number[] = [];
  for (let i = 0; i < headings.length - 1; i += 1) {
    const h0 = headings[i] ?? 0;
    const h1 = headings[i + 1] ?? 0;
    const t0 = headingEndT[i] ?? 0;
    const t1 = headingEndT[i + 1] ?? 0;
    const step = headingSteps[i + 1] ?? 0;
    const delta = wrapDelta(h1 - h0);
    headingDeltas.push(delta);
    const dtS = (t1 - t0) / 1000.0;
    if (dtS > 0) angularVelocities.push(delta / dtS);
    if (step > 0) curvatures.push(delta / step);
  }

  const pathLen = pathLengthPx(events);
  const displacement = Math.hypot(lastPt[1] - firstPt[1], lastPt[2] - firstPt[2]);
  let straightness = safeDiv(displacement, pathLen);
  if (Number.isFinite(straightness)) {
    straightness = Math.min(1.0, Math.max(0.0, straightness));
  }

  const significant = headingDeltas.filter((d) => Math.abs(d) >= headingChangeRad);
  let nDirectionChanges = 0.0;
  if (significant.length >= 2) {
    for (let i = 0; i < significant.length - 1; i += 1) {
      const left = significant[i] ?? 0;
      const right = significant[i + 1] ?? 0;
      if (left !== 0 && right !== 0 && copysignOne(left) !== copysignOne(right)) {
        nDirectionChanges += 1.0;
      }
    }
  }

  const xs = points.map((p) => p[1]);
  const ys = points.map((p) => p[2]);
  const bboxArea = (maxVal(xs) - minVal(xs)) * (maxVal(ys) - minVal(ys));
  const timing = timingFeatures(points, dtMs, pauseMs);
  const durationMs = timing.duration_ms;

  let peakIndex = 0;
  for (let i = 1; i < speeds.length; i += 1) {
    if ((speeds[i] ?? Number.NEGATIVE_INFINITY) > (speeds[peakIndex] ?? Number.NEGATIVE_INFINITY)) {
      peakIndex = i;
    }
  }
  const peakT = speeds.length > 0 ? (speedEndT[peakIndex] ?? 0) - firstPt[0] : Number.NaN;
  const timeAfterPeak = Number.isFinite(peakT) ? durationMs - peakT : Number.NaN;

  const dwells = clickDwells(events);
  const clickTimes = events
    .filter((e) => e.event === 'down' || e.event === 'up' || e.event === 'click')
    .map((e) => e.t_ms);
  const preClickSpeeds: number[] = [];
  if (clickTimes.length > 0) {
    const lastClick = maxVal(clickTimes);
    for (let i = 0; i < speeds.length; i += 1) {
      const endT = speedEndT[i] ?? 0;
      const sp = speeds[i];
      if (sp !== undefined && endT >= lastClick - PRE_CLICK_MS && endT <= lastClick) {
        preClickSpeeds.push(sp);
      }
    }
  }

  const speedMean = mean(speeds);
  const raw: Record<string, number> = {
    speed_mean: speedMean,
    speed_std: sampleStd(speeds),
    speed_max: maxVal(speeds),
    speed_p25: percentile(speeds, 25.0),
    speed_p50: percentile(speeds, 50.0),
    speed_p75: percentile(speeds, 75.0),
    speed_p95: percentile(speeds, 95.0),
    acc_mean: mean(accelerations),
    acc_std: sampleStd(accelerations),
    acc_max_abs: maxVal(accelerations.map((v) => Math.abs(v))),
    acc_sign_change_rate: signChangeRate(accelerations),
    jerk_mean_abs: mean(accelerations.length >= 2 ? jerks.map((v) => Math.abs(v)) : []),
    jerk_std: sampleStd(jerks),
    ang_vel_mean_abs: mean(angularVelocities.map((v) => Math.abs(v))),
    ang_vel_std: sampleStd(angularVelocities),
    curvature_mean_abs: mean(curvatures.map((v) => Math.abs(v))),
    curvature_std: sampleStd(curvatures),
    path_length: pathLen,
    displacement,
    straightness,
    n_direction_changes: nDirectionChanges,
    direction_change_rate: safeDiv(nDirectionChanges * 100.0, pathLen),
    bbox_area_norm: safeDiv(bboxArea, screenArea(events)),
    tail_reversal_ratio: tailReversalRatio(points, pathLen),
    ...timing,
    speed_peak_position: safeDiv(peakT, durationMs),
    accel_phase_ratio: safeDiv(peakT, timeAfterPeak),
    click_dwell_mean: mean(dwells),
    click_dwell_std: sampleStd(dwells),
    pre_click_slowdown: safeDiv(mean(preClickSpeeds), speedMean),
  };

  const out: Record<string, number> = {};
  for (const name of SEGMENT_FEATURE_NAMES) {
    out[name] = raw[name] ?? Number.NaN;
  }
  return out;
}

export function extractWindowFeatures(
  events: readonly CanonicalMouseEvent[],
  options: {
    pauseMs?: number;
    minPoints?: number;
    minPathPx?: number;
    headingChangeRad?: number;
    includeShortcutFeatures?: boolean;
  } = {},
): Record<string, number> {
  const pauseMs = options.pauseMs ?? 100.0;
  const minPoints = options.minPoints ?? 8;
  const minPathPx = options.minPathPx ?? 20.0;
  const headingChangeRad = options.headingChangeRad ?? HEADING_CHANGE_RAD;
  const includeShortcutFeatures = options.includeShortcutFeatures ?? true;

  const segments = segmentMouseTrajectory(events, { pauseMs, minPoints, minPathPx });
  const segmentRows = segments.map((seg) =>
    extractSegmentFeatures(seg, { pauseMs, headingChangeRad }),
  );
  const windowDwells = clickDwells(events);
  const aggregated: Record<string, number> = {};

  for (const name of SEGMENT_FEATURE_NAMES) {
    if (!includeShortcutFeatures && SHORTCUT_FEATURES.has(name)) continue;
    let values = segmentRows.map((r) => r[name] ?? Number.NaN).filter((v) => Number.isFinite(v));
    if (values.length === 0 && windowDwells.length > 0) {
      if (name === 'click_dwell_mean') {
        values = windowDwells;
      } else if (name === 'click_dwell_std' && windowDwells.length >= 2) {
        values = [sampleStd(windowDwells)];
      }
    }
    aggregated[`${name}_mean`] = mean(values);
    aggregated[`${name}_std`] = sampleStd(values);
    aggregated[`${name}_max`] = maxVal(values);
  }

  const points = coordinatePoints(events);
  const { dtMs } = positiveIntervals(points);
  const timing = timingFeatures(points, dtMs, pauseMs);
  const windowTiming: Record<string, number> = {
    window_duration_ms: timing.duration_ms,
    window_n_points: timing.n_points,
    window_dt_mean: timing.dt_mean,
    window_dt_std: timing.dt_std,
    window_dt_cv: timing.dt_cv,
    window_dt_mode_fraction: timing.dt_mode_fraction,
    window_pause_count: timing.pause_count,
    window_pause_total_ms: timing.pause_total_ms,
  };

  for (const [k, v] of Object.entries(windowTiming)) {
    if (!includeShortcutFeatures && WINDOW_SHORTCUT_FEATURES.has(k)) continue;
    aggregated[k] = v;
  }
  aggregated.n_segments = segments.length;
  return aggregated;
}

export function mouseBehaviourToEvents(
  mouse: MouseBehaviour,
  env?: EnvSignals,
): CanonicalMouseEvent[] {
  let screenW: number | undefined;
  let screenH: number | undefined;
  if (env) {
    if (typeof env.screen_w_bucket === 'number' && env.screen_w_bucket > 0) {
      screenW = env.screen_w_bucket;
    } else if (typeof env.viewport_w === 'number' && env.viewport_w > 0) {
      screenW = env.viewport_w;
    }
    if (typeof env.screen_h_bucket === 'number' && env.screen_h_bucket > 0) {
      screenH = env.screen_h_bucket;
    } else if (typeof env.viewport_h === 'number' && env.viewport_h > 0) {
      screenH = env.viewport_h;
    }
  }

  const events: CanonicalMouseEvent[] = [];
  for (const pt of mouse.points) {
    if (pt.length >= 3) {
      const ev: CanonicalMouseEvent = {
        event: 'move',
        x: Number(pt[0]),
        y: Number(pt[1]),
        t_ms: Number(pt[2]),
      };
      if (screenW !== undefined && screenH !== undefined) {
        ev.screen_w = screenW;
        ev.screen_h = screenH;
      }
      events.push(ev);
    }
  }
  for (const clk of mouse.clicks) {
    if (clk.length >= 4) {
      const x = Number(clk[0]);
      const y = Number(clk[1]);
      const downMs = Number(clk[2]);
      const upMs = Number(clk[3]);
      const downEv: CanonicalMouseEvent = { event: 'down', x, y, t_ms: downMs };
      const upEv: CanonicalMouseEvent = { event: 'up', x, y, t_ms: upMs };
      if (screenW !== undefined && screenH !== undefined) {
        downEv.screen_w = screenW;
        downEv.screen_h = screenH;
        upEv.screen_w = screenW;
        upEv.screen_h = screenH;
      }
      events.push(downEv, upEv);
    }
  }
  events.sort((a, b) => a.t_ms - b.t_ms);
  return events;
}

export function extractMouseFeatureWindows(
  mouse: MouseBehaviour,
  env?: EnvSignals,
  options: { includeShortcutFeatures?: boolean } = {},
): Record<string, number>[] {
  if (mouse.points.length < MIN_MOUSE_MOVE_POINTS) {
    return [];
  }
  const events = mouseBehaviourToEvents(mouse, env);
  let windows = windowMouseEvents(events, { windowS: 10.0, hopS: 5.0, minMoves: 20 });
  if (windows.length === 0) {
    windows = [events];
  }
  return windows.map((win) =>
    extractWindowFeatures(win, {
      includeShortcutFeatures: options.includeShortcutFeatures ?? true,
    }),
  );
}

// ---------------------------------------------------------------------------
// Keyboard feature extraction (port of botguard_ml.features.keyboard)
// ---------------------------------------------------------------------------

function kbStats(values: readonly number[], prefix: string): Record<string, number> {
  if (values.length === 0) {
    return {
      [`${prefix}_mean`]: Number.NaN,
      [`${prefix}_std`]: Number.NaN,
      [`${prefix}_median`]: Number.NaN,
      [`${prefix}_mad`]: Number.NaN,
      [`${prefix}_cv`]: Number.NaN,
      [`${prefix}_skew`]: Number.NaN,
      [`${prefix}_kurt`]: Number.NaN,
    };
  }
  const m = mean(values);
  const s = popStd(values);
  const centered = values.map((v) => v - m);
  const absCentered = centered.map((v) => Math.abs(v));
  let skew = 0.0;
  let kurt = 0.0;
  if (s > 0) {
    const s3 = s * s * s;
    const s4 = s3 * s;
    skew = mean(centered.map((c) => (c * c * c) / s3));
    kurt = mean(centered.map((c) => (c * c * c * c) / s4)) - 3.0;
  }
  return {
    [`${prefix}_mean`]: m,
    [`${prefix}_std`]: s,
    [`${prefix}_median`]: percentile(values, 50.0),
    [`${prefix}_mad`]: percentile(absCentered, 50.0),
    [`${prefix}_cv`]: m !== 0 ? s / m : Number.NaN,
    [`${prefix}_skew`]: skew,
    [`${prefix}_kurt`]: kurt,
  };
}

function pearsonCorr(x: readonly number[], y: readonly number[]): number {
  const n = x.length;
  if (n === 0 || n !== y.length) return Number.NaN;
  const mx = mean(x);
  const my = mean(y);
  let cov = 0.0;
  let vx = 0.0;
  let vy = 0.0;
  for (let i = 0; i < n; i += 1) {
    const dx = (x[i] ?? 0) - mx;
    const dy = (y[i] ?? 0) - my;
    cov += dx * dy;
    vx += dx * dx;
    vy += dy * dy;
  }
  if (vx <= 0 || vy <= 0) return Number.NaN;
  return cov / Math.sqrt(vx * vy);
}

export function extractKeyboardFeaturesFromCanonical(
  events: readonly CanonicalKeyEvent[],
): Record<string, number> {
  const ordered = [...events].sort((a, b) => a.down_ms - b.down_ms);
  if (ordered.length === 0) {
    throw new Error('keyboard window must contain at least one event');
  }
  const down = ordered.map((e) => e.down_ms);
  const up = ordered.map((e) => e.up_ms);
  const dwell = ordered.map((_, i) => (up[i] ?? 0) - (down[i] ?? 0));
  const flight: number[] = [];
  const downDelta: number[] = [];
  for (let i = 0; i < ordered.length - 1; i += 1) {
    flight.push((down[i + 1] ?? 0) - (up[i] ?? 0));
    downDelta.push((down[i + 1] ?? 0) - (down[i] ?? 0));
  }

  const duration = (down[down.length - 1] ?? 0) - (down[0] ?? 0);
  const typingSpeedCps = duration > 0 ? ordered.length / (duration / 1000.0) : Number.NaN;

  const burstLengths: number[] = [];
  let current = 1;
  for (const val of flight) {
    if (val > 300) {
      burstLengths.push(current);
      current = 1;
    } else {
      current += 1;
    }
  }
  burstLengths.push(current);

  const pauses = flight.filter((v) => v > 500);
  const negFlights = flight.filter((v) => v < 0).length;

  let identicalIntervalFraction = Number.NaN;
  if (downDelta.length > 1) {
    const rounded = downDelta.map((d) => roundHalfToEven(d));
    let zeroDiffs = 0;
    for (let i = 0; i < rounded.length - 1; i += 1) {
      if ((rounded[i + 1] ?? 0) - (rounded[i] ?? 0) === 0) zeroDiffs += 1;
    }
    identicalIntervalFraction = zeroDiffs / (rounded.length - 1);
  }

  const lag1AutocorrFlight =
    flight.length > 2 && popStd(flight) > 0
      ? pearsonCorr(flight.slice(0, -1), flight.slice(1))
      : Number.NaN;

  const dwellTail = dwell.slice(1);
  const dwellFlightCorr =
    flight.length > 1 && popStd(dwellTail) > 0 && popStd(flight) > 0
      ? pearsonCorr(dwellTail, flight)
      : Number.NaN;

  let controlCount = 0;
  for (const ev of ordered) {
    if (ev.key_class === 'control') controlCount += 1;
  }

  return {
    n_keys: ordered.length,
    typing_speed_cps: typingSpeedCps,
    ...kbStats(dwell, 'dwell'),
    ...kbStats(flight, 'flight'),
    flight_min: flight.length > 0 ? minVal(flight) : Number.NaN,
    flight_p5: flight.length > 0 ? percentile(flight, 5.0) : Number.NaN,
    flight_p95: flight.length > 0 ? percentile(flight, 95.0) : Number.NaN,
    dd_mean: downDelta.length > 0 ? mean(downDelta) : Number.NaN,
    dd_std: downDelta.length > 0 ? popStd(downDelta) : Number.NaN,
    rollover_ratio: flight.length > 0 ? negFlights / flight.length : 0.0,
    burst_count: burstLengths.length,
    burst_len_mean: mean(burstLengths),
    pause_count: pauses.length,
    pause_mean: pauses.length > 0 ? mean(pauses) : Number.NaN,
    lag1_autocorr_flight: lag1AutocorrFlight,
    dwell_flight_corr: dwellFlightCorr,
    identical_interval_fraction: identicalIntervalFraction,
    backspace_ratio: controlCount / ordered.length,
    paste_events: Number.NaN,
  };
}

export function extractKeyboardFeatureDict(keys: KeyBehaviour): Record<string, number> | null {
  if (keys.events.length < MIN_KEYBOARD_EVENTS) {
    return null;
  }
  const canonical: CanonicalKeyEvent[] = [];
  for (const item of keys.events) {
    if (item.length >= 3) {
      const rawCls = String(item[0]);
      canonical.push({
        key_class: rawCls === 'backspace' ? 'control' : rawCls,
        down_ms: Number(item[1]),
        up_ms: Number(item[2]),
      });
    }
  }
  if (canonical.length < MIN_KEYBOARD_EVENTS) {
    return null;
  }
  const feats = extractKeyboardFeaturesFromCanonical(canonical);
  feats.paste_events = keys.paste_events;
  return feats;
}

/** Convert `NaN`/`Infinity` values to `null` so a feature map serializes cleanly as JSON. */
export function serializeFeatureMap(
  features: Readonly<Record<string, number>>,
): Record<string, number | null> {
  const out: Record<string, number | null> = {};
  for (const [k, v] of Object.entries(features)) {
    out[k] = Number.isFinite(v) ? v : null;
  }
  return out;
}

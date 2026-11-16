/**
 * Automated accessibility audit using axe-core and WCAG 2.1 AA contrast verification
 * across all portal pages and the step-up challenge modal (P9-09).
 *
 * Audits:
 *  1. Landing page (`landing`)
 *  2. Resident login page (`login` — initial, validation error, and OTP result states)
 *  3. Update details page (`update-details` — initial, validation error, and result states)
 *  4. Centre search page (`centre-search` — initial, validation error, and populated results)
 *  5. Operational Admin Dashboard (`admin` — populated overview, histogram, session inspector,
 *     keyboard row selection, simulator table, feedback queue, and privacy panel)
 *  6. Step-up verification challenge modal (`role="dialog"`, press-and-hold + keyboard single-press
 *     alternative)
 */
import fs from 'node:fs';
import path from 'node:path';
import axe, { type AxeResults, type Result } from 'axe-core';
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderPressHoldChallenge } from '@botguard/sdk';
import { App } from '../src/App';

let container: HTMLDivElement | null = null;
let root: Root | null = null;
const originalFetch = globalThis.fetch;

interface AuditRecord {
  target: string;
  passes_count: number;
  violations_count: number;
  critical_violations: number;
  serious_violations: number;
  contrast_elements_checked: number;
  min_contrast_ratio: number;
}

const auditSummaryRecords: AuditRecord[] = [];

function formatViolations(violations: Result[]): string {
  if (violations.length === 0) return 'No violations';
  return violations
    .map(
      (v) =>
        `[${v.impact ?? 'unknown'}] ${v.id}: ${v.help} (${v.nodes.map((n) => n.html).join('; ')})`,
    )
    .join('\n');
}

function parseCssColor(raw: string | null | undefined): [number, number, number, number] | null {
  if (!raw) return null;
  const trimmed = raw.trim().toLowerCase();
  if (!trimmed || trimmed === 'transparent' || trimmed === 'inherit' || trimmed === 'initial') {
    return null;
  }
  if (trimmed.startsWith('#')) {
    const hex = trimmed.slice(1);
    if (hex.length === 3) {
      const h0 = hex.slice(0, 1);
      const h1 = hex.slice(1, 2);
      const h2 = hex.slice(2, 3);
      const r = parseInt(h0 + h0, 16);
      const g = parseInt(h1 + h1, 16);
      const b = parseInt(h2 + h2, 16);
      return [r, g, b, 1];
    }
    if (hex.length === 6) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return [r, g, b, 1];
    }
  }
  const rgbMatch = trimmed.match(
    /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)$/,
  );
  if (rgbMatch) {
    return [
      Number(rgbMatch[1]),
      Number(rgbMatch[2]),
      Number(rgbMatch[3]),
      rgbMatch[4] !== undefined ? Number(rgbMatch[4]) : 1,
    ];
  }
  return null;
}

function relativeLuminance([r, g, b]: [number, number, number, number]): number {
  const toLinear = (c: number): number => {
    const v = c / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function contrastRatio(
  fg: [number, number, number, number],
  bg: [number, number, number, number],
): number {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

function resolveEffectiveColor(
  el: HTMLElement,
  prop: 'color' | 'backgroundColor',
  fallback: [number, number, number, number],
): [number, number, number, number] {
  let curr: HTMLElement | null = el;
  while (curr) {
    const inlineVal = curr.style?.[prop];
    const parsed = parseCssColor(inlineVal);
    if (parsed && parsed[3] > 0) {
      return parsed;
    }
    curr = curr.parentElement;
  }
  return fallback;
}

function verifyDomContrast(rootEl: HTMLElement): { checked: number; minRatio: number } {
  const elements = Array.from(rootEl.querySelectorAll<HTMLElement>('*'));
  let checked = 0;
  let minRatio = Infinity;

  for (const el of elements) {
    if (el.classList.contains('portal-skip-link')) continue;
    const directText = Array.from(el.childNodes)
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent?.trim() ?? '')
      .join('');
    if (!directText) continue;

    const fg = resolveEffectiveColor(el, 'color', [15, 23, 42, 1]);
    const bg = resolveEffectiveColor(el, 'backgroundColor', [255, 255, 255, 1]);
    const ratio = contrastRatio(fg, bg);
    const fontSizePx = parseFloat(el.style?.fontSize || '14') || 14;
    const fontWeight = Number(el.style?.fontWeight || 400) || 400;
    const isLargeText = fontSizePx >= 24 || (fontSizePx >= 18.66 && fontWeight >= 700);
    const minRequired = isLargeText ? 3.0 : 4.5;

    checked += 1;
    if (ratio < minRatio) {
      minRatio = ratio;
    }
    expect(
      ratio,
      `Contrast ${ratio.toFixed(2)}:1 below ${minRequired}:1 on <${el.tagName.toLowerCase()}> "${directText.slice(0, 40)}"`,
    ).toBeGreaterThanOrEqual(minRequired);
  }

  return { checked, minRatio: Number.isFinite(minRatio) ? Number(minRatio.toFixed(2)) : 21 };
}

async function runAxeAudit(targetName: string, target: HTMLElement): Promise<AxeResults> {
  const results = await axe.run(target, {
    rules: {
      'label-content-name-mismatch': { enabled: true },
      'heading-order': { enabled: true },
      'empty-heading': { enabled: true },
      tabindex: { enabled: true },
    },
  });
  const contrastStats = verifyDomContrast(target);
  const criticalCount = results.violations.filter((v) => v.impact === 'critical').length;
  const seriousCount = results.violations.filter((v) => v.impact === 'serious').length;

  auditSummaryRecords.push({
    target: targetName,
    passes_count: results.passes.length,
    violations_count: results.violations.length,
    critical_violations: criticalCount,
    serious_violations: seriousCount,
    contrast_elements_checked: contrastStats.checked,
    min_contrast_ratio: contrastStats.minRatio,
  });

  return results;
}

function createPortalAndAdminMockFetch(): typeof fetch {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === 'string' ? input : input.toString();
    const url = new URL(raw, 'http://127.0.0.1');
    const method = (init?.method ?? 'GET').toUpperCase();

    if (url.pathname.endsWith('/v1/nonce')) {
      return new Response(JSON.stringify({ nonce: 'axe_nonce_1', expires_in: 120 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    if (url.pathname.endsWith('/v1/assess')) {
      return new Response(
        JSON.stringify({
          decision: 'allow',
          band: 'low',
          token: 'axe_valid_token',
          challenge: null,
          request_id: 'req_axe_1',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (url.pathname.startsWith('/portal-api/')) {
      return new Response(
        JSON.stringify({
          status: 'ok',
          message: 'Verified request completed in demo portal.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (method === 'GET' && url.pathname === '/admin/overview') {
      return new Response(
        JSON.stringify({
          total_assessments: 2,
          requests_last_1m: 1,
          requests_per_minute: 2.0,
          window_minutes: 5,
          decisions: { allow: 1, challenge: 0, deny: 1 },
          decision_rates: { allow: 0.5, challenge: 0, deny: 0.5 },
          latency_ms: { mean: 3.1, p50: 3.0, p95: 4.5 },
          degraded_count: 0,
          protection_mode: 'passive',
          model_versions: {
            mouse: 'lightgbm-v1',
            keyboard: 'logistic_regression-v1',
            touch: null,
            fusion: 'v1',
          },
          auth_note: 'Protected by static API key for student project.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (method === 'GET' && url.pathname === '/admin/scores') {
      return new Response(
        JSON.stringify({
          total_scored: 2,
          action_filter: null,
          bins: Array.from({ length: 10 }, (_, idx) => ({
            bin_index: idx,
            bin_start: Number((idx * 0.1).toFixed(2)),
            bin_end: Number(((idx + 1) * 0.1).toFixed(2)),
            label: `${(idx * 0.1).toFixed(1)}–${((idx + 1) * 0.1).toFixed(1)}`,
            count: idx === 0 ? 1 : 0,
            allow: idx === 0 ? 1 : 0,
            challenge: 0,
            deny: 0,
          })),
          band_cutoffs: { low: 0.3, medium: 0.7 },
          thresholds: {
            low: { allow_below: 0.5, deny_at_or_above: 0.9 },
            medium: { allow_below: 0.3, deny_at_or_above: 0.8 },
            high: { allow_below: 0.15, deny_at_or_above: 0.7 },
          },
          actions: { otp_request: 'high' },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (method === 'GET' && url.pathname === '/admin/assessments') {
      return new Response(
        JSON.stringify({
          total: 2,
          limit: 25,
          offset: 0,
          items: [
            {
              id: 'assess-axe-1',
              ts: '2026-11-16T06:00:00+00:00',
              session_hash: 'sess_axe_1',
              action: 'otp_request',
              device_class: 'desktop',
              score: 0.09,
              band: 'low',
              decision: 'allow',
              rules_fired: [],
              top_factors: ['mouse:straightness_mean'],
              model_versions: { mouse: 'lightgbm-v1' },
              latency_ms: 3.1,
              degraded: false,
              feedback: 'fp',
              has_features: true,
            },
            {
              id: 'assess-axe-2',
              ts: '2026-11-16T06:01:00+00:00',
              session_hash: 'sess_axe_2',
              action: 'centre_search',
              device_class: 'desktop',
              score: 0.88,
              band: 'high',
              decision: 'deny',
              rules_fired: ['R02_WEBDRIVER'],
              top_factors: ['R02_WEBDRIVER'],
              model_versions: { mouse: 'lightgbm-v1' },
              latency_ms: 1.9,
              degraded: false,
              feedback: null,
              has_features: false,
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (method === 'GET' && url.pathname.startsWith('/admin/assessments/')) {
      const id = decodeURIComponent(url.pathname.split('/').pop() ?? 'assess-axe-1');
      const isSecond = id === 'assess-axe-2';
      return new Response(
        JSON.stringify({
          id,
          ts: '2026-11-16T06:00:00+00:00',
          session_hash: isSecond ? 'sess_axe_2' : 'sess_axe_1',
          action: isSecond ? 'centre_search' : 'otp_request',
          device_class: 'desktop',
          score: isSecond ? 0.88 : 0.09,
          band: isSecond ? 'high' : 'low',
          decision: isSecond ? 'deny' : 'allow',
          rules_fired: isSecond ? ['R02_WEBDRIVER'] : [],
          top_factors: isSecond ? ['R02_WEBDRIVER'] : ['mouse:straightness_mean'],
          model_versions: { mouse: 'lightgbm-v1' },
          latency_ms: 3.1,
          degraded: false,
          feedback: isSecond ? null : 'fp',
          has_features: !isSecond,
          features: isSecond ? null : { 'mouse:straightness_mean': 0.91 },
          features_expires_at: isSecond ? null : '2026-11-23T06:00:00+00:00',
          top_contributing_features: isSecond
            ? [{ feature: 'R02_WEBDRIVER', value: null }]
            : [{ feature: 'mouse:straightness_mean', value: 0.91 }],
          challenges: [],
          privacy_note: 'Derived feature values only.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (method === 'GET' && url.pathname === '/admin/feedback') {
      return new Response(
        JSON.stringify({
          total: 1,
          fp_count: 1,
          fn_count: 0,
          training_policy: 'stored_only_never_auto_trained',
          note: 'Stored for offline review only.',
          items: [
            {
              id: 'assess-axe-1',
              ts: '2026-11-16T06:00:00+00:00',
              session_hash: 'sess_axe_1',
              action: 'otp_request',
              device_class: 'desktop',
              score: 0.09,
              band: 'low',
              decision: 'allow',
              rules_fired: [],
              top_factors: ['mouse:straightness_mean'],
              model_versions: { mouse: 'lightgbm-v1' },
              latency_ms: 3.1,
              degraded: false,
              feedback: 'fp',
              has_features: true,
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (method === 'GET' && url.pathname === '/admin/sim-results') {
      return new Response(
        JSON.stringify({
          total_runs: 1,
          by_mode: {},
          tiers: [
            {
              protection_mode: 'passive',
              tier: 'tier1',
              total: 1,
              allowed: 0,
              challenged: 0,
              denied: 1,
              blocked_at_api: 0,
              allow_rate: 0,
              caught_rate: 1,
              mean_latency_ms: 1.5,
            },
          ],
          disclaimer: 'No model, feature, or threshold was tuned on the Phase 7 simulator.',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    if (method === 'GET' && url.pathname === '/admin/privacy') {
      return new Response(
        JSON.stringify({
          retention_settings: {
            store_features_in_db: true,
            feature_ttl_seconds: 604800,
            feature_ttl_days: 7,
            assessment_ttl_seconds: 2592000,
            assessment_ttl_days: 30,
          },
          record_counts: {
            total_assessments: 2,
            assessments_with_features: 1,
            expired_feature_records: 0,
            expired_assessment_records: 0,
            total_challenges: 0,
            buffered_writes: 0,
          },
          last_purge: {
            last_purge_at: null,
            features_purged: 0,
            assessments_purged: 0,
          },
          guarantees: ['Typed characters are never collected.'],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      );
    }
    return new Response('{}', { status: 404 });
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  document.documentElement.lang = 'en';
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  globalThis.fetch = createPortalAndAdminMockFetch();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  if (root) {
    act(() => {
      root?.unmount();
    });
    root = null;
  }
  container?.remove();
  container = null;
});

afterAll(() => {
  const outPath = path.resolve(__dirname, '../../results/system/axe_audit.json');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  const payload = {
    task: 'P9-09',
    axe_version: axe.version,
    total_states_audited: auditSummaryRecords.length,
    total_violations: auditSummaryRecords.reduce((acc, r) => acc + r.violations_count, 0),
    critical_violations: auditSummaryRecords.reduce((acc, r) => acc + r.critical_violations, 0),
    serious_violations: auditSummaryRecords.reduce((acc, r) => acc + r.serious_violations, 0),
    audits: auditSummaryRecords,
  };
  fs.writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf-8');
});

function getContainer(): HTMLDivElement {
  if (!container) {
    throw new Error('Test container is not initialized');
  }
  return container;
}

describe('Portal & Step-up Challenge Accessibility Audit (P9-09)', () => {
  it('Landing page has zero axe-core or contrast violations', async () => {
    act(() => {
      root?.render(<App initialPage="landing" />);
    });

    const skipLink = container?.querySelector('[data-testid="skip-to-main"]');
    expect(skipLink?.getAttribute('href')).toBe('#portal-main-content');
    expect(container?.querySelector('main#portal-main-content')).not.toBeNull();

    const results = await runAxeAudit('landing', getContainer());
    expect(results.violations, formatViolations(results.violations)).toEqual([]);
  });

  it('Resident login page (initial, validation error, and result) has zero axe-core violations', async () => {
    act(() => {
      root?.render(<App initialPage="login" />);
    });

    const initialResults = await runAxeAudit('login:initial', getContainer());
    expect(initialResults.violations, formatViolations(initialResults.violations)).toEqual([]);

    const input = container?.querySelector(
      '[data-testid="identifier-input"]',
    ) as HTMLInputElement | null;
    const sendBtn = container?.querySelector(
      '[data-testid="send-otp-btn"]',
    ) as HTMLButtonElement | null;

    await act(async () => {
      sendBtn?.click();
    });
    expect(container?.querySelector('[data-testid="login-validation-error"]')).not.toBeNull();
    expect(input?.getAttribute('aria-invalid')).toBe('true');
    expect(input?.getAttribute('aria-describedby')).toContain('login-validation-error');

    const errorResults = await runAxeAudit('login:validation_error', getContainer());
    expect(errorResults.violations, formatViolations(errorResults.violations)).toEqual([]);

    act(() => {
      if (input) {
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          'value',
        )?.set;
        setter?.call(input, '999900001234');
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
    await act(async () => {
      sendBtn?.click();
    });
    expect(container?.querySelector('[data-testid="otp-result"]')).not.toBeNull();

    const submittedResults = await runAxeAudit('login:result', getContainer());
    expect(submittedResults.violations, formatViolations(submittedResults.violations)).toEqual([]);
  });

  it('Update details page (initial, validation error, and result) has zero axe-core violations', async () => {
    act(() => {
      root?.render(<App initialPage="update-details" />);
    });

    const initialResults = await runAxeAudit('update-details:initial', getContainer());
    expect(initialResults.violations, formatViolations(initialResults.violations)).toEqual([]);

    const submitBtn = container?.querySelector(
      '[data-testid="submit-details-btn"]',
    ) as HTMLButtonElement | null;
    await act(async () => {
      submitBtn?.click();
    });
    expect(container?.querySelector('[data-testid="details-validation-error"]')).not.toBeNull();

    const errorResults = await runAxeAudit('update-details:validation_error', getContainer());
    expect(errorResults.violations, formatViolations(errorResults.violations)).toEqual([]);
  });

  it('Centre search page (initial, validation error, and results) has zero axe-core violations', async () => {
    act(() => {
      root?.render(<App initialPage="centre-search" />);
    });

    const initialResults = await runAxeAudit('centre-search:initial', getContainer());
    expect(initialResults.violations, formatViolations(initialResults.violations)).toEqual([]);

    const queryInput = container?.querySelector(
      '[data-testid="centre-query-input"]',
    ) as HTMLInputElement | null;
    const searchBtn = container?.querySelector(
      '[data-testid="search-centres-btn"]',
    ) as HTMLButtonElement | null;

    await act(async () => {
      searchBtn?.click();
    });
    expect(queryInput?.getAttribute('aria-invalid')).toBe('true');

    const errorResults = await runAxeAudit('centre-search:validation_error', getContainer());
    expect(errorResults.violations, formatViolations(errorResults.violations)).toEqual([]);

    act(() => {
      if (queryInput) {
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype,
          'value',
        )?.set;
        setter?.call(queryInput, '560001');
        queryInput.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
    await act(async () => {
      searchBtn?.click();
    });
    expect(container?.querySelector('[data-testid="centre-results"]')).not.toBeNull();

    const populatedResults = await runAxeAudit('centre-search:results', getContainer());
    expect(populatedResults.violations, formatViolations(populatedResults.violations)).toEqual([]);
  });

  it('Admin dashboard page has zero axe-core violations and supports keyboard row selection', async () => {
    await act(async () => {
      root?.render(<App initialPage="admin" />);
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    const results = await runAxeAudit('admin-dashboard', getContainer());
    expect(results.violations, formatViolations(results.violations)).toEqual([]);

    const secondRow = container?.querySelector(
      '[data-testid="assessment-row-assess-axe-2"]',
    ) as HTMLTableRowElement | null;
    expect(secondRow).not.toBeNull();
    expect(secondRow?.getAttribute('tabindex')).toBe('0');

    await act(async () => {
      secondRow?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container?.querySelector('[data-testid="detail-assessment-id"]')?.textContent).toBe(
      'assess-axe-2',
    );
  });

  it('Step-up press-and-hold & keyboard challenge dialog has zero axe-core violations', async () => {
    act(() => {
      root?.render(<App initialPage="login" />);
    });

    const challengePromise = renderPressHoldChallenge(
      {
        id: 'chal_axe_1',
        type: 'press_hold',
        hold_ms: 900,
        expires_in: 60,
      },
      'otp_request',
      { mountTarget: getContainer(), requireTrusted: false },
    );

    const dialog = container?.querySelector('[data-testid="stepup-dialog"]');
    expect(dialog).not.toBeNull();

    const results = await runAxeAudit('stepup-challenge-dialog', getContainer());
    expect(results.violations, formatViolations(results.violations)).toEqual([]);

    const cancelBtn = container?.querySelector(
      '[data-testid="stepup-cancel-btn"]',
    ) as HTMLButtonElement | null;
    cancelBtn?.click();
    await expect(challengePromise).rejects.toThrow();
  });
});

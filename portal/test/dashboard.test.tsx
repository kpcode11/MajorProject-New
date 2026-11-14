/**
 * Admin dashboard component tests and E2E smoke (P9-03).
 *
 * Covers the six Phase 9 views and their interactions:
 *  1. Overview metrics (rpm, allow/challenge/deny, latency, model versions)
 *  2. Score histogram with policy threshold lines
 *  3. Session detail (derived features only; no raw traces)
 *  4. Simulator results per bot tier
 *  5. Analyst feedback queue (mark fp / fn)
 *  6. Privacy panel (retention settings, record counts, purge)
 * plus a portal-shell smoke test that the dashboard loads admin JSON.
 */
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';
import { AdminDashboardPage } from '../src/pages/AdminDashboardPage';
import type {
  AdminAssessmentsListData,
  AdminFeedbackData,
  AdminOverviewData,
  AdminPrivacyData,
  AdminScoresData,
  AdminSimResultsData,
  AssessmentDetailData,
  AssessmentSummaryItem,
} from '../src/adminApi';

let container: HTMLDivElement | null = null;
let root: Root | null = null;
const originalFetch = globalThis.fetch;

const ALLOW_ID = 'assess-allow-1';
const DENY_ID = 'assess-deny-3';

const OVERVIEW: AdminOverviewData = {
  total_assessments: 2,
  requests_last_1m: 2,
  requests_per_minute: 4.5,
  window_minutes: 5,
  decisions: { allow: 1, challenge: 0, deny: 1 },
  decision_rates: { allow: 0.5, challenge: 0, deny: 0.5 },
  latency_ms: { mean: 3.25, p50: 3.5, p95: 5.1 },
  degraded_count: 0,
  protection_mode: 'passive',
  model_versions: {
    mouse: 'lightgbm-v1',
    keyboard: 'logistic_regression-v1',
    touch: null,
    fusion: 'v1',
  },
  auth_note:
    'Protected by static API key (X-Admin-Key / Bearer) for student project; production deployments require SSO/OIDC/OAuth2 with role-based access control (RBAC).',
};

const SCORES: AdminScoresData = {
  total_scored: 2,
  action_filter: null,
  bins: Array.from({ length: 10 }, (_, idx) => ({
    bin_index: idx,
    bin_start: Number((idx * 0.1).toFixed(2)),
    bin_end: Number(((idx + 1) * 0.1).toFixed(2)),
    label: `${(idx * 0.1).toFixed(1)}–${((idx + 1) * 0.1).toFixed(1)}`,
    count: idx === 0 || idx === 9 ? 1 : 0,
    allow: idx === 0 ? 1 : 0,
    challenge: 0,
    deny: idx === 9 ? 1 : 0,
  })),
  band_cutoffs: { low: 0.3, medium: 0.7 },
  thresholds: {
    low: { allow_below: 0.5, deny_at_or_above: 0.9 },
    medium: { allow_below: 0.3, deny_at_or_above: 0.8 },
    high: { allow_below: 0.15, deny_at_or_above: 0.7 },
  },
  actions: {
    otp_request: 'high',
    details_update: 'high',
    centre_search: 'medium',
    login: 'medium',
  },
};

const ALLOW_SUMMARY: AssessmentSummaryItem = {
  id: ALLOW_ID,
  ts: '2026-11-14T08:00:00+00:00',
  session_hash: 'sess_allow',
  action: 'otp_request',
  device_class: 'desktop',
  score: 0.08,
  band: 'low',
  decision: 'allow',
  rules_fired: [],
  top_factors: ['mouse:straightness_mean', 'keyboard:dwell_std'],
  model_versions: { mouse: 'lightgbm-v1', keyboard: 'logistic_regression-v1' },
  latency_ms: 3.5,
  degraded: false,
  feedback: null,
  has_features: true,
};

const DENY_SUMMARY: AssessmentSummaryItem = {
  id: DENY_ID,
  ts: '2026-11-14T08:01:00+00:00',
  session_hash: 'sess_deny',
  action: 'otp_request',
  device_class: 'desktop',
  score: 0.92,
  band: 'high',
  decision: 'deny',
  rules_fired: ['R02_WEBDRIVER', 'R11_UNTRUSTED_EVENTS'],
  top_factors: ['R02_WEBDRIVER', 'R11_UNTRUSTED_EVENTS'],
  model_versions: { mouse: 'lightgbm-v1', keyboard: 'logistic_regression-v1' },
  latency_ms: 1.8,
  degraded: false,
  feedback: null,
  has_features: false,
};

const ALLOW_DETAIL: AssessmentDetailData = {
  ...ALLOW_SUMMARY,
  features: {
    'mouse:straightness_mean': 0.912,
    'keyboard:dwell_std': 18.4,
  },
  features_expires_at: '2026-11-21T08:00:00+00:00',
  top_contributing_features: [
    { feature: 'mouse:straightness_mean', value: 0.912 },
    { feature: 'keyboard:dwell_std', value: 18.4 },
  ],
  challenges: [],
  privacy_note: 'Derived feature values only; raw traces are never stored.',
};

const DENY_DETAIL: AssessmentDetailData = {
  ...DENY_SUMMARY,
  features: null,
  features_expires_at: null,
  top_contributing_features: [
    { feature: 'R02_WEBDRIVER', value: null },
    { feature: 'R11_UNTRUSTED_EVENTS', value: null },
  ],
  challenges: [],
  privacy_note: 'Derived feature values only; raw traces are never stored.',
};

const SIM_RESULTS: AdminSimResultsData = {
  total_runs: 3,
  by_mode: {
    passive: {
      tier1: {
        total: 2,
        allowed: 0,
        challenged: 0,
        denied: 0,
        blocked_at_api: 2,
        allow_rate: 0,
        caught_rate: 1,
        mean_latency_ms: 1.2,
      },
      tier4: {
        total: 1,
        allowed: 0,
        challenged: 0,
        denied: 1,
        blocked_at_api: 0,
        allow_rate: 0,
        caught_rate: 1,
        mean_latency_ms: 4.8,
      },
    },
  },
  tiers: [
    {
      protection_mode: 'passive',
      tier: 'tier1',
      total: 2,
      allowed: 0,
      challenged: 0,
      denied: 0,
      blocked_at_api: 2,
      allow_rate: 0,
      caught_rate: 1,
      mean_latency_ms: 1.2,
    },
    {
      protection_mode: 'passive',
      tier: 'tier4',
      total: 1,
      allowed: 0,
      challenged: 0,
      denied: 1,
      blocked_at_api: 0,
      allow_rate: 0,
      caught_rate: 1,
      mean_latency_ms: 4.8,
    },
  ],
  disclaimer: 'No model, feature, or threshold was tuned on the Phase 7 simulator.',
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

interface DashboardBackendState {
  items: AssessmentSummaryItem[];
  details: Record<string, AssessmentDetailData>;
  privacy: AdminPrivacyData;
}

function createBackendState(): DashboardBackendState {
  return {
    items: [clone(ALLOW_SUMMARY), clone(DENY_SUMMARY)],
    details: {
      [ALLOW_ID]: clone(ALLOW_DETAIL),
      [DENY_ID]: clone(DENY_DETAIL),
    },
    privacy: {
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
      guarantees: [
        'Raw mouse coordinates, keystroke timings, and touch traces are never persisted.',
        'Typed characters, key identities, and form field values are never collected.',
      ],
    },
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function createDashboardFetch(state: DashboardBackendState): typeof fetch {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === 'string' ? input : input.toString();
    const url = new URL(raw, 'http://127.0.0.1');
    const method = (init?.method ?? 'GET').toUpperCase();
    const headers = (init?.headers as Record<string, string> | undefined) ?? {};
    const adminKey = headers['X-Admin-Key'] ?? headers['x-admin-key'];

    if (url.pathname.startsWith('/admin/') && adminKey !== 'dev-admin-key') {
      return jsonResponse({ error: { message: 'unauthorized_admin' } }, 401);
    }

    if (method === 'GET' && url.pathname === '/admin/overview') {
      return jsonResponse(OVERVIEW);
    }
    if (method === 'GET' && url.pathname === '/admin/scores') {
      return jsonResponse(SCORES);
    }
    if (method === 'GET' && url.pathname === '/admin/assessments') {
      const decision = url.searchParams.get('decision');
      const items = decision
        ? state.items.filter((item) => item.decision === decision)
        : state.items;
      const payload: AdminAssessmentsListData = {
        total: items.length,
        limit: 25,
        offset: 0,
        items,
      };
      return jsonResponse(payload);
    }
    if (method === 'GET' && url.pathname.startsWith('/admin/assessments/')) {
      const id = decodeURIComponent(url.pathname.split('/').pop() ?? '');
      const detail = state.details[id];
      if (!detail) {
        return jsonResponse({ error: { message: 'assessment_not_found' } }, 404);
      }
      return jsonResponse(detail);
    }
    if (method === 'GET' && url.pathname === '/admin/feedback') {
      const marked = state.items.filter((item) => item.feedback === 'fp' || item.feedback === 'fn');
      const payload: AdminFeedbackData = {
        total: marked.length,
        fp_count: marked.filter((item) => item.feedback === 'fp').length,
        fn_count: marked.filter((item) => item.feedback === 'fn').length,
        training_policy: 'stored_only_never_auto_trained',
        note: 'Analyst feedback is stored for offline review only and never auto-used for training.',
        items: marked,
      };
      return jsonResponse(payload);
    }
    if (method === 'POST' && url.pathname === '/admin/feedback') {
      const body = JSON.parse(typeof init?.body === 'string' ? init.body : '{}') as {
        assessment_id?: string;
        feedback?: 'fp' | 'fn' | null;
      };
      const id = body.assessment_id ?? '';
      const item = state.items.find((row) => row.id === id);
      const detail = state.details[id];
      if (item) item.feedback = body.feedback ?? null;
      if (detail) detail.feedback = body.feedback ?? null;
      return jsonResponse({
        assessment_id: id,
        feedback: body.feedback ?? null,
        training_policy: 'stored_only_never_auto_trained',
      });
    }
    if (method === 'GET' && url.pathname === '/admin/sim-results') {
      return jsonResponse(SIM_RESULTS);
    }
    if (method === 'GET' && url.pathname === '/admin/privacy') {
      return jsonResponse(state.privacy);
    }
    if (method === 'POST' && url.pathname === '/admin/privacy/purge') {
      state.privacy.last_purge = {
        last_purge_at: '2026-11-14T09:00:00+00:00',
        features_purged: 1,
        assessments_purged: 0,
      };
      state.privacy.record_counts.assessments_with_features = 0;
      return jsonResponse({
        purged_at: '2026-11-14T09:00:00+00:00',
        features_purged: 1,
        assessments_purged: 0,
      });
    }
    if (url.pathname.endsWith('/v1/nonce')) {
      return jsonResponse({ nonce: 'dashboard_nonce', expires_in_s: 120 });
    }
    return jsonResponse({ error: { message: `unhandled ${method} ${url.pathname}` } }, 404);
  });
  return mock as unknown as typeof fetch;
}

async function waitUntil(predicate: () => boolean, attempts = 40): Promise<void> {
  for (let i = 0; i < attempts; i += 1) {
    if (predicate()) {
      return;
    }
    await act(async () => {
      await Promise.resolve();
    });
  }
  throw new Error('timed out waiting for dashboard condition');
}

function setSelectValue(select: HTMLSelectElement, value: string): void {
  select.value = value;
  select.dispatchEvent(new Event('change', { bubbles: true }));
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
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

describe('Admin dashboard views (P9-03)', () => {
  it('renders overview metrics, score histogram threshold lines, session derived features, and simulator tiers', async () => {
    const state = createBackendState();
    const fetchImpl = createDashboardFetch(state);

    act(() => {
      root?.render(<AdminDashboardPage fetchImpl={fetchImpl} />);
    });

    await waitUntil(
      () =>
        container?.querySelector('[data-testid="metric-rpm"]')?.textContent?.includes('4.5') ===
        true,
    );

    expect(container?.querySelector('[data-testid="dashboard-overview"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="metric-rpm"]')?.textContent).toContain('4.5');
    expect(container?.querySelector('[data-testid="metric-rpm"]')?.textContent).toContain(
      'Total assessments: 2',
    );
    expect(container?.querySelector('[data-testid="metric-decisions"]')?.textContent).toContain(
      '1A',
    );
    expect(container?.querySelector('[data-testid="metric-decisions"]')?.textContent).toContain(
      '1D',
    );
    expect(container?.querySelector('[data-testid="metric-latency"]')?.textContent).toContain(
      '3.50',
    );
    expect(container?.querySelector('[data-testid="metric-latency"]')?.textContent).toContain(
      '5.10',
    );
    expect(container?.querySelector('[data-testid="metric-models"]')?.textContent).toContain(
      'lightgbm-v1',
    );
    expect(container?.querySelector('[data-testid="metric-models"]')?.textContent).toContain(
      'logistic_regression-v1',
    );
    expect(container?.querySelector('[data-testid="metric-models"]')?.textContent).toContain(
      'skipped (P8)',
    );

    const histogram = container?.querySelector('[data-testid="scores-histogram-svg"]');
    expect(histogram).not.toBeNull();
    expect(container?.querySelector('[data-testid="threshold-line-0"]')?.textContent).toContain(
      'allow < 0.15',
    );
    expect(container?.querySelector('[data-testid="threshold-line-1"]')?.textContent).toContain(
      'deny >= 0.70',
    );

    const sensitivity = container?.querySelector(
      '[data-testid="sensitivity-select"]',
    ) as HTMLSelectElement | null;
    expect(sensitivity).not.toBeNull();
    act(() => {
      if (sensitivity) setSelectValue(sensitivity, 'medium');
    });
    expect(container?.querySelector('[data-testid="threshold-line-0"]')?.textContent).toContain(
      'allow < 0.30',
    );
    expect(container?.querySelector('[data-testid="threshold-line-1"]')?.textContent).toContain(
      'deny >= 0.80',
    );

    expect(container?.querySelector('[data-testid="dashboard-session-detail"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="detail-assessment-id"]')?.textContent).toBe(
      ALLOW_ID,
    );
    expect(container?.querySelector('[data-testid="detail-rules-fired"]')?.textContent).toContain(
      'all environment & integrity checks passed',
    );
    const features =
      container?.querySelector('[data-testid="detail-top-features"]')?.textContent ?? '';
    expect(features).toContain('mouse:straightness_mean = 0.9120');
    expect(features).toContain('keyboard:dwell_std = 18.4000');
    expect(features).not.toContain('points');
    expect(features).not.toContain('keydown');
    expect(features).not.toMatch(/x\s*[:=]/i);

    const denyRow = container?.querySelector(
      `[data-testid="assessment-row-${DENY_ID}"]`,
    ) as HTMLTableRowElement | null;
    await act(async () => {
      denyRow?.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    await waitUntil(
      () =>
        container?.querySelector('[data-testid="detail-assessment-id"]')?.textContent === DENY_ID,
    );
    expect(container?.querySelector('[data-testid="detail-rules-fired"]')?.textContent).toContain(
      'R02_WEBDRIVER',
    );
    expect(
      container?.querySelector('[data-testid="session-inspector-pane"]')?.textContent,
    ).toContain('DENY · band=high');

    expect(
      container?.querySelector('[data-testid="dashboard-sim-results"]')?.textContent,
    ).toContain('No model, feature, or threshold was tuned');
    const simTable =
      container?.querySelector('[data-testid="sim-results-table"]')?.textContent ?? '';
    expect(simTable).toContain('tier1');
    expect(simTable).toContain('tier4');
    expect(simTable).toContain('100.0%');
    expect(container?.querySelector('[data-testid="sim-results-chart-svg"]')).not.toBeNull();
  });

  it('marks fp/fn feedback and triggers a privacy retention purge', async () => {
    const state = createBackendState();
    const fetchImpl = createDashboardFetch(state);

    act(() => {
      root?.render(<AdminDashboardPage fetchImpl={fetchImpl} />);
    });
    await waitUntil(() => container?.querySelector('[data-testid="mark-fp-btn"]') !== null);

    expect(container?.querySelector('[data-testid="feedback-queue-list"]')).toBeNull();
    expect(container?.querySelector('[data-testid="dashboard-feedback"]')?.textContent).toContain(
      'FP: 0',
    );
    expect(container?.querySelector('[data-testid="privacy-feature-ttl"]')?.textContent).toContain(
      'Enabled (TTL: 7d)',
    );
    expect(
      container?.querySelector('[data-testid="privacy-record-counts"]')?.textContent,
    ).toContain('Assessments: 2 (features: 1)');
    expect(container?.querySelector('[data-testid="privacy-last-purge"]')?.textContent).toContain(
      'Not yet run',
    );

    await act(async () => {
      (
        container?.querySelector('[data-testid="mark-fp-btn"]') as HTMLButtonElement | null
      )?.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    await waitUntil(() => container?.querySelector('[data-testid="feedback-queue-list"]') !== null);

    expect(container?.querySelector('[data-testid="admin-status-notice"]')?.textContent).toContain(
      'as FP',
    );
    expect(container?.querySelector('[data-testid="dashboard-feedback"]')?.textContent).toContain(
      'FP: 1',
    );
    expect(container?.querySelector('[data-testid="feedback-queue-list"]')?.textContent).toContain(
      'FP',
    );
    expect(container?.querySelector('[data-testid="clear-feedback-btn"]')).not.toBeNull();

    await act(async () => {
      (
        container?.querySelector('[data-testid="mark-fn-btn"]') as HTMLButtonElement | null
      )?.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    await waitUntil(
      () =>
        container
          ?.querySelector('[data-testid="dashboard-feedback"]')
          ?.textContent?.includes('FN: 1') === true,
    );
    expect(container?.querySelector('[data-testid="admin-status-notice"]')?.textContent).toContain(
      'as FN',
    );
    expect(container?.querySelector('[data-testid="feedback-queue-list"]')?.textContent).toContain(
      'FN',
    );

    await act(async () => {
      (
        container?.querySelector('[data-testid="run-purge-btn"]') as HTMLButtonElement | null
      )?.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    await waitUntil(
      () =>
        container
          ?.querySelector('[data-testid="admin-status-notice"]')
          ?.textContent?.includes('Retention purge') === true,
    );
    expect(container?.querySelector('[data-testid="admin-status-notice"]')?.textContent).toContain(
      '1 feature blob(s)',
    );
    expect(container?.querySelector('[data-testid="privacy-last-purge"]')?.textContent).toContain(
      '2026-11-14T09:00:00',
    );
    expect(container?.querySelector('[data-testid="privacy-last-purge"]')?.textContent).toContain(
      '1F/0A',
    );
    expect(
      container?.querySelector('[data-testid="privacy-record-counts"]')?.textContent,
    ).toContain('Assessments: 2 (features: 0)');
  });

  it('surfaces an error banner when the admin API rejects the key', async () => {
    const failingFetch = vi.fn(async () =>
      jsonResponse({ error: { message: 'unauthorized_admin' } }, 401),
    ) as unknown as typeof fetch;

    act(() => {
      root?.render(<AdminDashboardPage initialApiKey="wrong-key" fetchImpl={failingFetch} />);
    });

    await waitUntil(() => container?.querySelector('[data-testid="admin-error-banner"]') !== null);
    expect(container?.querySelector('[data-testid="admin-error-banner"]')?.textContent).toContain(
      'unauthorized_admin',
    );
  });
});

describe('Admin dashboard E2E smoke (P9-03)', () => {
  it('loads dashboard data from the backend mock when opened from the portal shell', async () => {
    const state = createBackendState();
    globalThis.fetch = createDashboardFetch(state);

    act(() => {
      root?.render(<App initialPage="admin" />);
    });

    await waitUntil(
      () => container?.querySelector('[data-testid="page-admin-dashboard"]') !== null,
    );
    await waitUntil(
      () =>
        container?.querySelector('[data-testid="metric-rpm"]')?.textContent?.includes('4.5') ===
        true,
    );

    expect(
      container?.querySelector('[data-testid="nav-admin"]')?.getAttribute('aria-current'),
    ).toBe('page');
    expect(container?.querySelector('[data-testid="dashboard-overview"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="dashboard-scores"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="dashboard-session-detail"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="dashboard-sim-results"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="dashboard-feedback"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="dashboard-privacy"]')).not.toBeNull();
    expect(container?.querySelector('[data-testid="detail-top-features"]')?.textContent).toContain(
      'mouse:straightness_mean',
    );

    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    const adminUrls = fetchMock.mock.calls
      .map((call) => String(call[0]))
      .filter((url) => url.includes('/admin/'));
    expect(adminUrls.some((url) => url.includes('/admin/overview'))).toBe(true);
    expect(adminUrls.some((url) => url.includes('/admin/scores'))).toBe(true);
    expect(adminUrls.some((url) => url.includes('/admin/assessments'))).toBe(true);
    expect(adminUrls.some((url) => url.includes('/admin/feedback'))).toBe(true);
    expect(adminUrls.some((url) => url.includes('/admin/sim-results'))).toBe(true);
    expect(adminUrls.some((url) => url.includes('/admin/privacy'))).toBe(true);
  });
});

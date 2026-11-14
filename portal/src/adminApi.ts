/**
 * Typed client for the Phase 9 `/admin/*` backend endpoints (P9-01, P9-02).
 */

export interface AdminOverviewData {
  total_assessments: number;
  requests_last_1m: number;
  requests_per_minute: number;
  window_minutes: number;
  decisions: {
    allow: number;
    challenge: number;
    deny: number;
  };
  decision_rates: {
    allow: number;
    challenge: number;
    deny: number;
  };
  latency_ms: {
    mean: number;
    p50: number;
    p95: number;
  };
  degraded_count: number;
  protection_mode: string;
  model_versions: {
    mouse: string | null;
    keyboard: string | null;
    touch: string | null;
    fusion: string | null;
  };
  portal_stats?: Record<string, unknown>;
  auth_note: string;
}

export interface ScoreHistogramBin {
  bin_index: number;
  bin_start: number;
  bin_end: number;
  label: string;
  count: number;
  allow: number;
  challenge: number;
  deny: number;
}

export interface AdminScoresData {
  total_scored: number;
  action_filter: string | null;
  bins: ScoreHistogramBin[];
  band_cutoffs: {
    low: number;
    medium: number;
  };
  thresholds: Record<
    string,
    {
      allow_below: number;
      deny_at_or_above: number;
    }
  >;
  actions: Record<string, string>;
}

export interface AssessmentSummaryItem {
  id: string;
  ts: string | null;
  session_hash: string;
  action: string;
  device_class: string | null;
  score: number;
  band: 'low' | 'medium' | 'high';
  decision: 'allow' | 'challenge' | 'deny';
  rules_fired: string[];
  top_factors: string[];
  model_versions: Record<string, string | null>;
  latency_ms: number | null;
  degraded: boolean;
  feedback: 'fp' | 'fn' | null;
  has_features: boolean;
}

export interface AssessmentDetailData extends AssessmentSummaryItem {
  features: Record<string, number> | null;
  features_expires_at: string | null;
  top_contributing_features: Array<{
    feature: string;
    value: number | null;
  }>;
  challenges: Array<{
    id: string;
    type: string;
    issued_at: string | null;
    completed_at: string | null;
    outcome: string | null;
  }>;
  privacy_note: string;
}

export interface AdminAssessmentsListData {
  total: number;
  limit: number;
  offset: number;
  items: AssessmentSummaryItem[];
}

export interface AdminFeedbackData {
  total: number;
  fp_count: number;
  fn_count: number;
  training_policy: string;
  note: string;
  items: AssessmentSummaryItem[];
}

export interface SimTierSummary {
  protection_mode: string;
  tier: string;
  total: number;
  allowed: number;
  challenged: number;
  denied: number;
  blocked_at_api: number;
  allow_rate: number;
  caught_rate: number;
  mean_latency_ms: number;
}

export interface AdminSimResultsData {
  total_runs: number;
  by_mode: Record<string, Record<string, Omit<SimTierSummary, 'protection_mode' | 'tier'>>>;
  tiers: SimTierSummary[];
  disclaimer: string;
}

export interface AdminPrivacyData {
  retention_settings: {
    store_features_in_db: boolean;
    feature_ttl_seconds: number;
    feature_ttl_days: number;
    assessment_ttl_seconds: number;
    assessment_ttl_days: number;
  };
  record_counts: {
    total_assessments: number;
    assessments_with_features: number;
    expired_feature_records: number;
    expired_assessment_records: number;
    total_challenges: number;
    buffered_writes: number;
  };
  last_purge: {
    last_purge_at: string | null;
    features_purged: number;
    assessments_purged: number;
  };
  guarantees: string[];
}

export const DEFAULT_ADMIN_API_KEY = 'dev-admin-key';

async function adminRequest<T>(
  path: string,
  apiKey: string,
  options: RequestInit = {},
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<T> {
  const headers: Record<string, string> = {
    'X-Admin-Key': apiKey,
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
  };
  const response = await fetchImpl(path, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers as Record<string, string> | undefined),
    },
  });
  if (!response.ok) {
    let errText = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { error?: { message?: string } };
      if (payload?.error?.message) {
        errText = payload.error.message;
      }
    } catch {
      // ignore parse failure
    }
    throw new Error(errText);
  }
  return (await response.json()) as T;
}

export async function fetchAdminOverview(
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<AdminOverviewData> {
  return adminRequest<AdminOverviewData>('/admin/overview', apiKey, {}, fetchImpl);
}

export async function fetchAdminScores(
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  actionFilter: string | null = null,
  bins: number = 10,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<AdminScoresData> {
  const query = new URLSearchParams({ bins: String(bins) });
  if (actionFilter) {
    query.set('action', actionFilter);
  }
  return adminRequest<AdminScoresData>(`/admin/scores?${query.toString()}`, apiKey, {}, fetchImpl);
}

export async function fetchAdminAssessments(
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  params: {
    decision?: string;
    band?: string;
    action?: string;
    limit?: number;
  } = {},
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<AdminAssessmentsListData> {
  const query = new URLSearchParams();
  if (params.decision) query.set('decision', params.decision);
  if (params.band) query.set('band', params.band);
  if (params.action) query.set('action', params.action);
  if (params.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return adminRequest<AdminAssessmentsListData>(
    `/admin/assessments${qs ? `?${qs}` : ''}`,
    apiKey,
    {},
    fetchImpl,
  );
}

export async function fetchAdminAssessmentDetail(
  assessmentId: string,
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<AssessmentDetailData> {
  return adminRequest<AssessmentDetailData>(
    `/admin/assessments/${encodeURIComponent(assessmentId)}`,
    apiKey,
    {},
    fetchImpl,
  );
}

export async function fetchAdminFeedback(
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  feedbackFilter: 'fp' | 'fn' | null = null,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<AdminFeedbackData> {
  const qs = feedbackFilter ? `?feedback=${feedbackFilter}` : '';
  return adminRequest<AdminFeedbackData>(`/admin/feedback${qs}`, apiKey, {}, fetchImpl);
}

export async function submitAdminFeedback(
  assessmentId: string,
  feedback: 'fp' | 'fn' | null,
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<{
  assessment_id: string;
  feedback: 'fp' | 'fn' | null;
  training_policy: string;
}> {
  return adminRequest(
    '/admin/feedback',
    apiKey,
    {
      method: 'POST',
      body: JSON.stringify({ assessment_id: assessmentId, feedback }),
    },
    fetchImpl,
  );
}

export async function fetchAdminSimResults(
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<AdminSimResultsData> {
  return adminRequest<AdminSimResultsData>('/admin/sim-results', apiKey, {}, fetchImpl);
}

export async function fetchAdminPrivacy(
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<AdminPrivacyData> {
  return adminRequest<AdminPrivacyData>('/admin/privacy', apiKey, {}, fetchImpl);
}

export async function triggerAdminPrivacyPurge(
  apiKey: string = DEFAULT_ADMIN_API_KEY,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<{
  purged_at: string;
  features_purged: number;
  assessments_purged: number;
}> {
  return adminRequest('/admin/privacy/purge', apiKey, { method: 'POST' }, fetchImpl);
}

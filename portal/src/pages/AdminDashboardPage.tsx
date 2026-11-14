/**
 * Phase 9 Admin Dashboard (`P9-02`) styled strictly with `supabase/DESIGN.md`.
 *
 * Implements the 6 required operational views:
 *  1. Overview: requests/min, allow/challenge/deny split, latency (mean/p50/p95), model versions.
 *  2. Score distribution histogram with policy threshold reference lines.
 *  3. Session detail: decision, band, rules fired, top contributing features (derived values only,
 *     no raw traces), challenge history.
 *  4. Simulator results per tier (from `/admin/sim-results` / `sim_runs.jsonl`).
 *  5. Feedback queue: mark "false positive / false negative" (`fp` / `fn`), stored only and never
 *     auto-used for training.
 *  6. Privacy panel: retention settings, record counts, last purge, and manual purge trigger.
 */
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import {
  DEFAULT_ADMIN_API_KEY,
  fetchAdminAssessmentDetail,
  fetchAdminAssessments,
  fetchAdminFeedback,
  fetchAdminOverview,
  fetchAdminPrivacy,
  fetchAdminScores,
  fetchAdminSimResults,
  submitAdminFeedback,
  triggerAdminPrivacyPurge,
  type AdminAssessmentsListData,
  type AdminFeedbackData,
  type AdminOverviewData,
  type AdminPrivacyData,
  type AdminScoresData,
  type AdminSimResultsData,
  type AssessmentDetailData,
} from '../adminApi.js';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from '../dashboard/RechartsCompat.js';
import {
  SUPABASE_COLORS,
  SUPABASE_COMPONENTS,
  SUPABASE_FONTS,
  SUPABASE_RADII,
  SUPABASE_TYPOGRAPHY,
} from '../designTokens.js';

export interface AdminDashboardPageProps {
  initialApiKey?: string;
  fetchImpl?: typeof fetch;
}

const FALLBACK_OVERVIEW: AdminOverviewData = {
  total_assessments: 0,
  requests_last_1m: 0,
  requests_per_minute: 0,
  window_minutes: 5,
  decisions: { allow: 0, challenge: 0, deny: 0 },
  decision_rates: { allow: 0, challenge: 0, deny: 0 },
  latency_ms: { mean: 0, p50: 0, p95: 0 },
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

const FALLBACK_SCORES: AdminScoresData = {
  total_scored: 0,
  action_filter: null,
  bins: Array.from({ length: 10 }, (_, idx) => ({
    bin_index: idx,
    bin_start: Number((idx * 0.1).toFixed(2)),
    bin_end: Number(((idx + 1) * 0.1).toFixed(2)),
    label: `${(idx * 0.1).toFixed(1)}–${((idx + 1) * 0.1).toFixed(1)}`,
    count: 0,
    allow: 0,
    challenge: 0,
    deny: 0,
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

export function AdminDashboardPage({
  initialApiKey = DEFAULT_ADMIN_API_KEY,
  fetchImpl = globalThis.fetch,
}: AdminDashboardPageProps = {}): ReactNode {
  const [apiKey, setApiKey] = useState<string>(initialApiKey);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  const [overview, setOverview] = useState<AdminOverviewData>(FALLBACK_OVERVIEW);
  const [scores, setScores] = useState<AdminScoresData>(FALLBACK_SCORES);
  const [selectedSensitivity, setSelectedSensitivity] = useState<'high' | 'medium' | 'low'>('high');
  const [assessments, setAssessments] = useState<AdminAssessmentsListData>({
    total: 0,
    limit: 25,
    offset: 0,
    items: [],
  });
  const [decisionFilter, setDecisionFilter] = useState<string>('');
  const [selectedDetail, setSelectedDetail] = useState<AssessmentDetailData | null>(null);
  const [feedbackData, setFeedbackData] = useState<AdminFeedbackData>({
    total: 0,
    fp_count: 0,
    fn_count: 0,
    training_policy: 'stored_only_never_auto_trained',
    note: 'Analyst feedback is stored for offline review only and never auto-used for training.',
    items: [],
  });
  const [simResults, setSimResults] = useState<AdminSimResultsData>({
    total_runs: 0,
    by_mode: {},
    tiers: [],
    disclaimer: 'No model, feature, or threshold was tuned on the Phase 7 simulator.',
  });
  const [privacyData, setPrivacyData] = useState<AdminPrivacyData>({
    retention_settings: {
      store_features_in_db: false,
      feature_ttl_seconds: 604800,
      feature_ttl_days: 7,
      assessment_ttl_seconds: 2592000,
      assessment_ttl_days: 30,
    },
    record_counts: {
      total_assessments: 0,
      assessments_with_features: 0,
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
  });

  const loadAll = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [ov, sc, asList, fb, sim, priv] = await Promise.all([
        fetchAdminOverview(apiKey, fetchImpl),
        fetchAdminScores(apiKey, null, 10, fetchImpl),
        fetchAdminAssessments(
          apiKey,
          { decision: decisionFilter || undefined, limit: 25 },
          fetchImpl,
        ),
        fetchAdminFeedback(apiKey, null, fetchImpl),
        fetchAdminSimResults(apiKey, fetchImpl),
        fetchAdminPrivacy(apiKey, fetchImpl),
      ]);
      setOverview(ov);
      setScores(sc);
      setAssessments(asList);
      setFeedbackData(fb);
      setSimResults(sim);
      setPrivacyData(priv);

      const firstItem = asList.items[0];
      if (firstItem) {
        const targetId = selectedDetail?.id ?? firstItem.id;
        try {
          const detail = await fetchAdminAssessmentDetail(targetId, apiKey, fetchImpl);
          setSelectedDetail(detail);
        } catch {
          const fallbackDetail = await fetchAdminAssessmentDetail(firstItem.id, apiKey, fetchImpl);
          setSelectedDetail(fallbackDetail);
        }
      } else {
        setSelectedDetail(null);
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Unable to load admin dashboard data.');
    } finally {
      setLoading(false);
    }
  }, [apiKey, decisionFilter, fetchImpl, selectedDetail?.id]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const handleSelectAssessment = async (id: string): Promise<void> => {
    try {
      const detail = await fetchAdminAssessmentDetail(id, apiKey, fetchImpl);
      setSelectedDetail(detail);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to load assessment detail.');
    }
  };

  const handleMarkFeedback = async (
    assessmentId: string,
    feedback: 'fp' | 'fn' | null,
  ): Promise<void> => {
    try {
      await submitAdminFeedback(assessmentId, feedback, apiKey, fetchImpl);
      setStatusNotice(
        feedback
          ? `Marked assessment ${assessmentId.slice(0, 8)} as ${feedback.toUpperCase()} (stored only, never auto-trained).`
          : `Cleared feedback on assessment ${assessmentId.slice(0, 8)}.`,
      );
      await loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to update feedback.');
    }
  };

  const handlePurgeNow = async (): Promise<void> => {
    try {
      const res = await triggerAdminPrivacyPurge(apiKey, fetchImpl);
      setStatusNotice(
        `Retention purge completed: ${res.features_purged} feature blob(s) and ${res.assessments_purged} assessment(s) purged.`,
      );
      await loadAll();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to trigger retention purge.');
    }
  };

  const activeThreshold = scores.thresholds[selectedSensitivity] ?? {
    allow_below: 0.15,
    deny_at_or_above: 0.7,
  };

  const passiveSimTiers = simResults.tiers.filter((t) => t.protection_mode === 'passive');

  return (
    <div
      data-testid="page-admin-dashboard"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        fontFamily: SUPABASE_FONTS.sans,
        color: SUPABASE_COLORS.ink,
      }}
    >
      {/* Top Header & API Key Bar */}
      <section
        aria-labelledby="admin-dashboard-heading"
        style={{
          ...SUPABASE_COMPONENTS.cardFeatureLight,
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={SUPABASE_COMPONENTS.pillTagGreen}>PHASE 9 TELEMETRY</span>
              <span
                style={{
                  ...SUPABASE_COMPONENTS.pillTagSoft,
                  fontFamily: SUPABASE_FONTS.mono,
                }}
              >
                mode: {overview.protection_mode}
              </span>
            </div>
            <h2
              id="admin-dashboard-heading"
              style={{
                ...SUPABASE_TYPOGRAPHY.displayMd,
                margin: 0,
              }}
            >
              Operational BotGuard Dashboard
            </h2>
            <p style={{ ...SUPABASE_TYPOGRAPHY.caption, margin: '4px 0 0' }}>
              {overview.auth_note}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <label
              htmlFor="admin-api-key-input"
              style={{ ...SUPABASE_TYPOGRAPHY.caption, fontWeight: 500 }}
            >
              Admin Key:
            </label>
            <input
              id="admin-api-key-input"
              data-testid="admin-api-key-input"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              style={{ ...SUPABASE_COMPONENTS.textInput, width: '160px' }}
            />
            <button
              type="button"
              data-testid="admin-refresh-btn"
              onClick={() => void loadAll()}
              style={SUPABASE_COMPONENTS.buttonPrimaryGreen}
            >
              {loading ? 'Refreshing…' : 'Refresh Telemetry'}
            </button>
          </div>
        </div>

        {errorMsg && (
          <div
            role="alert"
            data-testid="admin-error-banner"
            style={{
              padding: '10px 14px',
              borderRadius: SUPABASE_RADII.sm,
              border: `1px solid ${SUPABASE_COLORS.accentCrimson}`,
              backgroundColor: SUPABASE_COLORS.canvasSoft,
              color: SUPABASE_COLORS.accentCrimson,
              fontSize: '13px',
            }}
          >
            {errorMsg}
          </div>
        )}

        {statusNotice && (
          <div
            role="status"
            data-testid="admin-status-notice"
            style={{
              padding: '10px 14px',
              borderRadius: SUPABASE_RADII.sm,
              border: `1px solid ${SUPABASE_COLORS.primaryDeep}`,
              backgroundColor: SUPABASE_COLORS.canvasSoft,
              color: SUPABASE_COLORS.ink,
              fontSize: '13px',
            }}
          >
            {statusNotice}
          </div>
        )}
      </section>

      {/* 1. OVERVIEW VIEW */}
      <section
        aria-labelledby="view-overview-heading"
        data-testid="dashboard-overview"
        style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}
      >
        <h3 id="view-overview-heading" style={{ ...SUPABASE_TYPOGRAPHY.headingLg, margin: 0 }}>
          1. System Overview & Active Models
        </h3>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '16px',
          }}
        >
          {/* RPM Card */}
          <div style={SUPABASE_COMPONENTS.cardFeatureLight} data-testid="metric-rpm">
            <div style={SUPABASE_TYPOGRAPHY.caption}>Requests / Min (5m window)</div>
            <div style={{ ...SUPABASE_TYPOGRAPHY.displayLg, marginTop: '6px' }}>
              {overview.requests_per_minute.toFixed(1)}
            </div>
            <div
              style={{
                ...SUPABASE_TYPOGRAPHY.micro,
                color: SUPABASE_COLORS.inkMute,
                marginTop: '6px',
              }}
            >
              Total assessments: <strong>{overview.total_assessments}</strong> · Last 1m:{' '}
              <strong>{overview.requests_last_1m}</strong>
            </div>
          </div>

          {/* Decision Split Card */}
          <div style={SUPABASE_COMPONENTS.cardFeatureLight} data-testid="metric-decisions">
            <div style={SUPABASE_TYPOGRAPHY.caption}>Allow / Challenge / Deny Split</div>
            <div
              style={{
                display: 'flex',
                gap: '12px',
                alignItems: 'baseline',
                marginTop: '6px',
                fontFamily: SUPABASE_FONTS.mono,
                fontSize: '20px',
                fontWeight: 500,
              }}
            >
              <span style={{ color: SUPABASE_COLORS.primaryDeep }}>
                {overview.decisions.allow}A
              </span>
              <span style={{ color: SUPABASE_COLORS.ink }}>{overview.decisions.challenge}C</span>
              <span style={{ color: SUPABASE_COLORS.accentCrimson }}>
                {overview.decisions.deny}D
              </span>
            </div>
            <div
              style={{
                ...SUPABASE_TYPOGRAPHY.micro,
                color: SUPABASE_COLORS.inkMute,
                marginTop: '6px',
              }}
            >
              Allow {(overview.decision_rates.allow * 100).toFixed(1)}% · Challenge{' '}
              {(overview.decision_rates.challenge * 100).toFixed(1)}% · Deny{' '}
              {(overview.decision_rates.deny * 100).toFixed(1)}%
            </div>
          </div>

          {/* Latency Card */}
          <div style={SUPABASE_COMPONENTS.cardFeatureLight} data-testid="metric-latency">
            <div style={SUPABASE_TYPOGRAPHY.caption}>Scoring Latency (ms)</div>
            <div style={{ ...SUPABASE_TYPOGRAPHY.displayLg, marginTop: '6px' }}>
              {overview.latency_ms.p50.toFixed(2)}
              <span style={{ fontSize: '14px', color: SUPABASE_COLORS.inkMute }}> ms p50</span>
            </div>
            <div
              style={{
                ...SUPABASE_TYPOGRAPHY.micro,
                color: SUPABASE_COLORS.inkMute,
                marginTop: '6px',
              }}
            >
              Mean: {overview.latency_ms.mean.toFixed(2)} ms · p95:{' '}
              <strong>{overview.latency_ms.p95.toFixed(2)} ms</strong>
            </div>
          </div>

          {/* Dark Featured Card: Model Versions (`card-feature-dark` from supabase/DESIGN.md) */}
          <div style={SUPABASE_COMPONENTS.cardFeatureDark} data-testid="metric-models">
            <div style={{ ...SUPABASE_TYPOGRAPHY.caption, color: SUPABASE_COLORS.inkFaint }}>
              Loaded ONNX Models
            </div>
            <div
              style={{
                marginTop: '10px',
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '6px',
                fontFamily: SUPABASE_FONTS.mono,
                fontSize: '12px',
              }}
            >
              <div>
                <span style={{ color: SUPABASE_COLORS.inkMute2 }}>mouse: </span>
                <span style={{ color: SUPABASE_COLORS.primary }}>
                  {overview.model_versions.mouse ?? 'none'}
                </span>
              </div>
              <div>
                <span style={{ color: SUPABASE_COLORS.inkMute2 }}>keyboard: </span>
                <span style={{ color: SUPABASE_COLORS.primary }}>
                  {overview.model_versions.keyboard ?? 'none'}
                </span>
              </div>
              <div>
                <span style={{ color: SUPABASE_COLORS.inkMute2 }}>fusion: </span>
                <span style={{ color: SUPABASE_COLORS.onDark }}>
                  {overview.model_versions.fusion ?? 'none'}
                </span>
              </div>
              <div>
                <span style={{ color: SUPABASE_COLORS.inkMute2 }}>touch: </span>
                <span style={{ color: SUPABASE_COLORS.inkMute2 }}>
                  {overview.model_versions.touch ?? 'skipped (P8)'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. SCORE DISTRIBUTION HISTOGRAM WITH THRESHOLD LINES */}
      <section
        aria-labelledby="view-scores-heading"
        data-testid="dashboard-scores"
        style={SUPABASE_COMPONENTS.cardFeatureLight}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '16px',
          }}
        >
          <div>
            <h3 id="view-scores-heading" style={{ ...SUPABASE_TYPOGRAPHY.headingLg, margin: 0 }}>
              2. Risk Score Distribution & Policy Thresholds
            </h3>
            <p style={{ ...SUPABASE_TYPOGRAPHY.caption, margin: '4px 0 0' }}>
              Histogram across <code>[0.0, 1.0]</code> with vertical policy cutoffs (
              <code>allow_below={activeThreshold.allow_below.toFixed(2)}</code>,{' '}
              <code>deny_at_or_above={activeThreshold.deny_at_or_above.toFixed(2)}</code>).
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label htmlFor="sensitivity-select" style={SUPABASE_TYPOGRAPHY.caption}>
              Threshold class:
            </label>
            <select
              id="sensitivity-select"
              data-testid="sensitivity-select"
              value={selectedSensitivity}
              onChange={(e) => setSelectedSensitivity(e.target.value as 'high' | 'medium' | 'low')}
              style={SUPABASE_COMPONENTS.textInput}
            >
              <option value="high">high (otp_request, details_update)</option>
              <option value="medium">medium (centre_search, login)</option>
              <option value="low">low (page_view)</option>
            </select>
          </div>
        </div>

        <ResponsiveContainer height={250}>
          <BarChart
            data={scores.bins as unknown as ReadonlyArray<Record<string, unknown>>}
            ariaLabel="Risk score distribution histogram with threshold lines"
            testId="scores-histogram-svg"
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Bar dataKey="allow" name="Allow" stackId="decisions" fill={SUPABASE_COLORS.primary} />
            <Bar
              dataKey="challenge"
              name="Challenge"
              stackId="decisions"
              fill={SUPABASE_COLORS.accentYellow}
            />
            <Bar
              dataKey="deny"
              name="Deny"
              stackId="decisions"
              fill={SUPABASE_COLORS.accentCrimson}
            />
            <ReferenceLine
              x={activeThreshold.allow_below}
              label={`allow < ${activeThreshold.allow_below.toFixed(2)}`}
              stroke={SUPABASE_COLORS.primaryDeep}
            />
            <ReferenceLine
              x={activeThreshold.deny_at_or_above}
              label={`deny >= ${activeThreshold.deny_at_or_above.toFixed(2)}`}
              stroke={SUPABASE_COLORS.accentCrimson}
            />
          </BarChart>
        </ResponsiveContainer>
      </section>

      {/* 3. SESSION DETAIL & RECENT ASSESSMENTS */}
      <section
        aria-labelledby="view-session-detail-heading"
        data-testid="dashboard-session-detail"
        style={SUPABASE_COMPONENTS.cardFeatureLight}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '16px',
          }}
        >
          <div>
            <h3
              id="view-session-detail-heading"
              style={{ ...SUPABASE_TYPOGRAPHY.headingLg, margin: 0 }}
            >
              3. Session Assessments & Derived Feature Inspector
            </h3>
            <p style={{ ...SUPABASE_TYPOGRAPHY.caption, margin: '4px 0 0' }}>
              Inspect per-session decision, risk band, fired rules, and top contributing derived
              features (raw coordinate and keystroke traces are never stored).
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label htmlFor="decision-filter-select" style={SUPABASE_TYPOGRAPHY.caption}>
              Filter decision:
            </label>
            <select
              id="decision-filter-select"
              data-testid="decision-filter-select"
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
              style={SUPABASE_COMPONENTS.textInput}
            >
              <option value="">All decisions ({assessments.total})</option>
              <option value="allow">allow</option>
              <option value="challenge">challenge</option>
              <option value="deny">deny</option>
            </select>
          </div>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
            gap: '20px',
          }}
        >
          {/* Left: Assessments Table */}
          <div style={{ overflowX: 'auto' }}>
            <table
              data-testid="assessments-table"
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '13px',
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: `1px solid ${SUPABASE_COLORS.hairline}`,
                    textAlign: 'left',
                    color: SUPABASE_COLORS.inkMute,
                  }}
                >
                  <th style={{ padding: '8px' }}>ID</th>
                  <th style={{ padding: '8px' }}>Action</th>
                  <th style={{ padding: '8px' }}>Decision</th>
                  <th style={{ padding: '8px' }}>Score</th>
                  <th style={{ padding: '8px' }}>Rules</th>
                  <th style={{ padding: '8px' }}>Feedback</th>
                </tr>
              </thead>
              <tbody>
                {assessments.items.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      style={{
                        padding: '16px 8px',
                        color: SUPABASE_COLORS.inkMute,
                        textAlign: 'center',
                      }}
                    >
                      No assessments recorded yet. Run a portal action or simulator session.
                    </td>
                  </tr>
                ) : (
                  assessments.items.map((item) => {
                    const isSelected = selectedDetail?.id === item.id;
                    return (
                      <tr
                        key={item.id}
                        data-testid={`assessment-row-${item.id}`}
                        onClick={() => void handleSelectAssessment(item.id)}
                        style={{
                          borderBottom: `1px solid ${SUPABASE_COLORS.hairlineCool}`,
                          backgroundColor: isSelected
                            ? SUPABASE_COLORS.canvasSoft
                            : SUPABASE_COLORS.canvas,
                          cursor: 'pointer',
                        }}
                      >
                        <td
                          style={{
                            padding: '8px',
                            fontFamily: SUPABASE_FONTS.mono,
                            fontSize: '12px',
                          }}
                        >
                          {item.id.slice(0, 8)}
                        </td>
                        <td style={{ padding: '8px' }}>{item.action}</td>
                        <td style={{ padding: '8px' }}>
                          <span
                            style={
                              item.decision === 'allow'
                                ? SUPABASE_COMPONENTS.pillTagGreen
                                : SUPABASE_COMPONENTS.pillTagSoft
                            }
                          >
                            {item.decision} ({item.band})
                          </span>
                        </td>
                        <td style={{ padding: '8px', fontFamily: SUPABASE_FONTS.mono }}>
                          {item.score.toFixed(3)}
                        </td>
                        <td style={{ padding: '8px', fontFamily: SUPABASE_FONTS.mono }}>
                          {item.rules_fired.length}
                        </td>
                        <td style={{ padding: '8px' }}>
                          {item.feedback ? item.feedback.toUpperCase() : '—'}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Right: Composited Dark Inspector (`canvas-night` from supabase/DESIGN.md) */}
          <div data-testid="session-inspector-pane" style={SUPABASE_COMPONENTS.cardFeatureDark}>
            {selectedDetail ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '8px',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '12px', color: SUPABASE_COLORS.inkMute2 }}>
                      Session Assessment ID
                    </div>
                    <div
                      data-testid="detail-assessment-id"
                      style={{ fontFamily: SUPABASE_FONTS.mono, fontSize: '14px' }}
                    >
                      {selectedDetail.id}
                    </div>
                  </div>
                  <span style={SUPABASE_COMPONENTS.pillTagGreen}>
                    {selectedDetail.decision.toUpperCase()} · band={selectedDetail.band} · score=
                    {selectedDetail.score.toFixed(3)}
                  </span>
                </div>

                <div style={{ fontSize: '13px', color: SUPABASE_COLORS.inkFaint }}>
                  Action: <code>{selectedDetail.action}</code> · Device:{' '}
                  <code>{selectedDetail.device_class ?? 'desktop'}</code> · Latency:{' '}
                  <code>{selectedDetail.latency_ms?.toFixed(2) ?? '0.00'} ms</code>
                </div>

                <div>
                  <div
                    style={{
                      fontSize: '12px',
                      color: SUPABASE_COLORS.inkMute2,
                      marginBottom: '4px',
                    }}
                  >
                    Rules Fired ({selectedDetail.rules_fired.length}):
                  </div>
                  <div
                    data-testid="detail-rules-fired"
                    style={{
                      fontFamily: SUPABASE_FONTS.mono,
                      fontSize: '12px',
                      color:
                        selectedDetail.rules_fired.length > 0
                          ? SUPABASE_COLORS.accentYellow
                          : SUPABASE_COLORS.primary,
                    }}
                  >
                    {selectedDetail.rules_fired.length > 0
                      ? selectedDetail.rules_fired.join(', ')
                      : 'None (all environment & integrity checks passed)'}
                  </div>
                </div>

                <div>
                  <div
                    style={{
                      fontSize: '12px',
                      color: SUPABASE_COLORS.inkMute2,
                      marginBottom: '4px',
                    }}
                  >
                    Top Contributing Derived Features (no raw traces):
                  </div>
                  <ul
                    data-testid="detail-top-features"
                    style={{
                      margin: 0,
                      paddingLeft: '18px',
                      fontFamily: SUPABASE_FONTS.mono,
                      fontSize: '12px',
                    }}
                  >
                    {selectedDetail.top_contributing_features.length === 0 ? (
                      <li>No behavioural feature factors recorded</li>
                    ) : (
                      selectedDetail.top_contributing_features.map((f) => (
                        <li key={f.feature}>
                          {f.feature}
                          {f.value !== null && f.value !== undefined
                            ? ` = ${Number(f.value).toFixed(4)}`
                            : ''}
                        </li>
                      ))
                    )}
                  </ul>
                </div>

                {selectedDetail.challenges[0] && (
                  <div style={{ fontSize: '12px', fontFamily: SUPABASE_FONTS.mono }}>
                    Step-up challenge: {selectedDetail.challenges[0].type} (outcome:{' '}
                    {selectedDetail.challenges[0].outcome ?? 'pending'})
                  </div>
                )}

                <div
                  style={{
                    display: 'flex',
                    gap: '8px',
                    flexWrap: 'wrap',
                    paddingTop: '8px',
                    borderTop: `1px solid ${SUPABASE_COLORS.inkSecondary}`,
                  }}
                >
                  <button
                    type="button"
                    data-testid="mark-fp-btn"
                    onClick={() => void handleMarkFeedback(selectedDetail.id, 'fp')}
                    style={SUPABASE_COMPONENTS.buttonPrimaryGreen}
                  >
                    Mark False Positive (FP)
                  </button>
                  <button
                    type="button"
                    data-testid="mark-fn-btn"
                    onClick={() => void handleMarkFeedback(selectedDetail.id, 'fn')}
                    style={SUPABASE_COMPONENTS.buttonSecondaryOutline}
                  >
                    Mark False Negative (FN)
                  </button>
                  {selectedDetail.feedback && (
                    <button
                      type="button"
                      data-testid="clear-feedback-btn"
                      onClick={() => void handleMarkFeedback(selectedDetail.id, null)}
                      style={SUPABASE_COMPONENTS.buttonOnDark}
                    >
                      Clear Feedback
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ color: SUPABASE_COLORS.inkMute2, fontSize: '14px' }}>
                Select an assessment row to inspect derived features and rule evaluations.
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 4. SIMULATOR RESULTS PER TIER */}
      <section
        aria-labelledby="view-sim-results-heading"
        data-testid="dashboard-sim-results"
        style={SUPABASE_COMPONENTS.cardFeatureLight}
      >
        <h3 id="view-sim-results-heading" style={{ ...SUPABASE_TYPOGRAPHY.headingLg, margin: 0 }}>
          4. Bot Simulator Results per Tier (<code>sim_runs.jsonl</code>)
        </h3>
        <p style={{ ...SUPABASE_TYPOGRAPHY.caption, margin: '4px 0 16px' }}>
          {simResults.disclaimer} Total recorded sessions: <strong>{simResults.total_runs}</strong>.
        </p>

        {passiveSimTiers.length > 0 && (
          <ResponsiveContainer height={220}>
            <BarChart
              data={passiveSimTiers as unknown as ReadonlyArray<Record<string, unknown>>}
              ariaLabel="Simulator outcomes by bot tier in passive mode"
              testId="sim-results-chart-svg"
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="tier" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="allowed" name="Allowed" stackId="sim" fill={SUPABASE_COLORS.primary} />
              <Bar
                dataKey="challenged"
                name="Challenged"
                stackId="sim"
                fill={SUPABASE_COLORS.accentYellow}
              />
              <Bar
                dataKey="denied"
                name="Denied"
                stackId="sim"
                fill={SUPABASE_COLORS.accentCrimson}
              />
              <Bar
                dataKey="blocked_at_api"
                name="Blocked at API (401)"
                stackId="sim"
                fill={SUPABASE_COLORS.accentViolet}
              />
            </BarChart>
          </ResponsiveContainer>
        )}

        <div style={{ overflowX: 'auto', marginTop: '16px' }}>
          <table
            data-testid="sim-results-table"
            style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: `1px solid ${SUPABASE_COLORS.hairline}`,
                  textAlign: 'left',
                  color: SUPABASE_COLORS.inkMute,
                }}
              >
                <th style={{ padding: '8px' }}>Mode</th>
                <th style={{ padding: '8px' }}>Tier</th>
                <th style={{ padding: '8px' }}>Total</th>
                <th style={{ padding: '8px' }}>Allowed</th>
                <th style={{ padding: '8px' }}>Challenged</th>
                <th style={{ padding: '8px' }}>Denied</th>
                <th style={{ padding: '8px' }}>Blocked at API</th>
                <th style={{ padding: '8px' }}>Caught Rate</th>
                <th style={{ padding: '8px' }}>Mean Latency</th>
              </tr>
            </thead>
            <tbody>
              {simResults.tiers.map((row) => (
                <tr
                  key={`${row.protection_mode}-${row.tier}`}
                  style={{ borderBottom: `1px solid ${SUPABASE_COLORS.hairlineCool}` }}
                >
                  <td style={{ padding: '8px', fontFamily: SUPABASE_FONTS.mono }}>
                    {row.protection_mode}
                  </td>
                  <td style={{ padding: '8px', fontFamily: SUPABASE_FONTS.mono }}>{row.tier}</td>
                  <td style={{ padding: '8px' }}>{row.total}</td>
                  <td style={{ padding: '8px' }}>{row.allowed}</td>
                  <td style={{ padding: '8px' }}>{row.challenged}</td>
                  <td style={{ padding: '8px' }}>{row.denied}</td>
                  <td style={{ padding: '8px' }}>{row.blocked_at_api}</td>
                  <td style={{ padding: '8px', fontFamily: SUPABASE_FONTS.mono }}>
                    {(row.caught_rate * 100).toFixed(1)}%
                  </td>
                  <td style={{ padding: '8px', fontFamily: SUPABASE_FONTS.mono }}>
                    {row.mean_latency_ms.toFixed(2)} ms
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. FEEDBACK QUEUE & 6. PRIVACY PANEL (2-column grid) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '20px',
        }}
      >
        {/* 5. Feedback Queue */}
        <section
          aria-labelledby="view-feedback-heading"
          data-testid="dashboard-feedback"
          style={SUPABASE_COMPONENTS.cardFeatureLight}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 id="view-feedback-heading" style={{ ...SUPABASE_TYPOGRAPHY.headingLg, margin: 0 }}>
              5. Analyst Feedback Queue
            </h3>
            <span style={SUPABASE_COMPONENTS.pillTagSoft}>
              FP: {feedbackData.fp_count} · FN: {feedbackData.fn_count}
            </span>
          </div>
          <p style={{ ...SUPABASE_TYPOGRAPHY.caption, margin: '6px 0 12px' }}>
            {feedbackData.note} (<code>{feedbackData.training_policy}</code>)
          </p>

          {feedbackData.items.length === 0 ? (
            <div style={{ ...SUPABASE_TYPOGRAPHY.caption, padding: '12px 0' }}>
              No assessments currently marked as FP or FN. Select a session above to flag it.
            </div>
          ) : (
            <ul
              data-testid="feedback-queue-list"
              style={{
                listStyle: 'none',
                margin: 0,
                padding: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              {feedbackData.items.map((item) => (
                <li
                  key={item.id}
                  style={{
                    padding: '10px 12px',
                    borderRadius: SUPABASE_RADII.sm,
                    border: `1px solid ${SUPABASE_COLORS.hairlineCool}`,
                    backgroundColor: SUPABASE_COLORS.canvasSoft,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '13px',
                  }}
                >
                  <div>
                    <code style={{ fontFamily: SUPABASE_FONTS.mono }}>{item.id.slice(0, 10)}</code>{' '}
                    · <strong>{item.feedback?.toUpperCase()}</strong> ({item.decision}, score=
                    {item.score.toFixed(2)})
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleMarkFeedback(item.id, null)}
                    style={{
                      ...SUPABASE_COMPONENTS.buttonSecondaryOutline,
                      padding: '4px 10px',
                      fontSize: '12px',
                    }}
                  >
                    Clear
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* 6. Privacy Panel */}
        <section
          aria-labelledby="view-privacy-heading"
          data-testid="dashboard-privacy"
          style={SUPABASE_COMPONENTS.cardFeatureLight}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '8px',
            }}
          >
            <h3 id="view-privacy-heading" style={{ ...SUPABASE_TYPOGRAPHY.headingLg, margin: 0 }}>
              6. Privacy & Retention Enforcement
            </h3>
            <button
              type="button"
              data-testid="run-purge-btn"
              onClick={() => void handlePurgeNow()}
              style={SUPABASE_COMPONENTS.buttonPrimaryGreen}
            >
              Run Retention Purge
            </button>
          </div>

          <div
            style={{
              marginTop: '12px',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '10px',
              fontSize: '13px',
            }}
          >
            <div
              style={{
                padding: '10px',
                borderRadius: SUPABASE_RADII.sm,
                backgroundColor: SUPABASE_COLORS.canvasSoft,
                border: `1px solid ${SUPABASE_COLORS.hairlineCool}`,
              }}
            >
              <div style={SUPABASE_TYPOGRAPHY.caption}>Feature Storage</div>
              <div style={{ fontWeight: 500, marginTop: '2px' }} data-testid="privacy-feature-ttl">
                {privacyData.retention_settings.store_features_in_db ? 'Enabled' : 'Disabled'} (TTL:{' '}
                {privacyData.retention_settings.feature_ttl_days}d)
              </div>
            </div>
            <div
              style={{
                padding: '10px',
                borderRadius: SUPABASE_RADII.sm,
                backgroundColor: SUPABASE_COLORS.canvasSoft,
                border: `1px solid ${SUPABASE_COLORS.hairlineCool}`,
              }}
            >
              <div style={SUPABASE_TYPOGRAPHY.caption}>Assessment Retention</div>
              <div style={{ fontWeight: 500, marginTop: '2px' }}>
                TTL: {privacyData.retention_settings.assessment_ttl_days}d
              </div>
            </div>
            <div
              style={{
                padding: '10px',
                borderRadius: SUPABASE_RADII.sm,
                backgroundColor: SUPABASE_COLORS.canvasSoft,
                border: `1px solid ${SUPABASE_COLORS.hairlineCool}`,
              }}
            >
              <div style={SUPABASE_TYPOGRAPHY.caption}>Record Counts</div>
              <div
                style={{ fontFamily: SUPABASE_FONTS.mono, fontSize: '12px', marginTop: '2px' }}
                data-testid="privacy-record-counts"
              >
                Assessments: {privacyData.record_counts.total_assessments} (features:{' '}
                {privacyData.record_counts.assessments_with_features}) · Challenges:{' '}
                {privacyData.record_counts.total_challenges}
              </div>
            </div>
            <div
              style={{
                padding: '10px',
                borderRadius: SUPABASE_RADII.sm,
                backgroundColor: SUPABASE_COLORS.canvasSoft,
                border: `1px solid ${SUPABASE_COLORS.hairlineCool}`,
              }}
            >
              <div style={SUPABASE_TYPOGRAPHY.caption}>Last Purge</div>
              <div
                style={{ fontFamily: SUPABASE_FONTS.mono, fontSize: '12px', marginTop: '2px' }}
                data-testid="privacy-last-purge"
              >
                {privacyData.last_purge.last_purge_at
                  ? `${privacyData.last_purge.last_purge_at.slice(0, 19)}Z (${privacyData.last_purge.features_purged}F/${privacyData.last_purge.assessments_purged}A)`
                  : 'Not yet run'}
              </div>
            </div>
          </div>

          <ul
            style={{
              margin: '12px 0 0',
              paddingLeft: '18px',
              fontSize: '12px',
              color: SUPABASE_COLORS.inkMute,
              lineHeight: 1.5,
            }}
          >
            {privacyData.guarantees.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

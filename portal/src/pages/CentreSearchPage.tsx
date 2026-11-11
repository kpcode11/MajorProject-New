/**
 * "Centre search" page (P7-02).
 *
 * Allows residents to search mock enrolment/update centres while protecting the search
 * API against automated scraping bots.
 */
import { useBotGuard } from '@botguard/sdk/react';
import { useState, type FormEvent, type ReactNode } from 'react';
import { callPortalEndpoint, type CentreRecord, type PortalApiResult } from '../api.js';

const DEFAULT_DEMO_CENTRES: ReadonlyArray<CentreRecord> = [
  {
    code: 'DEMO-BLR-01',
    name: 'Mock Citizen Seva Kendra — Indiranagar',
    district: 'Bengaluru Urban',
    services: ['New Enrolment', 'Demographic Update', 'Biometric Update'],
    hours: '09:30 – 17:30 (Mon–Sat)',
  },
  {
    code: 'DEMO-DEL-02',
    name: 'Mock Citizen Seva Kendra — Connaught Place',
    district: 'New Delhi',
    services: ['Demographic Update', 'Mobile Number Link'],
    hours: '10:00 – 18:00 (Mon–Fri)',
  },
  {
    code: 'DEMO-MUM-03',
    name: 'Mock Citizen Seva Kendra — Andheri West',
    district: 'Mumbai Suburban',
    services: ['New Enrolment', 'Demographic Update'],
    hours: '09:00 – 17:00 (Mon–Sat)',
  },
];

export function CentreSearchPage(): ReactNode {
  const { assessWithStepUp } = useBotGuard();
  const [query, setQuery] = useState('');
  const [serviceType, setServiceType] = useState('ALL');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<PortalApiResult<{ centres?: CentreRecord[] }> | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setValidationError('Please enter at least 2 characters (PIN code or city name).');
      return;
    }
    setValidationError(null);
    setSearching(true);
    try {
      const apiResult = await callPortalEndpoint<{ centres?: CentreRecord[] }>(
        '/portal-api/centres/search',
        {
          action: 'centre_search',
          service_type: serviceType,
          query_length: trimmed.length,
        },
        () => assessWithStepUp('centre_search'),
      );
      setResult(apiResult);
    } finally {
      setSearching(false);
    }
  };

  const centres: ReadonlyArray<CentreRecord> =
    result?.ok && Array.isArray(result.data?.centres) && result.data.centres.length > 0
      ? result.data.centres
      : result?.ok
        ? DEFAULT_DEMO_CENTRES
        : [];

  return (
    <section
      data-testid="page-centre-search"
      aria-labelledby="centre-search-heading"
      style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(15,23,42,0.05)',
      }}
    >
      <h2 id="centre-search-heading" style={{ marginTop: 0, fontSize: '20px', color: '#0f172a' }}>
        Centre search
      </h2>
      <p style={{ color: '#475569', fontSize: '14px', marginBottom: '20px' }}>
        Search mock enrolment and update centres by PIN code or district name.
      </p>

      <form
        onSubmit={(e) => void handleSubmit(e)}
        noValidate
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '12px',
          alignItems: 'flex-end',
          marginBottom: '16px',
        }}
      >
        <div style={{ flex: '1 1 240px' }}>
          <label
            htmlFor="centre-query"
            style={{ display: 'block', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}
          >
            PIN Code or District
          </label>
          <input
            id="centre-query"
            name="query"
            type="text"
            autoComplete="off"
            placeholder="e.g. 560001 or Bengaluru"
            data-testid="centre-query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              fontSize: '14px',
              borderRadius: '8px',
              border: '1px solid #94a3b8',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ flex: '0 1 220px' }}>
          <label
            htmlFor="centre-service"
            style={{ display: 'block', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}
          >
            Service Type
          </label>
          <select
            id="centre-service"
            name="serviceType"
            data-testid="centre-service-select"
            value={serviceType}
            onChange={(e) => setServiceType(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              fontSize: '14px',
              borderRadius: '8px',
              border: '1px solid #94a3b8',
              background: '#ffffff',
              boxSizing: 'border-box',
            }}
          >
            <option value="ALL">All Services</option>
            <option value="ENROLMENT">New Enrolment</option>
            <option value="DEMOGRAPHIC_UPDATE">Demographic Update</option>
            <option value="BIOMETRIC_UPDATE">Biometric Update</option>
          </select>
        </div>

        <button
          type="submit"
          data-testid="search-centres-btn"
          disabled={searching}
          style={{
            padding: '10px 20px',
            fontSize: '15px',
            fontWeight: 600,
            borderRadius: '8px',
            border: 'none',
            background: searching ? '#64748b' : '#0284c7',
            color: '#ffffff',
            cursor: searching ? 'wait' : 'pointer',
          }}
        >
          {searching ? 'Searching…' : 'Search Centres'}
        </button>
      </form>

      {validationError && (
        <p
          role="alert"
          data-testid="centre-validation-error"
          style={{ color: '#b91c1c', fontSize: '13px', marginTop: 0, marginBottom: '16px' }}
        >
          {validationError}
        </p>
      )}

      {result && (
        <div
          role="status"
          data-testid="centre-search-status"
          data-outcome={result.ok ? 'accepted' : 'rejected'}
          style={{
            marginBottom: '16px',
            padding: '12px 16px',
            borderRadius: '8px',
            border: `1px solid ${result.ok ? '#22c55e' : '#ef4444'}`,
            background: result.ok ? '#f0fdf4' : '#fef2f2',
            color: result.ok ? '#166534' : '#991b1b',
            fontSize: '14px',
          }}
        >
          <strong>{result.ok ? 'Search Verified: ' : 'Search Blocked: '}</strong>
          <span>{result.message}</span>
        </div>
      )}

      {centres.length > 0 && (
        <ul
          data-testid="centre-results"
          style={{
            listStyle: 'none',
            padding: 0,
            margin: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {centres.map((centre) => (
            <li
              key={centre.code}
              data-testid={`centre-item-${centre.code}`}
              style={{
                border: '1px solid #cbd5e1',
                borderRadius: '8px',
                padding: '14px 16px',
                background: '#f8fafc',
              }}
            >
              <div style={{ fontWeight: 700, fontSize: '15px', color: '#0f172a' }}>
                {centre.name}{' '}
                <span style={{ color: '#64748b', fontWeight: 500 }}>({centre.code})</span>
              </div>
              <div style={{ fontSize: '13px', color: '#334155', marginTop: '4px' }}>
                District: {centre.district} · Hours: {centre.hours}
              </div>
              <div style={{ fontSize: '12px', color: '#0369a1', marginTop: '4px' }}>
                Services: {centre.services.join(', ')}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

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
      className="portal-page-card"
    >
      <h2 id="centre-search-heading">Centre search</h2>
      <p className="portal-page-lead">
        Search mock enrolment and update centres by PIN code or district name.
      </p>

      <form onSubmit={(e) => void handleSubmit(e)} noValidate className="portal-form-inline">
        <div className="portal-field portal-field-flex">
          <label htmlFor="centre-query" className="portal-label">
            PIN Code or District
          </label>
          <input
            id="centre-query"
            name="query"
            type="text"
            autoComplete="off"
            placeholder="e.g. 560001 or Bengaluru"
            data-testid="centre-query-input"
            aria-invalid={validationError ? 'true' : undefined}
            aria-describedby={validationError ? 'centre-validation-error' : undefined}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="portal-input"
          />
        </div>

        <div className="portal-field portal-field-select">
          <label htmlFor="centre-service" className="portal-label">
            Service Type
          </label>
          <select
            id="centre-service"
            name="serviceType"
            data-testid="centre-service-select"
            value={serviceType}
            onChange={(e) => setServiceType(e.target.value)}
            className="portal-select"
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
          className="portal-button"
        >
          {searching ? 'Searching…' : 'Search Centres'}
        </button>
      </form>

      {validationError && (
        <p
          id="centre-validation-error"
          role="alert"
          data-testid="centre-validation-error"
          className="portal-validation"
        >
          {validationError}
        </p>
      )}

      {result && (
        <div
          role="status"
          data-testid="centre-search-status"
          data-outcome={result.ok ? 'accepted' : 'rejected'}
          className="portal-result"
        >
          <strong>{result.ok ? 'Search Verified: ' : 'Search Blocked: '}</strong>
          <span>{result.message}</span>
        </div>
      )}

      {centres.length > 0 && (
        <ul
          data-testid="centre-results"
          aria-label="Enrolment and update centres"
          className="portal-centres"
        >
          {centres.map((centre) => (
            <li
              key={centre.code}
              data-testid={`centre-item-${centre.code}`}
              className="portal-centre"
            >
              <div className="portal-centre-name">
                {centre.name} <span>({centre.code})</span>
              </div>
              <div className="portal-centre-meta">
                District: {centre.district} · Hours: {centre.hours}
              </div>
              <div className="portal-centre-services">Services: {centre.services.join(', ')}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

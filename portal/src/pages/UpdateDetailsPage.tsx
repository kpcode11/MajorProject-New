/**
 * "Update details" form page (P7-02).
 *
 * Provides a multi-field demographic update workflow that naturally produces mouse,
 * keyboard, focus, and scroll telemetry without ever sending raw typed strings to the backend.
 */
import { useBotGuard } from '@botguard/sdk/react';
import { useState, type FormEvent, type ReactNode } from 'react';
import { callPortalEndpoint, type PortalApiResult } from '../api.js';

export function UpdateDetailsPage(): ReactNode {
  const { assessWithStepUp } = useBotGuard();
  const [fullName, setFullName] = useState('');
  const [address, setAddress] = useState('');
  const [pincode, setPincode] = useState('');
  const [city, setCity] = useState('BENGALURU');
  const [language, setLanguage] = useState('EN');
  const [confirmed, setConfirmed] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<PortalApiResult | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fieldsUpdated: string[] = [];
    if (fullName.trim().length > 0) fieldsUpdated.push('name');
    if (address.trim().length > 0) fieldsUpdated.push('address');
    if (pincode.trim().length > 0) fieldsUpdated.push('pincode');

    if (fieldsUpdated.length === 0) {
      setValidationError('Please fill at least one demographic field to update.');
      return;
    }
    if (!confirmed) {
      setValidationError('Please confirm the synthetic demo declaration checkbox.');
      return;
    }

    setValidationError(null);
    setSubmitting(true);
    try {
      const apiResult = await callPortalEndpoint(
        '/portal-api/details/update',
        {
          action: 'details_update',
          fields_updated: fieldsUpdated,
          city_code: city,
          language_code: language,
          confirmed: true,
        },
        () => assessWithStepUp('details_update'),
      );
      setResult(apiResult);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section
      data-testid="page-update-details"
      aria-labelledby="update-details-heading"
      className="portal-page-card"
    >
      <h2 id="update-details-heading">Update details</h2>
      <p className="portal-page-lead">
        Update synthetic demographic details. Only field names and coarse selections are sent to the
        demo API; typed text stays in browser memory.
      </p>

      <form onSubmit={(e) => void handleSubmit(e)} noValidate className="portal-form">
        <div className="portal-field">
          <label htmlFor="detail-name" className="portal-label">
            Synthetic Resident Full Name
          </label>
          <input
            id="detail-name"
            name="fullName"
            type="text"
            autoComplete="off"
            placeholder="e.g. Aarav Demo Citizen"
            data-testid="detail-name-input"
            aria-describedby={validationError ? 'details-validation-error' : undefined}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="portal-input"
          />
        </div>

        <div className="portal-field">
          <label htmlFor="detail-address" className="portal-label">
            Synthetic Address Line
          </label>
          <input
            id="detail-address"
            name="address"
            type="text"
            autoComplete="off"
            placeholder="e.g. 42 Research Park Avenue"
            data-testid="detail-address-input"
            aria-describedby={validationError ? 'details-validation-error' : undefined}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="portal-input"
          />
        </div>

        <div className="portal-form-inline">
          <div className="portal-field portal-field-flex">
            <label htmlFor="detail-pincode" className="portal-label">
              PIN Code
            </label>
            <input
              id="detail-pincode"
              name="pincode"
              type="text"
              autoComplete="off"
              inputMode="numeric"
              placeholder="e.g. 560001"
              data-testid="detail-pincode-input"
              aria-describedby={validationError ? 'details-validation-error' : undefined}
              value={pincode}
              onChange={(e) => setPincode(e.target.value)}
              className="portal-input"
            />
          </div>

          <div className="portal-field portal-field-select">
            <label htmlFor="detail-city" className="portal-label">
              District / City
            </label>
            <select
              id="detail-city"
              name="city"
              data-testid="detail-city-select"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="portal-select"
            >
              <option value="BENGALURU">Bengaluru Urban</option>
              <option value="DELHI">New Delhi</option>
              <option value="MUMBAI">Mumbai Suburban</option>
              <option value="CHENNAI">Chennai</option>
              <option value="HYDERABAD">Hyderabad</option>
            </select>
          </div>
        </div>

        <div className="portal-field">
          <label htmlFor="detail-language" className="portal-label">
            Preferred Notification Language
          </label>
          <select
            id="detail-language"
            name="language"
            data-testid="detail-language-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="portal-select"
          >
            <option value="EN">English</option>
            <option value="HI">Hindi</option>
            <option value="KN">Kannada</option>
            <option value="TA">Tamil</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
          <input
            id="detail-confirm"
            name="confirmed"
            type="checkbox"
            data-testid="detail-confirm-checkbox"
            aria-describedby={validationError ? 'details-validation-error' : undefined}
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          <label htmlFor="detail-confirm" className="portal-label">
            I confirm these entries are synthetic demonstration values only.
          </label>
        </div>

        {validationError && (
          <p
            id="details-validation-error"
            role="alert"
            data-testid="details-validation-error"
            className="portal-validation"
          >
            {validationError}
          </p>
        )}

        <div>
          <button
            type="submit"
            data-testid="submit-details-btn"
            disabled={submitting}
            className="portal-button"
          >
            {submitting ? 'Submitting Update…' : 'Submit Update Request'}
          </button>
        </div>
      </form>

      {result && (
        <div
          role="status"
          data-testid="details-result"
          data-outcome={result.ok ? 'accepted' : 'rejected'}
          className="portal-result"
        >
          <strong>{result.ok ? 'Update Request Accepted: ' : 'Update Request Rejected: '}</strong>
          <span>{result.message}</span>
          {result.decision && (
            <div style={{ marginTop: '4px', fontSize: '12px', opacity: 0.9 }}>
              BotGuard decision: <code>{result.decision}</code> | band: <code>{result.band}</code>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

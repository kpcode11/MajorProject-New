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
          action: 'update_details',
          fields_updated: fieldsUpdated,
          city_code: city,
          language_code: language,
          confirmed: true,
        },
        () => assessWithStepUp('update_details'),
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
      style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(15,23,42,0.05)',
      }}
    >
      <h2 id="update-details-heading" style={{ marginTop: 0, fontSize: '20px', color: '#0f172a' }}>
        Update details
      </h2>
      <p style={{ color: '#475569', fontSize: '14px', marginBottom: '20px' }}>
        Update synthetic demographic details. Only field names and coarse selections are sent to the
        demo API; typed text stays in browser memory.
      </p>

      <form
        onSubmit={(e) => void handleSubmit(e)}
        noValidate
        style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '520px' }}
      >
        <div>
          <label
            htmlFor="detail-name"
            style={{ display: 'block', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}
          >
            Synthetic Resident Full Name
          </label>
          <input
            id="detail-name"
            name="fullName"
            type="text"
            autoComplete="off"
            placeholder="e.g. Aarav Demo Citizen"
            data-testid="detail-name-input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
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

        <div>
          <label
            htmlFor="detail-address"
            style={{ display: 'block', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}
          >
            Synthetic Address Line
          </label>
          <input
            id="detail-address"
            name="address"
            type="text"
            autoComplete="off"
            placeholder="e.g. 42 Research Park Avenue"
            data-testid="detail-address-input"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
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

        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 180px' }}>
            <label
              htmlFor="detail-pincode"
              style={{ display: 'block', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}
            >
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
              value={pincode}
              onChange={(e) => setPincode(e.target.value)}
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

          <div style={{ flex: '1 1 200px' }}>
            <label
              htmlFor="detail-city"
              style={{ display: 'block', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}
            >
              District / City
            </label>
            <select
              id="detail-city"
              name="city"
              data-testid="detail-city-select"
              value={city}
              onChange={(e) => setCity(e.target.value)}
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
              <option value="BENGALURU">Bengaluru Urban</option>
              <option value="DELHI">New Delhi</option>
              <option value="MUMBAI">Mumbai Suburban</option>
              <option value="CHENNAI">Chennai</option>
              <option value="HYDERABAD">Hyderabad</option>
            </select>
          </div>
        </div>

        <div>
          <label
            htmlFor="detail-language"
            style={{ display: 'block', fontWeight: 600, fontSize: '14px', marginBottom: '6px' }}
          >
            Preferred Notification Language
          </label>
          <select
            id="detail-language"
            name="language"
            data-testid="detail-language-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
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
            <option value="EN">English</option>
            <option value="HI">Hindi</option>
            <option value="KN">Kannada</option>
            <option value="TA">Tamil</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            id="detail-confirm"
            name="confirmed"
            type="checkbox"
            data-testid="detail-confirm-checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          <label htmlFor="detail-confirm" style={{ fontSize: '14px', color: '#334155' }}>
            I confirm these entries are synthetic demonstration values only.
          </label>
        </div>

        {validationError && (
          <p
            role="alert"
            data-testid="details-validation-error"
            style={{ color: '#b91c1c', fontSize: '13px', margin: 0 }}
          >
            {validationError}
          </p>
        )}

        <div>
          <button
            type="submit"
            data-testid="submit-details-btn"
            disabled={submitting}
            style={{
              padding: '10px 20px',
              fontSize: '15px',
              fontWeight: 600,
              borderRadius: '8px',
              border: 'none',
              background: submitting ? '#64748b' : '#0284c7',
              color: '#ffffff',
              cursor: submitting ? 'wait' : 'pointer',
            }}
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
          style={{
            marginTop: '20px',
            padding: '14px 16px',
            borderRadius: '8px',
            border: `1px solid ${result.ok ? '#22c55e' : '#ef4444'}`,
            background: result.ok ? '#f0fdf4' : '#fef2f2',
            color: result.ok ? '#166534' : '#991b1b',
            fontSize: '14px',
          }}
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

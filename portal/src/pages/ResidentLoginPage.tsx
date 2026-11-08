/**
 * "Resident login" page with an identifier text field and Send OTP button (P7-02).
 *
 * Never transmits the raw typed identifier string to the backend; sends only coarse
 * length metadata alongside the `X-Human-Token` header.
 */
import { useBotGuard } from '@botguard/sdk/react';
import { useState, type FormEvent, type ReactNode } from 'react';
import { callPortalEndpoint, type PortalApiResult } from '../api.js';

export function ResidentLoginPage(): ReactNode {
  const { assessWithStepUp } = useBotGuard();
  const [identifier, setIdentifier] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [result, setResult] = useState<PortalApiResult | null>(null);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = identifier.trim();
    if (trimmed.length < 4) {
      setValidationError('Please enter at least 4 characters for the mock identifier.');
      return;
    }
    setValidationError(null);
    setSubmitting(true);
    try {
      const apiResult = await callPortalEndpoint(
        '/portal-api/otp/request',
        {
          action: 'login',
          identifier_length: trimmed.length,
        },
        () => assessWithStepUp('login'),
      );
      setResult(apiResult);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section
      data-testid="page-login"
      aria-labelledby="login-page-heading"
      style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(15,23,42,0.05)',
      }}
    >
      <h2 id="login-page-heading" style={{ marginTop: 0, fontSize: '20px', color: '#0f172a' }}>
        Resident login
      </h2>
      <p style={{ color: '#475569', fontSize: '14px', marginBottom: '20px' }}>
        Enter a synthetic mock identifier (for example, <code>9999-0000-1234</code>) and click{' '}
        <strong>Send OTP</strong>. Do not enter any real Aadhaar or government ID number.
      </p>

      <form onSubmit={(e) => void handleSubmit(e)} noValidate>
        <div style={{ marginBottom: '16px' }}>
          <label
            htmlFor="resident-identifier"
            style={{
              display: 'block',
              fontWeight: 600,
              fontSize: '14px',
              marginBottom: '6px',
              color: '#1e293b',
            }}
          >
            Mock Resident Identifier
          </label>
          <input
            id="resident-identifier"
            name="identifier"
            type="text"
            autoComplete="off"
            inputMode="numeric"
            placeholder="e.g. 999900001234"
            data-testid="identifier-input"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            style={{
              width: '100%',
              maxWidth: '360px',
              padding: '10px 12px',
              fontSize: '15px',
              borderRadius: '8px',
              border: '1px solid #94a3b8',
              boxSizing: 'border-box',
            }}
          />
          {validationError && (
            <p
              role="alert"
              data-testid="login-validation-error"
              style={{ color: '#b91c1c', fontSize: '13px', marginTop: '6px', marginBottom: 0 }}
            >
              {validationError}
            </p>
          )}
        </div>

        <button
          type="submit"
          data-testid="send-otp-btn"
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
          {submitting ? 'Verifying & Sending…' : 'Send OTP'}
        </button>
      </form>

      {result && (
        <div
          role="status"
          data-testid="otp-result"
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
          <strong>{result.ok ? 'OTP Dispatched (Demo): ' : 'OTP Request Rejected: '}</strong>
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

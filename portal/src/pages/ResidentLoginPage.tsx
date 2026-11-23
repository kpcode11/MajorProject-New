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
          action: 'otp_request',
          identifier_length: trimmed.length,
        },
        () => assessWithStepUp('otp_request'),
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
      className="portal-page-card"
    >
      <h2 id="login-page-heading">Resident login</h2>
      <p id="resident-identifier-hint" className="portal-page-lead">
        Enter a synthetic mock identifier (for example, <code>9999-0000-1234</code>) and click{' '}
        <strong>Send OTP</strong>. Do not enter any real Aadhaar or government ID number.
      </p>

      <form onSubmit={(e) => void handleSubmit(e)} noValidate className="portal-form">
        <div className="portal-field">
          <label htmlFor="resident-identifier" className="portal-label">
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
            aria-invalid={validationError ? 'true' : undefined}
            aria-describedby={
              validationError
                ? 'resident-identifier-hint login-validation-error'
                : 'resident-identifier-hint'
            }
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            className="portal-input"
          />
          {validationError && (
            <p
              id="login-validation-error"
              role="alert"
              data-testid="login-validation-error"
              className="portal-validation"
            >
              {validationError}
            </p>
          )}
        </div>

        <button
          type="submit"
          data-testid="send-otp-btn"
          disabled={submitting}
          className="portal-button"
          style={{ alignSelf: 'flex-start' }}
        >
          {submitting ? 'Verifying & Sending…' : 'Send OTP'}
        </button>
      </form>

      {result && (
        <div
          role="status"
          data-testid="otp-result"
          data-outcome={result.ok ? 'accepted' : 'rejected'}
          className="portal-result"
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

/**
 * Landing page for the Mock Resident Self-Service Portal (P7-02).
 */
import type { ReactNode } from 'react';

export type PortalPageId = 'landing' | 'login' | 'update-details' | 'centre-search';

export interface LandingPageProps {
  onNavigate: (page: PortalPageId) => void;
}

const SERVICE_CARDS: ReadonlyArray<{
  id: Exclude<PortalPageId, 'landing'>;
  testId: string;
  title: string;
  actionLabel: string;
  description: string;
  actionCode: string;
}> = [
  {
    id: 'login',
    testId: 'card-login',
    title: 'Resident login',
    actionLabel: 'Open Resident login',
    description:
      'Enter a synthetic 12-digit identifier and request a one-time password (OTP) protected against automated OTP flooding.',
    actionCode: 'action: otp_request',
  },
  {
    id: 'update-details',
    testId: 'card-update-details',
    title: 'Update details',
    actionLabel: 'Open Update details',
    description:
      'Submit a demographic update form (name, address, PIN code, city, language) exercising natural mouse and keystroke timing.',
    actionCode: 'action: details_update',
  },
  {
    id: 'centre-search',
    testId: 'card-centre-search',
    title: 'Centre search',
    actionLabel: 'Open Centre search',
    description:
      'Locate mock enrolment and update centres by district or PIN code, protected against automated scraping bots.',
    actionCode: 'action: centre_search',
  },
];

export function LandingPage({ onNavigate }: LandingPageProps): ReactNode {
  return (
    <div
      data-testid="page-landing"
      style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}
    >
      <section
        aria-labelledby="portal-welcome-heading"
        style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 1px 3px rgba(15,23,42,0.05)',
        }}
      >
        <h2
          id="portal-welcome-heading"
          style={{ marginTop: 0, fontSize: '20px', color: '#0f172a' }}
        >
          Welcome to the Mock Citizen Portal
        </h2>
        <p style={{ color: '#334155', lineHeight: 1.6, marginBottom: '12px' }}>
          This local demonstration portal evaluates passive behavioural bot detection (SIH1672) as a
          drop-in replacement for visual CAPTCHA puzzles. Every protected action requests a
          short-lived <code>X-Human-Token</code> from the passive BotGuard SDK before calling{' '}
          <code>/portal-api/*</code>.
        </p>
        <p style={{ color: '#475569', fontSize: '14px', margin: 0 }}>
          Privacy guarantee: raw typed characters and field values are never collected by the
          telemetry SDK or stored by the backend.
        </p>
      </section>

      <section aria-label="Available self-service flows">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '16px',
          }}
        >
          {SERVICE_CARDS.map((card) => (
            <article
              key={card.id}
              data-testid={card.testId}
              style={{
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                borderRadius: '12px',
                padding: '20px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '16px',
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: '#0369a1',
                    marginBottom: '6px',
                    fontFamily: 'monospace',
                  }}
                >
                  {card.actionCode}
                </div>
                <h3 style={{ margin: '0 0 8px', fontSize: '18px', color: '#0f172a' }}>
                  {card.title}
                </h3>
                <p style={{ margin: 0, fontSize: '14px', color: '#475569', lineHeight: 1.5 }}>
                  {card.description}
                </p>
              </div>
              <button
                type="button"
                data-testid={`goto-${card.id}`}
                onClick={() => onNavigate(card.id)}
                style={{
                  padding: '10px 16px',
                  borderRadius: '8px',
                  border: '1px solid #0284c7',
                  background: '#0284c7',
                  color: '#ffffff',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textAlign: 'center',
                }}
              >
                {card.actionLabel}
              </button>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

/**
 * Landing page for the Mock Resident Self-Service Portal (P7-02).
 */
import type { ReactNode } from 'react';

export type PortalPageId = 'landing' | 'login' | 'update-details' | 'centre-search' | 'admin';

export interface LandingPageProps {
  onNavigate: (page: PortalPageId) => void;
}

const SERVICE_CARDS: ReadonlyArray<{
  id: Exclude<PortalPageId, 'landing' | 'admin'>;
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
    <div data-testid="page-landing">
      <section className="portal-hero" aria-labelledby="portal-welcome-heading">
        <h2 id="portal-welcome-heading">Resident services, without the puzzle.</h2>
        <p>
          This local demonstration portal evaluates passive behavioural bot detection (SIH1672) as a
          drop-in replacement for visual CAPTCHA puzzles. Every protected action requests a
          short-lived <code>X-Human-Token</code> from the passive BotGuard SDK before calling{' '}
          <code>/portal-api/*</code>.
        </p>
        <p className="portal-privacy-note">
          Privacy guarantee: raw typed characters and field values are never collected by the
          telemetry SDK or stored by the backend.
        </p>
      </section>

      <section aria-label="Available self-service flows">
        <p className="portal-section-label">Available self-service flows</p>
        <div className="portal-service-grid">
          {SERVICE_CARDS.map((card) => (
            <article key={card.id} data-testid={card.testId} className="portal-service-card">
              <div>
                <div className="portal-service-code">{card.actionCode}</div>
                <h3>{card.title}</h3>
                <p>{card.description}</p>
              </div>
              <button
                type="button"
                data-testid={`goto-${card.id}`}
                onClick={() => onNavigate(card.id)}
                className="portal-primary-action"
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

/**
 * Mock Resident Services Portal — DEMO — not a government portal (P7-01, P7-02).
 *
 * Wraps the portal shell in `BotGuardProvider`, renders a prominent disclaimer banner
 * stating that this application is a local research demonstration and not affiliated with
 * UIDAI or any government portal, and provides navigation between:
 *  - Landing (`landing`)
 *  - Resident login (`login`)
 *  - Update details (`update-details`)
 *  - Centre search (`centre-search`)
 */
import { BotGuardProvider, useBotGuard } from '@botguard/sdk/react';
import { useState, type ReactNode } from 'react';
import { CentreSearchPage } from './pages/CentreSearchPage.js';
import { LandingPage, type PortalPageId } from './pages/LandingPage.js';
import { ResidentLoginPage } from './pages/ResidentLoginPage.js';
import { UpdateDetailsPage } from './pages/UpdateDetailsPage.js';

export const DEMO_DISCLAIMER_TEXT = 'DEMO — not a government portal';

const NAV_ITEMS: ReadonlyArray<{ id: PortalPageId; label: string; testId: string }> = [
  { id: 'landing', label: 'Overview', testId: 'nav-landing' },
  { id: 'login', label: 'Resident login', testId: 'nav-login' },
  { id: 'update-details', label: 'Update details', testId: 'nav-update-details' },
  { id: 'centre-search', label: 'Centre search', testId: 'nav-centre-search' },
];

function resolveInitialPage(explicitPage?: PortalPageId): PortalPageId {
  if (explicitPage) return explicitPage;
  if (typeof window === 'undefined') return 'landing';
  const params = new URLSearchParams(window.location.search);
  const queryPage = params.get('page');
  if (
    queryPage === 'landing' ||
    queryPage === 'login' ||
    queryPage === 'update-details' ||
    queryPage === 'centre-search'
  ) {
    return queryPage;
  }
  const hashPage = window.location.hash.replace(/^#\/?/, '');
  if (
    hashPage === 'landing' ||
    hashPage === 'login' ||
    hashPage === 'update-details' ||
    hashPage === 'centre-search'
  ) {
    return hashPage;
  }
  return 'landing';
}

export function PortalStatusBadge(): ReactNode {
  const { running, assessing, lastResponse } = useBotGuard();
  return (
    <div
      data-testid="botguard-status"
      aria-live="polite"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 12px',
        borderRadius: '999px',
        fontSize: '13px',
        background: '#e0f2fe',
        color: '#0369a1',
        fontWeight: 500,
      }}
    >
      <span>Passive BotGuard: {running ? 'Active' : 'Idle'}</span>
      {assessing && <span>(Assessing…)</span>}
      {lastResponse && (
        <span data-testid="last-decision">
          Last decision: {lastResponse.decision} ({lastResponse.band})
        </span>
      )}
    </div>
  );
}

export interface PortalShellProps {
  initialPage?: PortalPageId;
}

export function PortalShell({ initialPage }: PortalShellProps = {}): ReactNode {
  const [activePage, setActivePage] = useState<PortalPageId>(() => resolveInitialPage(initialPage));

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div
        role="region"
        aria-label="Demonstration disclaimer"
        data-testid="demo-disclaimer-banner"
        style={{
          background: '#fef3c7',
          color: '#92400e',
          borderBottom: '1px solid #f59e0b',
          padding: '10px 16px',
          textAlign: 'center',
          fontSize: '14px',
          fontWeight: 700,
          letterSpacing: '0.02em',
        }}
      >
        {DEMO_DISCLAIMER_TEXT} — Academic research prototype for passive bot detection (SIH1672). Do
        not enter real personal identifiers.
      </div>

      <header
        style={{
          background: '#ffffff',
          borderBottom: '1px solid #e2e8f0',
          padding: '16px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: '#0f172a' }}>
              Mock Resident Self-Service Portal
            </h1>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#475569' }}>
              Protected by passive behavioural verification — no CAPTCHA puzzles
            </p>
          </div>
          <PortalStatusBadge />
        </div>

        <nav aria-label="Portal sections" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {NAV_ITEMS.map((item) => {
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                type="button"
                data-testid={item.testId}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => setActivePage(item.id)}
                style={{
                  padding: '8px 14px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: isActive ? '1px solid #0284c7' : '1px solid #cbd5e1',
                  background: isActive ? '#0284c7' : '#f8fafc',
                  color: isActive ? '#ffffff' : '#1e293b',
                }}
              >
                {item.label}
              </button>
            );
          })}
        </nav>
      </header>

      <main
        style={{
          flex: 1,
          maxWidth: '960px',
          width: '100%',
          margin: '0 auto',
          padding: '24px',
          boxSizing: 'border-box',
        }}
      >
        {activePage === 'landing' && <LandingPage onNavigate={setActivePage} />}
        {activePage === 'login' && <ResidentLoginPage />}
        {activePage === 'update-details' && <UpdateDetailsPage />}
        {activePage === 'centre-search' && <CentreSearchPage />}
      </main>

      <footer
        style={{
          borderTop: '1px solid #e2e8f0',
          padding: '14px 24px',
          textAlign: 'center',
          fontSize: '12px',
          color: '#64748b',
          background: '#ffffff',
        }}
      >
        {DEMO_DISCLAIMER_TEXT} · Local-only test target
      </footer>
    </div>
  );
}

export interface AppProps {
  initialPage?: PortalPageId;
}

export function App({ initialPage }: AppProps = {}): ReactNode {
  return (
    <BotGuardProvider>
      <PortalShell initialPage={initialPage} />
    </BotGuardProvider>
  );
}

export default App;

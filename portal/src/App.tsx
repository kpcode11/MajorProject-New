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
import { useEffect, useState, type ReactNode } from 'react';
import { AdminDashboardPage } from './pages/AdminDashboardPage.js';
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
  { id: 'admin', label: 'Admin dashboard', testId: 'nav-admin' },
];

function isStandaloneAdminPort(): boolean {
  return typeof window !== 'undefined' && window.location?.port === '5174';
}

function resolveInitialPage(explicitPage?: PortalPageId): PortalPageId {
  if (explicitPage) return explicitPage;
  if (typeof window === 'undefined') return 'landing';
  if (isStandaloneAdminPort()) return 'admin';
  const params = new URLSearchParams(window.location.search);
  const queryPage = params.get('page');
  if (
    queryPage === 'landing' ||
    queryPage === 'login' ||
    queryPage === 'update-details' ||
    queryPage === 'centre-search' ||
    queryPage === 'admin'
  ) {
    return queryPage;
  }
  const hashPage = window.location.hash.replace(/^#\/?/, '');
  if (
    hashPage === 'landing' ||
    hashPage === 'login' ||
    hashPage === 'update-details' ||
    hashPage === 'centre-search' ||
    hashPage === 'admin'
  ) {
    return hashPage;
  }
  return 'landing';
}

export function PortalStatusBadge(): ReactNode {
  const { running, assessing, lastResponse } = useBotGuard();
  return (
    <div data-testid="botguard-status" aria-live="polite" className="portal-status">
      <span className="portal-status-dot" aria-hidden="true" />
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
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') return 'light';
    const saved = window.localStorage.getItem('botguard-theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    window.localStorage.setItem('botguard-theme', theme);
  }, [theme]);

  return (
    <div className="portal-app" data-theme={theme}>
      <a href="#portal-main-content" className="portal-skip-link" data-testid="skip-to-main">
        Skip to main content
      </a>
      <div
        role="region"
        aria-label="Demonstration disclaimer"
        data-testid="demo-disclaimer-banner"
        className="portal-disclaimer"
      >
        {DEMO_DISCLAIMER_TEXT} — Academic research prototype for passive bot detection (SIH1672). Do
        not enter real personal identifiers.
      </div>

      <header className="portal-header">
        <div className="portal-header-inner">
          <div className="portal-brand">
            <div className="portal-mark" aria-hidden="true">
              BG
            </div>
            <div className="portal-brand-copy">
              <span className="portal-brand-title">
                {activePage === 'admin' ? 'BotGuard security console' : 'Resident services portal'}
              </span>
              <span className="portal-brand-subtitle">
                {activePage === 'admin'
                  ? 'Operational monitoring for passive bot detection'
                  : 'Protected by passive behavioural verification'}
              </span>
            </div>
          </div>
          <PortalStatusBadge />
        </div>

        <nav aria-label="Portal sections" className="portal-nav">
          <div className="portal-nav-inner">
            {isStandaloneAdminPort() ? (
              <>
                <button
                  type="button"
                  data-testid="nav-admin"
                  aria-current="page"
                  onClick={() => setActivePage('admin')}
                  className="portal-nav-button"
                  data-active="true"
                >
                  Security console
                </button>
                <a
                  href="http://127.0.0.1:5173"
                  target="_blank"
                  rel="noreferrer"
                  className="portal-nav-button"
                  style={{ textDecoration: 'none' }}
                >
                  Open resident portal ↗
                </a>
              </>
            ) : (
              <>
                {NAV_ITEMS.filter((item) => item.id !== 'admin').map((item) => {
                  const isActive = activePage === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      data-testid={item.testId}
                      aria-current={isActive ? 'page' : undefined}
                      onClick={() => setActivePage(item.id)}
                      className="portal-nav-button"
                      data-active={isActive}
                    >
                      {item.label}
                    </button>
                  );
                })}
                <button
                  type="button"
                  data-testid="nav-admin"
                  aria-current={activePage === 'admin' ? 'page' : undefined}
                  onClick={() => setActivePage('admin')}
                  className="portal-nav-button admin"
                  data-active={activePage === 'admin'}
                >
                  Security console
                </button>
              </>
            )}
          </div>
        </nav>
      </header>

      <main
        id="portal-main-content"
        tabIndex={-1}
        className="portal-main"
        style={{ maxWidth: activePage === 'admin' ? '1320px' : undefined }}
      >
        {activePage === 'landing' && <LandingPage onNavigate={setActivePage} />}
        {activePage === 'login' && <ResidentLoginPage />}
        {activePage === 'update-details' && <UpdateDetailsPage />}
        {activePage === 'centre-search' && <CentreSearchPage />}
        {activePage === 'admin' && <AdminDashboardPage />}
      </main>

      <footer className="portal-footer">
        <div className="portal-footer-inner">
          <span>{DEMO_DISCLAIMER_TEXT} · Local-only test target</span>
          <button
            type="button"
            className="portal-theme-toggle"
            data-testid="theme-toggle"
            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
            aria-pressed={theme === 'dark'}
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          >
            <span>{theme === 'light' ? 'Dark theme' : 'Light theme'}</span>
          </button>
        </div>
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

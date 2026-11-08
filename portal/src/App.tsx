/**
 * Mock Resident Services Portal — DEMO — not a government portal (P7-01).
 *
 * Wraps the portal shell in `BotGuardProvider` and renders a prominent disclaimer banner
 * stating that this application is a local research demonstration and not affiliated with
 * UIDAI or any government portal.
 */
import { BotGuardProvider, useBotGuard } from '@botguard/sdk/react';
import type { ReactNode } from 'react';

export const DEMO_DISCLAIMER_TEXT = 'DEMO — not a government portal';

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

export function PortalShell(): ReactNode {
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
          <h2 id="portal-welcome-heading" style={{ marginTop: 0, fontSize: '18px' }}>
            Welcome to the Mock Citizen Portal
          </h2>
          <p style={{ color: '#334155', lineHeight: 1.6, marginBottom: 0 }}>
            This mock portal demonstrates passive bot detection for resident login (OTP request),
            demographic detail updates, and enrolment centre search without visual CAPTCHA puzzles.
          </p>
        </section>
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

export function App(): ReactNode {
  return (
    <BotGuardProvider>
      <PortalShell />
    </BotGuardProvider>
  );
}

export default App;

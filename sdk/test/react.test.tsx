import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type AssessResponse, BotGuardClient } from '../src/index';
import { type BotGuardContextValue, BotGuardProvider, useBotGuard } from '../src/react/index';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const ALLOW_RESPONSE: AssessResponse = {
  decision: 'allow',
  band: 'low',
  token: 'jwt-react-allow',
  challenge: null,
  request_id: 'req-react-1',
  model_versions: { mouse: 'lgbm-1.0.0' },
  degraded: false,
};

const CHALLENGE_RESPONSE: AssessResponse = {
  decision: 'challenge',
  band: 'medium',
  token: null,
  challenge: {
    id: 'chal-react-1',
    type: 'press_hold',
    hold_ms: 900,
    expires_in: 60,
  },
  request_id: 'req-react-chal',
  model_versions: { mouse: 'lgbm-1.0.0' },
  degraded: false,
};

let container: HTMLDivElement | null = null;
let root: Root | null = null;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  if (root) {
    act(() => {
      root?.unmount();
    });
    root = null;
  }
  container?.remove();
  container = null;
});

describe('BotGuardProvider & useBotGuard (P6-09)', () => {
  it('starts the SDK client on mount, exposes assess(), and stops on unmount', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-react-1', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(ALLOW_RESPONSE));

    const client = new BotGuardClient({
      transportDeps: { fetchImpl: fetchMock },
    });

    let latestCtx = null as BotGuardContextValue | null;
    function Consumer() {
      latestCtx = useBotGuard();
      return <span id="decision">{latestCtx.lastResponse?.decision ?? 'none'}</span>;
    }

    await act(async () => {
      root?.render(
        <BotGuardProvider client={client}>
          <Consumer />
        </BotGuardProvider>,
      );
    });

    expect(client.running).toBe(true);
    expect(container?.querySelector('#decision')?.textContent).toBe('none');

    let res: AssessResponse | undefined;
    await act(async () => {
      res = await latestCtx?.assess('login');
    });

    expect(res).toEqual(ALLOW_RESPONSE);
    expect(container?.querySelector('#decision')?.textContent).toBe('allow');

    await act(async () => {
      root?.unmount();
      root = null;
    });

    expect(client.running).toBe(false);
  });

  it('assessWithStepUp automatically runs the step-up challenge when decision is challenge', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-1', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(CHALLENGE_RESPONSE))
      .mockResolvedValueOnce(jsonResponse({ nonce: 'n-2', expires_in: 300 }))
      .mockResolvedValueOnce(jsonResponse(ALLOW_RESPONSE));

    const handler = vi.fn(async () => ({ holdStartMs: 100, holdEndMs: 1_050 }));

    let latestCtx = null as BotGuardContextValue | null;
    function Consumer() {
      latestCtx = useBotGuard();
      return <div>{latestCtx.lastResponse?.decision ?? 'idle'}</div>;
    }

    await act(async () => {
      root?.render(
        <BotGuardProvider
          options={{
            transportDeps: { fetchImpl: fetchMock },
            challengeHandler: handler,
          }}
        >
          <Consumer />
        </BotGuardProvider>,
      );
    });

    let finalRes: AssessResponse | undefined;
    await act(async () => {
      finalRes = await latestCtx?.assessWithStepUp('otp_request');
    });

    expect(handler).toHaveBeenCalledTimes(1);
    expect(finalRes).toEqual(ALLOW_RESPONSE);
    expect(latestCtx?.lastResponse).toEqual(ALLOW_RESPONSE);
  });

  it('throws a descriptive error when useBotGuard() is called outside BotGuardProvider', () => {
    let caught = null as Error | null;
    function Orphan() {
      try {
        useBotGuard();
      } catch (err) {
        caught = err as Error;
      }
      return null;
    }

    act(() => {
      root?.render(<Orphan />);
    });

    expect(caught?.message).toContain('useBotGuard() must be used within a <BotGuardProvider>');
  });
});

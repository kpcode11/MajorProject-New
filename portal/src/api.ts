/**
 * Client helper for calling protected mock portal routes (`/portal-api/*`) (P7-02, P7-03).
 *
 * Strictly avoids sending raw typed strings from inputs — only coarse metadata is sent
 * alongside the `X-Human-Token` header issued by BotGuard.
 */
import type { AssessResponse } from '@botguard/sdk';

export interface PortalApiResult<T = Record<string, unknown>> {
  ok: boolean;
  status: number;
  message: string;
  decision?: AssessResponse['decision'];
  band?: AssessResponse['band'];
  data?: T;
}

export interface CentreRecord {
  code: string;
  name: string;
  district: string;
  services: string[];
  hours: string;
}

export async function callPortalEndpoint<T = Record<string, unknown>>(
  path: string,
  body: Record<string, unknown>,
  assessFn: () => Promise<AssessResponse>,
  fetchImpl: typeof fetch = globalThis.fetch,
): Promise<PortalApiResult<T>> {
  let assessment: AssessResponse | null;
  try {
    assessment = await assessFn();
  } catch {
    assessment = null;
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (assessment?.token) {
    headers['X-Human-Token'] = assessment.token;
  }

  try {
    const response = await fetchImpl(path, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    let payload: Record<string, unknown>;
    try {
      payload = (await response.json()) as Record<string, unknown>;
    } catch {
      payload = {};
    }

    if (response.ok) {
      return {
        ok: true,
        status: response.status,
        message:
          typeof payload.message === 'string'
            ? payload.message
            : 'Request verified and accepted by mock portal.',
        decision: assessment?.decision,
        band: assessment?.band,
        data: payload as T,
      };
    }

    const detail =
      typeof payload.detail === 'string'
        ? payload.detail
        : typeof payload.message === 'string'
          ? payload.message
          : assessment?.decision === 'deny'
            ? 'Blocked by passive bot detection (decision: deny).'
            : `Request rejected with HTTP ${response.status}.`;

    return {
      ok: false,
      status: response.status,
      message: detail,
      decision: assessment?.decision,
      band: assessment?.band,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message:
        assessment?.decision === 'deny'
          ? 'Blocked by passive bot detection (decision: deny).'
          : 'Portal backend unavailable or network error.',
      decision: assessment?.decision,
      band: assessment?.band,
    };
  }
}

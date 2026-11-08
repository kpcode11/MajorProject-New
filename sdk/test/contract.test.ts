/**
 * SDK / Backend contract test (P6-13).
 *
 * Loads the canonical JSON Schema generated directly from the backend's Pydantic v2 models
 * (`data/fixtures/backend_contract_schema.json`) and validates SDK-produced `AssessRequest` and
 * `ChallengeAssessRequest` payloads against every schema rule (`$ref`, `anyOf`, `type`, `enum`,
 * `required`, `minLength`/`maxLength`, `minimum`/`maximum`, `minItems`/`maxItems`, `properties`).
 *
 * Also writes sample SDK-produced payloads to `data/fixtures/sdk_sample_payloads.json` so the
 * backend pytest suite (`backend/tests/test_sdk_contract.py`) validates them directly with
 * Pydantic `AssessRequest.model_validate` and `ChallengeAssessRequest.model_validate`.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  type AssessResponse,
  BotGuardClient,
  type ChallengeInfo,
  buildAssessPayload,
  buildChallengePayload,
} from '../src/index';

interface JsonSchemaNode {
  $ref?: string;
  $defs?: Record<string, JsonSchemaNode>;
  type?: string;
  enum?: unknown[];
  anyOf?: JsonSchemaNode[];
  properties?: Record<string, JsonSchemaNode>;
  required?: string[];
  items?: JsonSchemaNode;
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  minItems?: number;
  maxItems?: number;
}

const testDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(testDir, '..', '..');
const schemaPath = resolve(repoRoot, 'data', 'fixtures', 'backend_contract_schema.json');
const samplePayloadsPath = resolve(repoRoot, 'data', 'fixtures', 'sdk_sample_payloads.json');

const contractSchemas = JSON.parse(readFileSync(schemaPath, 'utf8')) as {
  AssessRequest: JsonSchemaNode;
  ChallengeAssessRequest: JsonSchemaNode;
  AssessResponse: JsonSchemaNode;
  NonceResponse: JsonSchemaNode;
};

/** Recursive validator for Pydantic v2 JSON Schemas. Returns a list of violation messages. */
function validateAgainstSchema(
  value: unknown,
  schema: JsonSchemaNode,
  rootSchema: JsonSchemaNode = schema,
  path = '$',
): string[] {
  if (schema.$ref) {
    const refPrefix = '#/$defs/';
    if (!schema.$ref.startsWith(refPrefix)) {
      return [`${path}: unsupported $ref ${schema.$ref}`];
    }
    const defName = schema.$ref.slice(refPrefix.length);
    const target = rootSchema.$defs?.[defName];
    if (!target) {
      return [`${path}: missing $defs.${defName}`];
    }
    return validateAgainstSchema(value, target, rootSchema, path);
  }

  if (schema.anyOf) {
    const branchErrors: string[][] = [];
    for (const branch of schema.anyOf) {
      const errs = validateAgainstSchema(value, branch, rootSchema, path);
      if (errs.length === 0) return [];
      branchErrors.push(errs);
    }
    return [
      `${path}: did not match anyOf branches (${branchErrors.map((e) => e.join('; ')).join(' | ')})`,
    ];
  }

  if (schema.enum) {
    if (!schema.enum.includes(value)) {
      return [`${path}: value ${JSON.stringify(value)} not in enum ${JSON.stringify(schema.enum)}`];
    }
  }

  if (schema.type) {
    switch (schema.type) {
      case 'null':
        if (value !== null) return [`${path}: expected null, got ${typeof value}`];
        return [];
      case 'boolean':
        if (typeof value !== 'boolean') return [`${path}: expected boolean, got ${typeof value}`];
        return [];
      case 'integer':
        if (typeof value !== 'number' || !Number.isInteger(value)) {
          return [`${path}: expected integer, got ${String(value)}`];
        }
        break;
      case 'number':
        if (typeof value !== 'number' || !Number.isFinite(value)) {
          return [`${path}: expected number, got ${String(value)}`];
        }
        break;
      case 'string':
        if (typeof value !== 'string') return [`${path}: expected string, got ${typeof value}`];
        if (schema.minLength !== undefined && value.length < schema.minLength) {
          return [`${path}: length ${value.length} < minLength ${schema.minLength}`];
        }
        if (schema.maxLength !== undefined && value.length > schema.maxLength) {
          return [`${path}: length ${value.length} > maxLength ${schema.maxLength}`];
        }
        return [];
      case 'array': {
        if (!Array.isArray(value)) return [`${path}: expected array, got ${typeof value}`];
        const errs: string[] = [];
        if (schema.minItems !== undefined && value.length < schema.minItems) {
          errs.push(`${path}: items ${value.length} < minItems ${schema.minItems}`);
        }
        if (schema.maxItems !== undefined && value.length > schema.maxItems) {
          errs.push(`${path}: items ${value.length} > maxItems ${schema.maxItems}`);
        }
        if (schema.items) {
          value.forEach((item, idx) => {
            errs.push(
              ...validateAgainstSchema(
                item,
                schema.items as JsonSchemaNode,
                rootSchema,
                `${path}[${idx}]`,
              ),
            );
          });
        }
        return errs;
      }
      case 'object': {
        if (typeof value !== 'object' || value === null || Array.isArray(value)) {
          return [`${path}: expected object, got ${String(value)}`];
        }
        const record = value as Record<string, unknown>;
        const errs: string[] = [];
        for (const reqKey of schema.required ?? []) {
          if (!(reqKey in record) || record[reqKey] === undefined) {
            errs.push(`${path}: missing required property '${reqKey}'`);
          }
        }
        const props = schema.properties ?? {};
        for (const [k, v] of Object.entries(record)) {
          if (v === undefined) continue;
          const propSchema = props[k];
          if (!propSchema) {
            errs.push(`${path}: unknown property '${k}' not present in backend schema`);
            continue;
          }
          errs.push(...validateAgainstSchema(v, propSchema, rootSchema, `${path}.${k}`));
        }
        return errs;
      }
    }
  }

  if (typeof value === 'number') {
    if (schema.minimum !== undefined && value < schema.minimum) {
      return [`${path}: ${value} < minimum ${schema.minimum}`];
    }
    if (schema.maximum !== undefined && value > schema.maximum) {
      return [`${path}: ${value} > maximum ${schema.maximum}`];
    }
  }

  return [];
}

let clock = 0;
const now = (): number => clock;

afterEach(() => {
  clock = 0;
});

describe('P6-13 SDK / Backend JSON Schema Contract Test', () => {
  it('validates live SDK-collected AssessRequest and ChallengeAssessRequest payloads against the backend Pydantic JSON Schema', async () => {
    let capturedAssessBody: unknown = null;
    let capturedChallengeBody: unknown = null;

    const sampleAllow: AssessResponse = {
      decision: 'allow',
      band: 'low',
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.contract',
      challenge: null,
      request_id: 'req-contract-1',
      model_versions: { mouse: 'lgbm-1.0.0', keyboard: 'lr-1.0.0', fusion: '1.0.0' },
      degraded: false,
    };

    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/v1/nonce')) {
        return new Response(JSON.stringify({ nonce: 'nonce-contract-123456', expires_in: 300 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.endsWith('/v1/assess')) {
        capturedAssessBody = JSON.parse(String(init?.body));
        return new Response(JSON.stringify(sampleAllow), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.endsWith('/v1/assess/challenge')) {
        capturedChallengeBody = JSON.parse(String(init?.body));
        return new Response(JSON.stringify(sampleAllow), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      throw new Error(`Unexpected URL ${url}`);
    });

    const client = new BotGuardClient({
      endpoint: 'http://127.0.0.1:8000',
      now,
      envOptions: { integrityTargets: [Math.max] },
      transportDeps: { fetchImpl: fetchMock, nowEpochMs: () => 1_760_000_000_000 },
    });
    client.start();

    // Simulate realistic desktop session: mouse moves, click, keystrokes, scroll, focus
    for (let i = 0; i < 25; i += 1) {
      clock = 100 + i * 25;
      const move = new MouseEvent('mousemove', {
        clientX: 120 + i * 8,
        clientY: 240 + Math.round(Math.sin(i) * 15),
        bubbles: true,
      });
      Object.defineProperty(move, 'isTrusted', { value: true });
      window.dispatchEvent(move);
    }

    clock = 800;
    const down = new MouseEvent('mousedown', { clientX: 320, clientY: 250, bubbles: true });
    Object.defineProperty(down, 'isTrusted', { value: true });
    window.dispatchEvent(down);
    clock = 875;
    const up = new MouseEvent('mouseup', { clientX: 320, clientY: 250, bubbles: true });
    Object.defineProperty(up, 'isTrusted', { value: true });
    window.dispatchEvent(up);

    const keys: [string, string][] = [
      ['r', 'KeyR'],
      ['e', 'KeyE'],
      ['s', 'KeyS'],
      ['1', 'Digit1'],
      [' ', 'Space'],
      ['Enter', 'Enter'],
    ];
    for (const [k, c] of keys) {
      clock += 60;
      const kd = new KeyboardEvent('keydown', { key: k, code: c, bubbles: true });
      Object.defineProperty(kd, 'isTrusted', { value: true });
      window.dispatchEvent(kd);
      clock += 75;
      const ku = new KeyboardEvent('keyup', { key: k, code: c, bubbles: true });
      Object.defineProperty(ku, 'isTrusted', { value: true });
      window.dispatchEvent(ku);
    }

    const scrollEv = new Event('scroll', { bubbles: true });
    Object.defineProperty(scrollEv, 'isTrusted', { value: true });
    window.dispatchEvent(scrollEv);

    clock = 2_400;
    const assessRes = await client.assess('otp_request');

    const challengeInfo: ChallengeInfo = {
      id: 'chal-contract-001',
      type: 'press_hold',
      hold_ms: 1100,
      expires_in: 60,
    };
    clock = 3_800;
    const challengeRes = await client.runChallenge(challengeInfo, 'otp_request', {
      holdStartMs: 2_500,
      holdEndMs: 3_680,
    });

    client.stop();

    expect(assessRes).toEqual(sampleAllow);
    expect(challengeRes).toEqual(sampleAllow);
    expect(capturedAssessBody).not.toBeNull();
    expect(capturedChallengeBody).not.toBeNull();

    // Validate captured requests and responses against the backend JSON Schema
    expect(validateAgainstSchema(capturedAssessBody, contractSchemas.AssessRequest)).toEqual([]);
    expect(
      validateAgainstSchema(capturedChallengeBody, contractSchemas.ChallengeAssessRequest),
    ).toEqual([]);
    expect(validateAgainstSchema(assessRes, contractSchemas.AssessResponse)).toEqual([]);

    // Persist the SDK-produced payloads when not in CI or when missing so backend pytest validates them
    if (!process.env.CI) {
      writeFileSync(
        samplePayloadsPath,
        `${JSON.stringify(
          {
            assess_request: capturedAssessBody,
            challenge_assess_request: capturedChallengeBody,
          },
          null,
          2,
        )}\n`,
        'utf8',
      );
    }
  });

  it('rejects malformed payloads against the backend JSON Schema', () => {
    const badAssess = {
      nonce: '', // violates minLength: 1
      action: 'otp_request',
      schema_version: 0, // violates minimum: 1
      unexpected_field: 123, // unknown property
    };
    const errors = validateAgainstSchema(badAssess, contractSchemas.AssessRequest);
    expect(errors.length).toBeGreaterThanOrEqual(3);

    // Valid builder output always passes
    const validAssess = buildAssessPayload({ nonce: 'n-1', action: 'login' });
    expect(validateAgainstSchema(validAssess, contractSchemas.AssessRequest)).toEqual([]);

    const validChallenge = buildChallengePayload({
      nonce: 'n-2',
      challengeId: 'c-2',
      action: 'login',
      holdStartMs: 0,
      holdEndMs: 1100,
    });
    expect(validateAgainstSchema(validChallenge, contractSchemas.ChallengeAssessRequest)).toEqual(
      [],
    );
  });
});

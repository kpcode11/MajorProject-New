# Load Test Summary Report (`results/system/loadtest_summary.md`)

> **Phase 10 (`P10-04`) Load Testing:** Evaluates throughput (`requests/sec`),
> latency percentiles (`p50`, `p95`, `p99`), error/rejection rates, and protected-API
> breach counts across the four required traffic scenarios.

- **Total requests executed:** `630`
- **Total malicious requests sent:** `460`
- **Malicious requests reaching protected API (`200 OK`):** **`0`** (`0.00%`)
- **Unhandled server errors (`5xx`):** **`0`** (`0.00%`)

## Scenario Results

| Scenario | Requests | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | 200 OK | 401 | 413 | 422 | 429 | 5xx | Malicious Sent | Malicious Reached Protected API |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `normal_mix` | 120 | 276.49 | 0.49 | 10.09 | 12.46 | 110 | 10 | 0 | 0 | 0 | 0 | 10 | **0** |
| `protected_endpoint_flood` | 200 | 2828.45 | 0.21 | 1.21 | 3.03 | 0 | 200 | 0 | 0 | 0 | 0 | 200 | **0** |
| `nonce_flood` | 150 | 7795.93 | 0.11 | 0.25 | 0.44 | 60 | 0 | 0 | 0 | 90 | 0 | 90 | **0** |
| `malformed_assess_flood` | 160 | 7511.70 | 0.13 | 0.21 | 0.46 | 0 | 40 | 40 | 80 | 0 | 0 | 160 | **0** |

## Scenario Notes

- **`normal_mix`** (75% valid multimodal human flows + 25% automated headless bot probes): 30/30 humans accepted; 0/10 bots reached API.
- **`protected_endpoint_flood`** (Flood of plain HTTP requests to /portal-api/* (no token or forged token)): 100% rejected at token verification gate with HTTP 401.
- **`nonce_flood`** (Flood of GET /v1/nonce from single IP/session (cap=60/min)): First 60 issued (200); remaining 90 throttled (429).
- **`malformed_assess_flood`** (Flood of oversized (>64 KB), schema-violating, and forged-nonce /v1/assess payloads): Rejected immediately via 413 (oversize), 422 (schema/privacy), and 401 (nonce); 0 tokens issued.

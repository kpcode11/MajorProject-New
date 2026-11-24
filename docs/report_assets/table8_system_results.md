# System-Level Evaluation Results (`results/system/system_results.md`)

> **Methodological Note:** All models (`mouse-v1`, `keyboard-v1`, `fusion-v1`) and
> rule weights (`backend/config/rules.yaml`) were frozen prior to simulator and
> latency benchmarking. No model, feature, or threshold was tuned on the simulator.

## 1. Server Scoring Latency Distribution & Throughput (`n = 1,000` calls)

| Metric | Value | Unit | Target | Notes |
| :--- | ---: | :--- | :--- | :--- |
| `server_scoring_p50_ms` | 1.6498 | ms | <= 200.0 ms (p95) | n_calls=1000 multimodal ONNX+rules |
| `server_scoring_mean_ms` | 3.0707 | ms | <= 200.0 ms (p95) | Mean scoring time per /v1/assess payload |
| `server_scoring_p95_ms` | 15.1606 | ms | <= 200.0 ms | Passes p95 < 200 ms criterion |
| `server_scoring_p99_ms` | 22.0690 | ms | <= 200.0 ms | min=1.4755 ms, max=36.7004 ms |
| `single_worker_scoring_throughput_rps` | 325.5800 | requests/sec | >= 50.0 req/s | total_elapsed_s=3.0714 |
| `sdk_esm_gzip_kb` | 16.2200 | KB | <= 30.0 KB | Zero runtime dependencies |
| `sdk_umd_gzip_kb` | 14.8600 | KB | <= 30.0 KB | Zero runtime dependencies |
| `axe_core_total_violations` | 0.0000 | count | 0 violations | Audited 11 portal & modal states |

## 2. Simulator Outcomes & Per-Tier Latency Distribution (`n = 200` sessions)

| Mode | Tier | Total | Allowed | Challenged | Denied | Blocked at API | Caught Rate | p50 Latency (ms) | Mean Latency (ms) | p95 Latency (ms) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `off` | `tier1` | 25 | 25 | 0 | 0 | 0 | 0.0% | 0.52 | 2.58 | 8.26 |
| `off` | `tier2` | 25 | 25 | 0 | 0 | 0 | 0.0% | 2.67 | 3.13 | 6.91 |
| `off` | `tier3` | 25 | 25 | 0 | 0 | 0 | 0.0% | 4.67 | 5.80 | 12.60 |
| `off` | `tier4` | 25 | 25 | 0 | 0 | 0 | 0.0% | 5.73 | 6.21 | 10.75 |
| `passive` | `tier1` | 25 | 0 | 0 | 6 | 19 | 100.0% | 0.48 | 1.14 | 3.69 |
| `passive` | `tier2` | 25 | 0 | 2 | 23 | 0 | 100.0% | 1.82 | 2.02 | 3.19 |
| `passive` | `tier3` | 25 | 0 | 2 | 23 | 0 | 100.0% | 4.37 | 4.51 | 7.42 |
| `passive` | `tier4` | 25 | 2 | 3 | 20 | 0 | 92.0% | 4.99 | 5.89 | 10.27 |

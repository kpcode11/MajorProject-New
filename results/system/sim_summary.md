# Bot Simulator Summary Report (`results/system/sim_summary.md`)

> **Methodological Note (Non-Generalisation Disclaimer):**
> All machine learning models (`mouse-v1` LightGBM, `keyboard-v1` Logistic Regression,
> `fusion-v1` stacking combiner) and rule weights (`backend/config/rules.yaml`) were
> trained and frozen prior to Phase 7 on held-out public dataset splits. **No model,
> feature, or threshold was tuned on the Phase 7 simulator.** The numbers below
> document end-to-end system verification against the local mock portal
> (`results/system/sim_runs.jsonl`, `seed=42`) and must not be reported
> as statistical generalisation benchmarks.

- **Total simulated sessions:** `200`
- **Source log:** `results/system/sim_runs.jsonl`
- **Random seed:** `42`

## 1. Outcomes by Protection Mode and Bot Tier

| Protection Mode | Tier | Description | Total | Allowed | Challenged | Denied | Blocked at API | Blocked/Challenged Rate | Mean Latency (ms) |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `off` | `tier1` | Plain HTTP client posting directly to `/portal-api/*` (no browser) | 25 | 25 (100.0%) | 0 | 0 | 0 | 0.0% | 2.58 |
| `off` | `tier2` | Playwright (default headless settings) performing direct fills and clicks | 25 | 25 (100.0%) | 0 | 0 | 0 | 0.0% | 3.13 |
| `off` | `tier3` | Playwright with basic automation-hiding context adjustments (`webdriver=false`) | 25 | 25 (100.0%) | 0 | 0 | 0 | 0.0% | 5.80 |
| `off` | `tier4` | Playwright with Appendix D.3 Bezier mouse paths + randomised typing delays | 25 | 25 (100.0%) | 0 | 0 | 0 | 0.0% | 6.21 |
| `passive` | `tier1` | Plain HTTP client posting directly to `/portal-api/*` (no browser) | 25 | 0 (0.0%) | 0 | 6 | 19 | 100.0% | 1.14 |
| `passive` | `tier2` | Playwright (default headless settings) performing direct fills and clicks | 25 | 0 (0.0%) | 2 | 23 | 0 | 100.0% | 2.02 |
| `passive` | `tier3` | Playwright with basic automation-hiding context adjustments (`webdriver=false`) | 25 | 0 (0.0%) | 2 | 23 | 0 | 100.0% | 4.51 |
| `passive` | `tier4` | Playwright with Appendix D.3 Bezier mouse paths + randomised typing delays | 25 | 2 (8.0%) | 3 | 20 | 0 | 92.0% | 5.89 |

## 2. Passive Mode Breakdown by Protected Portal Action

| Action | Sensitivity | Total | Allowed | Challenged | Denied | Blocked at API |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `otp_request` | `high` | 64 | 1 | 3 | 50 | 10 |
| `details_update` | `high` | 12 | 0 | 0 | 8 | 4 |
| `centre_search` | `medium` | 24 | 1 | 4 | 14 | 5 |

## 3. Tier-by-Tier Observations

1. **Unprotected Mode (`protection_mode=off`):**
   - All four bot tiers (`tier1`–`tier4`) succeed on `100.0%` (`25/25`) of requests
     when `require_human_token` enforcement is bypassed.
2. **Tier 1 (`tier1` — Plain HTTP Client, `protection_mode=passive`):**
   - Direct `/portal-api/*` POSTs without a browser or token are rejected at the API
     gateway (`401 Unauthorized`, `blocked-at-api`), while plain-HTTP `/v1/assess`
     probes with empty telemetry fire `R01_NO_PAYLOAD` (`w=0.80`) and are `denied`.
3. **Tier 2 (`tier2` — Default Playwright, `protection_mode=passive`):**
   - Default headless Playwright leaves `navigator.webdriver=true` (`R02_WEBDRIVER`),
     software WebGL (`R06_SOFTWARE_RENDERER`), `0` desktop plugins
     (`R07_ZERO_PLUGINS_DESKTOP`), and zero mouse/keystroke trajectory points on
     direct `page.fill()` / `page.click()`, resulting in `0/25` allowed (`23 denied`,
     `2 challenged`).
4. **Tier 3 (`tier3` — Stealth-Adjusted Playwright, `protection_mode=passive`):**
   - Hiding `navigator.webdriver` bypasses `R02_WEBDRIVER`, but cross-signal
     inconsistencies (`R03`–`R10`) and collinear constant-velocity mouse steps /
     fixed-interval typing are caught by the rule and behavioural layers (`0/25`
     allowed: `23 denied`, `2 challenged`).
5. **Tier 4 (`tier4` — Appendix D.3 Bezier + Randomised Typing, `protection_mode=passive`):**
   - Even with cubic Bezier paths, smoothstep easing, Gaussian jitter, and randomised
     keystroke timings, the untuned multimodal scorer + step-up flow denies `20/25`
     and challenges `3/25` sessions, while `2/25` (`8.0%`) pass after satisfying
     both low-risk trajectory statistics and the step-up hold duration requirement.

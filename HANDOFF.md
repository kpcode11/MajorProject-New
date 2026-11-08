# Handoff

**Updated:** 2026-11-08 21:20  |  **By:** Antigravity  |  **Branch:** phase-6-browser-sdk  |  **Last commit:** see `git log -1`

## Current task
- ID: P7-01 — Demo portal scaffold (`portal/`)
- State: not started (`TODO`; Phase 6 is complete and ready for human review / merge to `main`, then create `phase-7-mock-portal`)

## Done in Phase 6 (P6-01..P6-13 all DONE)
- **P6-01 (`9f0c704`):** `sdk/` package (Vite 8 ES + UMD, TS 6 strict, vitest 5 + happy-dom, ESLint 10 + Prettier), `config.ts`, CI `sdk` job, `scripts/tasks.py` integration.
- **P6-02 (`d1f02a4`):** `collectors/env.ts` (coarse Appendix B.2 snapshot, `deviceClass()`).
- **CI fix (`c476a63`):** track small `backend/models/**/*.onnx`; ignore `*.db`.
- **P6-03 (`8b92328`):** `ringbuffer.ts`, `collectors/mouse.ts` (`MouseCollector`).
- **P6-04 (`115c28f`):** `collectors/keyboard.ts` (`KeyboardCollector`, `keyClass`). Backend `KeyBehaviour` gained `untrusted_count`.
- **P6-05 (`714e96c`):** `collectors/scroll.ts` (`ScrollCollector`) and `collectors/timing.ts` (`TimingCollector`).
- **P6-06 (`044bd2c`):** `src/transport.ts` (`fetchNonce`, `buildAssessPayload`, `buildChallengePayload`, `postAssess`, `postChallenge`, `safeAssess`, `safeSubmitChallenge`, `BotGuardTransportError`).
- **P6-07 (`b7676cb`):** `src/index.ts` (`BotGuardClient` class and `BotGuard` singleton facade).
- **P6-08 (`6c46c30`):** `src/challenge.ts` (`renderPressHoldChallenge`, `createChallengeHandler`, `defaultPressHoldRenderer`, `BotGuardChallengeCancelledError`).
- **P6-09 (`1417f3f`):** `src/react/index.tsx` (`BotGuardProvider` and `useBotGuard()` hook exported at `@botguard/sdk/react`).
- **P6-10 (`30a8a73`):** `src/performance.ts` (`scheduleIdleTask`, `createThrottleGate`) and stress/listener-leak tests.
- **P6-11 (`b03e6c3`):** Comprehensive SDK privacy, bounding, stress, and cleanup test suite (`sdk/test/sdk_suite.test.ts`).
- **P6-12 (`0ae5bef`):** `sdk/scripts/size-report.mjs` and `results/system/sdk_size.json` (ESM = `10.90 KB` gzip, UMD = `10.05 KB` gzip, React = `1.02 KB` gzip — all < 30 KB target).
- **P6-13:** `scripts/export_backend_json_schema.py`, `data/fixtures/backend_contract_schema.json`, `data/fixtures/sdk_sample_payloads.json`, `sdk/test/contract.test.ts`, and `backend/tests/test_sdk_contract.py` (100 SDK tests across 12 suites + 338 backend tests + 66 ML tests all pass).

## Exact next step
- Review and merge `phase-6-browser-sdk` into `main` (or create `phase-7-mock-portal`), read `docs/plan/phase_7.md`, and start `P7-01` (`Demo portal scaffold`).

## Files touched (recent)
- `scripts/export_backend_json_schema.py`, `data/fixtures/backend_contract_schema.json`, `data/fixtures/sdk_sample_payloads.json`, `sdk/test/contract.test.ts`, `backend/tests/test_sdk_contract.py` (new); `PROGRESS.md`; `HANDOFF.md`

## Commands to run first
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast
    cd sdk; npm run build

## Known problems / gotchas
- Run `npm` only from `sdk/`. Git writes need elevated permission in the agent sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

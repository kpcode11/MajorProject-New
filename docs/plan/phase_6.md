## Phase 6 — Browser SDK

**Goal:** A small TypeScript SDK that collects the signals of Appendix B.2/B.3, talks to the backend, and exposes a clean API plus a React wrapper.

### Tasks

- [ ] **P6-01** Create the `sdk/` package skeleton (Vite + TypeScript + vitest + ESLint), add a Node job to CI, then write `config.ts`: defaults (window length, max points, throttle interval, endpoints).
- [ ] **P6-02** `collectors/env.ts`: environment snapshot (Appendix B.2). Coarsen values (buckets, class labels). **No persistent fingerprint hash.**
- [ ] **P6-03** `collectors/mouse.ts`: `mousemove` (throttled to about 60 Hz), `mousedown/up`, `click`, `wheel`; record `isTrusted`; bounded ring buffer; output downsampled `(x, y, t)` plus counts of untrusted events.
- [ ] **P6-04** `collectors/keyboard.ts`: `keydown/keyup` timing with **key class only** (map in code; never store `event.key` or `event.code`); paste/autofill event counts only; no access to input values.
- [ ] **P6-05** `collectors/scroll.ts` and `collectors/timing.ts`: scroll summary, focus/blur/visibility transitions, time from page load to first interaction and to action.
- [ ] **P6-06** `transport.ts`: fetch nonce, build payload, POST to `/v1/assess`, handle errors, retries with backoff, timeouts; never block the host page.
- [ ] **P6-07** `index.ts`: public API `BotGuard.start()`, `assess(action)`, `runChallenge()`, `stop()`; idempotent and safe to call multiple times.
- [ ] **P6-08** `challenge.ts`: renders a pluggable step-up UI (Phase 7 provides the default implementation).
- [ ] **P6-09** `react/`: `BotGuardProvider` and `useBotGuard()` hook.
- [ ] **P6-10** Performance work: passive listeners; throttle; aggregation in `requestIdleCallback` or a Web Worker; bounded buffers; `stop()` removes all listeners and clears memory.
- [ ] **P6-11** Tests (vitest + jsdom/happy-dom): collectors produce bounded output; key collector never exposes characters (assert on serialised payload); throttling works; payload size under the 64 KB limit in a stress test; `stop()` leaves no listeners.
- [ ] **P6-12** Bundle: ES module and UMD; report gzipped size in `results/system/sdk_size.json` (target under 30 KB core).
- [ ] **P6-13** Contract test: the SDK's payload validates against the backend's Pydantic schema (generate a JSON Schema from the backend and validate SDK-produced payloads in a test).

### Acceptance criteria

- [ ] `npm test` passes in `sdk/`.
- [ ] Contract test passes.
- [ ] Serialised payloads contain no characters typed and no input values (test with a form field filled with a known string; assert the string never appears).
- [ ] Bundle size reported.

---

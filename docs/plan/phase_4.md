## Phase 4 — Environment rule layer

**Goal:** Deterministic, explainable checks that need no dataset. They catch trivial automation and feed the final decision.

### Tasks

- [x] **P4-01** Define the environment payload schema (`backend/app/schemas.py: EnvSignals`) with the fields in Appendix B.2.
- [x] **P4-02** Implement `rules.py` with each rule as a small pure function returning `RuleResult(id, fired: bool, weight: float, reason: str)`:

| Rule id | Condition (examples) | Default weight |
|---------|----------------------|----------------|
| R01_NO_PAYLOAD | No behaviour/environment payload at all | strong |
| R02_WEBDRIVER | `webdriver == true` | strong |
| R03_UA_PLATFORM_MISMATCH | UA OS family inconsistent with `platform` | medium |
| R04_UA_HINTS_MISMATCH | UA vs client-hints brand/version inconsistent | medium |
| R05_TZ_LANG_MISMATCH | Timezone and language list implausible together (soft) | weak |
| R06_SOFTWARE_RENDERER | WebGL renderer class is a software renderer | weak/medium |
| R07_ZERO_PLUGINS_DESKTOP | Desktop UA with zero plugins and other flags | weak |
| R08_VIEWPORT_ANOMALY | Outer window size zero or viewport larger than screen | medium |
| R09_TOUCH_INCONSISTENT | Touch events vs claimed device class mismatch | weak |
| R10_NATIVE_FUNCTION_TAMPER | Native-function integrity check failed | medium |
| R11_UNTRUSTED_EVENTS | High fraction of `isTrusted == false` input events | strong |
| R12_TOO_FAST | Time from nonce issue to action under a plausible minimum | medium |
| R13_RATE_LIMIT | Request-rate caps exceeded (server-side, Store) | hard |

- [x] **P4-03** Combine rule weights into a **rule score** in [0, 1] (documented formula) and a list of reasons. A hard rule (R13, invalid nonce/signature) bypasses the model.
- [x] **P4-04** Make weights configurable in `backend/config/rules.yaml`.
- [ ] **P4-05** Tests: one passing and one failing payload per rule; a "normal Chrome on Windows" fixture must produce rule score near 0; a "headless default" fixture must fire several rules.
- [ ] **P4-06** Document each signal and its privacy class in `docs/signals.md`.
- [ ] **P4-07** Optional baseline: compare against the open-source BotD library's verdicts on the same fixtures (only as an offline comparison; do not add it as a runtime dependency without a decision-log entry).

### Acceptance criteria

- [ ] All rule tests pass.
- [ ] A fixture list shows expected rule outcomes in `docs/signals.md`.
- [ ] No rule uses persistent identifiers or a unique fingerprint hash.

---

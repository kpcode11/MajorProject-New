# HANDOFF.md

- **Last updated:** 2026-11-23
- **Branch:** `main`
- **Current phase:** Phase 10 — Final evaluation, documentation, and release (`docs/plan/phase_10.md`)
- **Last completed tasks:** `P10-09` (Claims checker, `385510b`), `P10-11` (Release metadata: MIT `LICENSE`, `CITATION.cff`, git tag `v1.0.0`), `P10-12` (Portal UI design system)
- **Remaining TODO task:** `P10-10` — Demo-video script (`docs/demo_script.md`; human records the video `[HUMAN]`)

## What was just done
- **P10-09 (`385510b`):** Added `scripts/check_claims.py`, wired it into `.github/workflows/ci.yml`, added 3 tests in `ml/tests/test_check_claims.py`, fixed stale keyboard hyperparameters in `docs/model_card.md` and unbacked table cells in `README.md`, and saved `results/system/claims_check.json`.
- **P10-11:** Added MIT `LICENSE`, CFF 1.2.0 `CITATION.cff` (`v1.0.0`), updated `README.md` licence/citation links, verified `check_claims.py` + `lint` + `test-fast`, committed, and created annotated git tag `v1.0.0`.
- **P10-12 (`e3a70c4`):** Applied the shared portal design contract in `portal/Design.md` to the resident portal shell and landing page. Added semantic CSS variables, responsive service cards, accessible focus treatment, reduced-motion support, and kept all existing navigation/test contracts intact. Verified portal tests, typecheck, lint, and production build.
- **Impeccable polish (`03eae57`):** Removed the overused Inter font finding and unified Resident login, Update details, and Centre search with the portal token and component styles. Verified desktop/mobile renders at 1440×900 and 390×844, then ran the Impeccable detector (0 findings), portal tests/lint/build, and the repository fast suite.
- **Theme polish:** Added persisted light/dark theme switching, normalized portal typography and line-height, and replaced the security console's black card treatment with warmer neutral surfaces. Verified 24 portal tests, accessibility contrast, lint, build, detector, and fast-suite checks.

## Exact next step
1. Complete `P10-10` (`docs/demo_script.md`) if desired, and obtain `[HUMAN]` sign-off on final results text and demo recording.
2. Push the portal UI commit and `v1.0.0` tag when ready.

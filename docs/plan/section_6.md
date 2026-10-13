## 6. Phase overview and milestones

| Phase | Name | Needs datasets? | Can an agent start without human help? |
|-------|------|-----------------|----------------------------------------|
| 0 | Scaffolding and handoff system | no | yes |
| 1 | Dataset access, inventory and audit (mouse) | yes (mouse) | yes, except `[HUMAN]` items |
| 2 | Mouse model | yes | yes |
| 3 | Keyboard model and desktop fusion | yes (Aalto) | yes |
| 4 | Environment rule layer | no | yes (can run in parallel with 1-3) |
| 5 | Scoring backend | models from 2-3 | yes |
| 6 | Browser SDK | no (needs backend schema) | yes |
| 7 | Mock portal, step-up, simulator, desktop end-to-end | no | yes |
| 8 | Mobile extension (decision gate) | gated | needs `[HUMAN]` decision |
| 9 | Dashboard, privacy, accessibility | no | yes |
| 10 | Final evaluation, documentation, release | all | yes |

**Milestones:** M1 after Phase 3 (offline models); **M2 after Phase 7 (desktop MVP; the minimum acceptable deliverable)**; M3 after Phase 8; M4 after Phase 10.

**If free-tier budgets are tight,** the shortest path to a defensible project is: Phases 0, 1, 2, 3 (with small samples), 4, 5, 6, 7, then 10 (reduced). Phases 8 and 9 are extensions.

---

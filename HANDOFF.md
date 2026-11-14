# Handoff

**Updated:** 2026-11-14 14:36  |  **By:** Cursor Grok  |  **Branch:** phase-9-dashboard-privacy  |  **Last commit:** see `git log -1`

## Current task
- ID: P9-03 — Dashboard tests
- State: `DONE` (next task is **P9-04** — `Retention purge`)

## Done in Phase 9 so far
- Recorded human decision in `docs/decision_log.md` to skip Phase 8 (`P8-*` marked `SKIPPED`) and proceed to Phase 9 using `supabase/DESIGN.md` for the Admin Dashboard UI.
- **P9-01 (`c7073d9`):** Admin API (`backend/app/admin.py`) protected by `ADMIN_API_KEY`.
- **P9-02 (`affede1`):** Six Admin Dashboard views in `portal/src/pages/AdminDashboardPage.tsx`.
- **P9-03:** Dashboard component tests in `portal/test/dashboard.test.tsx` (all 6 views, fp/fn marking, purge, portal-shell smoke) plus `backend/tests/test_dashboard_smoke.py` verifying the dashboard's `/admin/*` GETs/POSTs against `_AsgiTestClient`. Lint and `python scripts/tasks.py test-fast` passed.

## Exact next step
- Start **P9-04** (`Retention purge`): implement `retention.py` as a scheduled purge (cron-like background task or CLI) that deletes stored feature JSON older than the configured TTL (default 7 days) and anonymises or deletes assessments older than the long-term TTL; unit-test with a fake clock.

## Files touched (recent)
- `portal/test/dashboard.test.tsx`, `backend/tests/test_dashboard_smoke.py`, `PROGRESS.md`, `HANDOFF.md`

## Commands to run first
    python scripts/status.py
    python scripts/tasks.py lint
    python scripts/tasks.py test-fast

## Known problems / gotchas
- Always use `_AsgiTestClient` from `test_api.py` in backend unit tests (never `fastapi.testclient.TestClient`, which hangs inside the Windows sandbox due to `anyio` socketpair creation).
- Run `npm` inside `sdk/` or `portal/`, never the repository root.
- Git writes require elevated permissions outside the sandbox.

## Dataset / long-job state
- None.

## Questions for the human
- None.

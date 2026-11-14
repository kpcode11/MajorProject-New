# Handoff

**Updated:** 2026-11-14 14:10  |  **By:** Antigravity  |  **Branch:** phase-9-dashboard-privacy  |  **Last commit:** see `git log -1`

## Current task
- ID: P9-01 — Admin API (`/admin/overview`, `/admin/scores`, `/admin/assessments`, `/admin/assessments/{id}`, `/admin/feedback`, `/admin/sim-results`, `/admin/privacy`)
- State: `DONE` (next task is **P9-02** — `Admin dashboard`)

## Done in Phase 9 so far
- Recorded human decision in `docs/decision_log.md` to skip Phase 8 (`P8-*` marked `SKIPPED` in `PROGRESS.md`) and proceed directly to Phase 9 (`phase-9-dashboard-privacy`), using `supabase/DESIGN.md` for the Phase 9 Admin Dashboard UI (`P9-02`).
- **P9-01:** Added `ADMIN_API_KEY` in `backend/app/config.py`, `backend/app/admin.py` (`create_admin_router`, `require_admin_api_key`), derived feature propagation in `backend/app/scoring.py` and `backend/app/main.py`, feedback/purge helpers in `backend/app/db.py`, and 4 unit tests in `backend/tests/test_admin_api.py`.

## Exact next step
- Start **P9-02** (`Admin dashboard`): build the React + Recharts Admin Dashboard views styled strictly according to `supabase/DESIGN.md` (`#3ecf8e` primary emerald with `#171717` near-black text on primary, `#ffffff` canvas, `#fafafa` canvas-soft, `#1c1c1c` canvas-night for code/featured panels, `#dfdfdf` 1px hairlines, 6px button radius, 12px card radius, weight 500 tight display headings):
  1. Overview: requests per minute, allow/challenge/deny split, latency, model versions.
  2. Score distribution histogram with threshold lines.
  3. Session detail: decision, band, rules fired, top contributing features (derived values only, no raw traces).
  4. Simulator results per tier (from `/admin/sim-results`).
  5. Feedback queue: mark "false positive / false negative" (stored, never auto-used for training).
  6. Privacy panel: retention settings, record counts, last purge.

## Files touched (recent)
- `backend/app/admin.py`, `backend/tests/test_admin_api.py` (new); `backend/app/config.py`, `backend/app/db.py`, `backend/app/scoring.py`, `backend/app/main.py`, `backend/tests/test_api.py`, `docs/decision_log.md`, `PROGRESS.md`, `HANDOFF.md`

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

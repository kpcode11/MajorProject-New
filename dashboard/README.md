# BotGuard Operational Admin Dashboard (`Phase 9`)

The React + Recharts-compatible Admin Dashboard (`P9-02`) is served inside the Vite application at [`portal/src/pages/AdminDashboardPage.tsx`](../portal/src/pages/AdminDashboardPage.tsx) (`http://127.0.0.1:5173/?page=admin` or via the **Admin dashboard** navigation tab) and styled using [`supabase/DESIGN.md`](../supabase/DESIGN.md) tokens ([`portal/src/designTokens.ts`](../portal/src/designTokens.ts)).

## Views Implemented (`P9-02`)
1. **Overview (`GET /admin/overview`)**: Requests per minute, allow/challenge/deny split, scoring latency (`mean`, `p50`, `p95`), and loaded ONNX model versions (`mouse`, `keyboard`, `fusion`, `touch`).
2. **Score Distribution Histogram (`GET /admin/scores`)**: Stacked bar histogram across `[0.0, 1.0]` with vertical policy threshold reference lines (`allow_below`, `deny_at_or_above`).
3. **Session Detail & Derived Feature Inspector (`GET /admin/assessments`, `GET /admin/assessments/{id}`)**: Per-session decision, risk band, fired rules, top contributing derived numerical features (never raw coordinate/keystroke traces), and step-up challenge outcome.
4. **Bot Simulator Results per Tier (`GET /admin/sim-results`)**: Stacked bar chart and table of outcomes across Tiers 1–4 (`off` vs `passive` mode) from `results/system/sim_runs.jsonl`.
5. **Analyst Feedback Queue (`GET /admin/feedback`, `POST /admin/feedback`)**: Mark or clear false positive (`fp`) / false negative (`fn`) labels (stored for offline review only; never auto-used for training).
6. **Privacy & Retention Panel (`GET /admin/privacy`, `POST /admin/privacy/purge`)**: Feature/assessment TTL settings, live record counts, last purge status, and manual retention purge trigger.

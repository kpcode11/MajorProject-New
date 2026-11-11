# Live Demonstration Script — Passive Bot Detection (Phase 7, P7-20)

> **IMPORTANT DISCLAIMER:**
> The mock portal is strictly an academic research demonstration (**"DEMO — not a government portal"**) for SIH1672. Never enter real Aadhaar numbers or personal identifiers. The bot simulator enforces a strict host allowlist (`simulator/allowlist.txt` via `simulator/safety.py`) and refuses any non-local or `.gov` / `.nic.in` / `uidai` target.

---

## 1. Quick Start (`python scripts/tasks.py demo`)

From the repository root, start both the FastAPI scoring/token backend (`http://127.0.0.1:8000`) and the React + Vite mock resident portal (`http://127.0.0.1:5173`) with a single command:

```powershell
python scripts/tasks.py demo
```

By default, `demo` uses:
- `PROTECTION_MODE=passive`
- `STORE_BACKEND=memory` (in-memory nonce, challenge, JTI, and sliding-window rate-limit store)
- `DATABASE_URL=sqlite:///./botguard.db` (local SQLite audit database)

### Optional Redis + PostgreSQL Profile

To run with Redis (`127.0.0.1:6379`) and PostgreSQL (`127.0.0.1:5432`) via Docker Compose:

```powershell
docker compose -f deploy/docker-compose.yml --profile infra up -d
$env:STORE_BACKEND="redis"
$env:REDIS_URL="redis://127.0.0.1:6379/0"
$env:DATABASE_URL="postgresql+psycopg://botguard:botguard_local_dev@127.0.0.1:5432/botguard"
python scripts/tasks.py demo
```

---

## 2. Scene 1 — Unprotected Portal (`PROTECTION_MODE=off`)

1. Start the demo with passive protection turned **off**:
   ```powershell
   python scripts/tasks.py demo --protection-mode off
   ```
2. Check the portal call statistics endpoint:
   ```powershell
   curl http://127.0.0.1:8000/portal-api/stats
   ```
   Verify `"protection_mode": "off"`.
3. Send a direct Tier 1 plain-HTTP POST to `/portal-api/otp/request` with **no** browser and **no** `X-Human-Token` header:
   ```powershell
   backend\.venv\Scripts\python.exe -c "from simulator.tier1_http import run_tier1_session; print(run_tier1_session('http://127.0.0.1:8000', protection_mode='off').to_dict())"
   ```
   - **Expected outcome:** `portal_status: 200`, `outcome: "allowed"`. Without passive token verification, automated scripts can abuse `/portal-api/otp/request` freely.

---

## 3. Scene 2 — Protected Portal (`PROTECTION_MODE=passive`) & Real Human Walkthrough

1. Restart the demo in default **passive** protection mode:
   ```powershell
   python scripts/tasks.py demo --protection-mode passive
   ```
2. Open `http://127.0.0.1:5173` in a desktop browser:
   - Point out the top banner: **`DEMO — not a government portal`** and the live status badge **`Passive BotGuard: Active`**.
3. **Resident Login (`otp_request` — high sensitivity):**
   - Click **Resident login** (`[data-testid="nav-login"]`).
   - Move the mouse naturally to the **Mock Resident Identifier** input (`[data-testid="identifier-input"]`), type `9999-0000-1234`, and click **Send OTP** (`[data-testid="send-otp-btn"]`).
   - **Expected outcome:** Passive assessment (`GET /v1/nonce` -> `POST /v1/assess`) returns `decision: "allow"` (`band: "low"`) with a single-use `X-Human-Token` JWT, and `/portal-api/otp/request` responds `200 OK` (`OTP Dispatched (Demo)`) with zero visual puzzles.
   - **Privacy verification (DevTools Network tab):** Inspect the `POST /v1/assess` and `POST /portal-api/otp/request` payloads:
     - `/v1/assess` contains only `[x, y, t_ms]` coordinates and `[key_class, down_ms, up_ms]` timings (`"digit"`, `"punct"`)—never the typed characters.
     - `/portal-api/otp/request` contains only `{"action": "otp_request", "identifier_length": 14}`.
4. **Update Details (`details_update`) & Centre Search (`centre_search`):**
   - Switch to **Update details** (`[data-testid="nav-update-details"]`), fill synthetic demographic fields, check the confirmation box, and click **Submit Update Request**.
   - Switch to **Centre search** (`[data-testid="nav-centre-search"]`), enter `560001`, and click **Search Centres**.

---

## 4. Scene 3 — Keyboard-Only Accessibility & Step-Up Challenge

1. **Keyboard-only navigation (missing mouse modality != bot):**
   - Reload `http://127.0.0.1:5173/?page=login` without touching the mouse.
   - Use `Tab` to focus the identifier input, type `999900001234`, `Tab` to **Send OTP**, and press `Enter`.
   - Or run the scripted keyboard-only reference check (clearly labelled as a demo script, not a validation dataset):
     ```powershell
     backend\.venv\Scripts\python.exe -c "from simulator.reference_human import run_reference_human_session; print(run_reference_human_session('http://127.0.0.1:8000', mode='keyboard_only').to_dict())"
     ```
   - **Expected outcome:** The session is **never** automatically denied for lacking mouse events (`initial_decision` is `"allow"` or `"challenge"`).
2. **Accessible Press-and-Hold Step-Up UI (`[data-testid="stepup-dialog"]`):**
   - When a medium-risk session triggers `decision: "challenge"`, the modal dialog appears with:
     - `role="dialog"`, `aria-modal="true"`, focus trapped inside the dialog, and a high-contrast `:focus-visible` ring.
     - **Pointer path:** Press and hold `[data-testid="stepup-hold-btn"]` for the server-chosen random duration (`0.8–1.5 s`).
     - **Keyboard single-press alternative:** Focus `[data-testid="stepup-kb-btn"]` and press `Space` or `Enter` once (no countdown time pressure, no image or text puzzles).
   - Upon completion, `POST /v1/assess/challenge` issues a single-use `X-Human-Token` and the original portal request succeeds (`200 OK`).

---

## 5. Scene 4 — Bot Simulator Tiers 1–4 & Portal Statistics

1. Run the batch simulator across Tiers 1–4 (`off` vs `passive` protection modes):
   ```powershell
   backend\.venv\Scripts\python.exe simulator/run_all.py --n-per-tier 25 --seed 42
   ```
   - **Tier 1 (`simulator/tier1_http.py`):** Plain HTTP client posting directly to `/portal-api/*` without a browser or token -> `blocked-at-api` (`401`) or `denied`.
   - **Tier 2 (`simulator/tier2_playwright.py`):** Default headless Playwright performing direct `page.fill()` and `page.click()` -> caught by `R02_WEBDRIVER`, `R06_SOFTWARE_RENDERER`, `R07_ZERO_PLUGINS_DESKTOP`, and empty trajectory -> `denied` / `challenged`.
   - **Tier 3 (`simulator/tier3_stealth.py`):** Playwright with basic stealth init-script adjustments (`navigator.webdriver = false`) -> caught by environment consistency rules (`R03`–`R10`) and mechanical linear input -> `denied` / `challenged`.
   - **Tier 4 (`simulator/tier4_humanlike.py`):** Playwright with Appendix D.3 cubic Bezier mouse paths (smoothstep ease-in/out + Gaussian jitter) and randomised typing delays -> recorded in `results/system/sim_runs.jsonl` and summarised in `results/system/sim_summary.md`.
2. Inspect live accepted vs. rejected counters on the running backend:
   ```powershell
   curl http://127.0.0.1:8000/portal-api/stats
   ```
   Review `accepted`, `rejected`, `by_action`, and `by_reason` (`missing_token`, `invalid_or_replayed_token`, etc.).

# Passive BotGuard — Plug-and-Play Website Integration Guide

This guide explains how any developer or website owner can integrate **Passive BotGuard** into their own website or web application in **3 simple steps**, without modifying the BotGuard ML models or rule engine.

---

## 1. How the Architecture Works Across Multiple Websites

Passive BotGuard is designed as a **centralized security service** (`backend/`) paired with a **lightweight browser SDK** (`sdk/`):

```text
[ Your Website A (e.g. Login / Checkout) ] ──┐
[ Your Website B (e.g. Student Portal)   ] ──┼──► [ BotGuard FastAPI Backend (:8000) ]
[ Mock Citizen Portal (:5173)            ] ──┘             │
                                                           ▼
                                            [ Central Admin & Kinematics Console ]
                                            (http://127.0.0.1:5173/?page=admin)
```

1. **Browser SDK (`@botguard/sdk`, ~15 KB gzipped):** Runs passively in the user's browser on your website. It listens to mouse cursor kinematics, keystroke timing (`key_class` only — never characters), and browser environment integrity signals.
2. **Scoring Backend (`http://127.0.0.1:8000`):** Evaluates the 13 deterministic rules (`R01`–`R13`) + ONNX ML models (`mouse-v1`, `keyboard-v1`, `fusion-v1`) in `~1.65 ms` and returns:
   - `decision: "allow"` + a short-lived signed JWT (`token`) for real humans;
   - `decision: "challenge"` + `challenge` metadata when risk is ambiguous (the SDK automatically shows the accessible press-and-hold step-up modal);
   - `decision: "deny"` when automation is detected.
3. **Your Website's Backend:** Verifies the single-use `X-Human-Token` JWT with one HTTP call to `POST /v1/token/verify` before executing the sensitive action.
4. **Central Admin Console (`http://127.0.0.1:5173/?page=admin`):** Displays live requests, score histograms, fired rules, and the **User Kinematics & 13-Rule Inspector** for every connected website.

---

## 2. Step-by-Step Integration

### Step 1: Start the Central BotGuard Backend

In the Passive BotGuard repository root:

```powershell
python scripts/tasks.py serve
# Or launch both the backend (:8000) and the Admin Console (:5173/?page=admin):
python scripts/tasks.py demo
```

---

### Step 2: Add the Browser SDK to Your Frontend

#### Option A — Any Vanilla HTML / JavaScript Website (Using the UMD Bundle)

Build the SDK bundle once (`cd sdk && npm run build`), copy `sdk/dist/botguard.umd.cjs` (or serve it), and add 10 lines of JavaScript to your HTML form:

```html
<script src="/botguard.umd.cjs"></script>
<script>
  // 1. Start passive telemetry collection as soon as the page loads
  const guard = new window.BotGuard.BotGuardClient({
    endpoint: 'http://127.0.0.1:8000',
    sendRawTrace: true, // or false to extract all 151 features locally in the browser
  });
  guard.start({ prefetchNonce: true });

  // 2. Intercept your form submission
  document.getElementById('my-login-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    // Assess passive mouse + keyboard behaviour
    let res = await guard.assess('login');

    // If risk is medium, automatically run the accessible step-up challenge modal
    if (res.decision === 'challenge' && res.challenge) {
      res = await guard.runChallenge(res.challenge, 'login');
    }

    if (res.decision !== 'allow' || !res.token) {
      alert('Automated bot traffic blocked by Passive BotGuard.');
      return;
    }

    // 3. Submit your form to your own backend with X-Human-Token
    const response = await fetch('/api/my-login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Human-Token': res.token,
      },
      body: JSON.stringify({ username: document.getElementById('user').value }),
    });
  });
</script>
```

#### Option B — Any React / Vite / Next.js Application

Install or link `@botguard/sdk` and wrap your app in `BotGuardProvider`:

```tsx
import { BotGuardProvider, useBotGuard } from '@botguard/sdk/react';

export function App() {
  return (
    <BotGuardProvider options={{ endpoint: 'http://127.0.0.1:8000' }}>
      <LoginForm />
    </BotGuardProvider>
  );
}

function LoginForm() {
  const { assessWithStepUp } = useBotGuard();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Automatically assesses passive telemetry and opens the step-up modal only if needed
    const res = await assessWithStepUp('login');
    if (res.decision !== 'allow' || !res.token) {
      alert('Verification failed or bot detected.');
      return;
    }

    await fetch('/api/login', {
      method: 'POST',
      headers: { 'X-Human-Token': res.token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'login' }),
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="text" placeholder="Username" />
      <button type="submit">Sign In</button>
    </form>
  );
}
```

---

### Step 3: Verify the Human Token on Your Backend

When your backend receives a request on a protected route (e.g., `/api/login`), verify the `X-Human-Token` header by calling `POST http://127.0.0.1:8000/v1/token/verify`:

#### Python (FastAPI / Flask / Django) Example
```python
import httpx
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()
BOTGUARD_URL = "http://127.0.0.1:8000"

@app.post("/api/login")
async def login(x_human_token: str | None = Header(default=None)):
    if not x_human_token:
        raise HTTPException(status_code=401, detail="Missing X-Human-Token")

    async with httpx.AsyncClient() as client:
        verify_res = await client.post(
            f"{BOTGUARD_URL}/v1/token/verify",
            json={"token": x_human_token, "expected_action": "login"},
        )
        data = verify_res.json()

    if not data.get("valid"):
        raise HTTPException(status_code=401, detail=f"BotGuard rejected token: {data.get('reason')}")

    # Token is valid and single-use consumed! Proceed with your business logic.
    return {"status": "ok", "message": "Human verified!"}
```

#### Node.js (Express) Example
```javascript
app.post('/api/login', async (req, res) => {
  const token = req.headers['x-human-token'];
  const verifyRes = await fetch('http://127.0.0.1:8000/v1/token/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, expected_action: 'login' }),
  });
  const data = await verifyRes.json();

  if (!data.valid) {
    return res.status(401).json({ error: 'Bot blocked', reason: data.reason });
  }
  return res.json({ status: 'ok' });
});
```

---

## 3. Customizing Actions, Thresholds & Rules for Your Website

- **Add or tune action sensitivity classes:** Edit [backend/config/policy.yaml](file:///c:/Users/KESHAV/Documents/MajorProject/backend/config/policy.yaml):
  - `low` (`allow_below: 0.50`, `deny_at_or_above: 0.90`) — read-only pages, public search
  - `medium` (`allow_below: 0.30`, `deny_at_or_above: 0.80`) — login, directory search
  - `high` (`allow_below: 0.15`, `deny_at_or_above: 0.70`) — OTP requests, password/profile changes, payments
- **Enable/disable or re-weight the 13 deterministic rules (`R01`–`R13`):** Edit [backend/config/rules.yaml](file:///c:/Users/KESHAV/Documents/MajorProject/backend/config/rules.yaml).
- **Inspect every user's Mouse & Keyboard Kinematics live:** Open `http://127.0.0.1:5173/?page=admin` and click the **"User Kinematics & 13-Rule Inspector"** tab.

# Accessibility Audit & Screen-Reader Smoke Test Notes (`docs/accessibility.md`)

**Project:** Passive Bot Detection to Replace CAPTCHA (SIH1672)
**Tasks covered:** `P9-09` (`axe-core` & WCAG 2.1 AA audit), `P9-10` (Keyboard-only E2E login/OTP flow), `P9-11` (Screen-reader smoke test notes).

---

## 1. Automated Accessibility Audit Summary (`P9-09`)

Automated `axe-core` (`4.13.0`) and WCAG 2.1 AA relative-luminance contrast checks (`portal/test/accessibility.test.tsx`) run across **11 UI states** in CI (`results/system/axe_audit.json`):

| Audited Target / State | `axe-core` Violations | Critical / Serious | Minimum Text Contrast Ratio |
|------------------------|-----------------------|--------------------|-----------------------------|
| `landing` | `0` | `0 / 0` | `4.95 : 1` |
| `login:initial` | `0` | `0 / 0` | `4.95 : 1` |
| `login:validation_error` | `0` | `0 / 0` | `4.95 : 1` |
| `login:result` | `0` | `0 / 0` | `4.95 : 1` |
| `update-details:initial` | `0` | `0 / 0` | `4.95 : 1` |
| `update-details:validation_error` | `0` | `0 / 0` | `4.95 : 1` |
| `centre-search:initial` | `0` | `0 / 0` | `4.95 : 1` |
| `centre-search:validation_error` | `0` | `0 / 0` | `4.95 : 1` |
| `centre-search:results` | `0` | `0 / 0` | `4.95 : 1` |
| `admin-dashboard` | `0` | `0 / 0` | `4.74 : 1` |
| `stepup-challenge-dialog` | `0` | `0 / 0` | `4.95 : 1` |

---

## 2. Screen-Reader Smoke Test Notes (`P9-11`)

> **Methodology & Honesty Note:**
> Consistent with the project's reporting rules (`docs/MASTER_PLAN.md` Section 1.2), no external human participant study was conducted. Screen-reader compatibility was verified through:
> 1. **Automated Accessibility-Tree & Live-Region Smoke Tests** (`portal/test/accessibility.test.tsx` and `sdk/test/challenge.test.ts`), which inspect every landmark, accessible name/description (`aria-label`, `aria-labelledby`, `aria-describedby`), validation state (`aria-invalid`, `role="alert"`), and live status region (`role="status"`, `aria-live="polite"`, `role="progressbar"`).
> 2. **Windows Narrator / NVDA Interactive Walkthrough Checklist** on Windows desktop (`http://127.0.0.1:5173`), documented below so any evaluator with NVDA (`Insert+N`) or Windows Narrator (`Win+Ctrl+Enter`) can reproduce the exact announcement sequence in under 2 minutes.

### 2.1 Landmark & Navigation Announcements

| Step | User / Screen-Reader Action | DOM Element & ARIA Attributes | Expected / Verified Screen-Reader Announcement |
|------|-----------------------------|-------------------------------|------------------------------------------------|
| 1 | First `Tab` on page load | `<a href="#portal-main-content" class="portal-skip-link">` | *"Skip to main content, link"* — pressing `Enter` moves focus directly to `<main id="portal-main-content" tabindex="-1">`. |
| 2 | Navigate by landmarks (`D` in NVDA / `CapsLock+D` in Narrator) | `<div role="region" aria-label="Demonstration disclaimer">`, `<header>`, `<nav aria-label="Portal sections">`, `<main id="portal-main-content">`, `<footer>` | All 5 top-level landmarks are distinctly named and reachable without reading repetitive header text. |
| 3 | `Tab` across `<nav aria-label="Portal sections">` buttons | `<button aria-current="page">Overview</button>` $\to$ `<button>Resident login</button>` | Active page button announces *"current page, button"*; inactive buttons announce their section name and *"button"*. |
| 4 | Status badge updates after passive assessment | `<div data-testid="botguard-status" aria-live="polite">` | Announces *"Passive BotGuard: Active — Last decision: allow (low)"* politely without interrupting active form speech. |

### 2.2 Resident Login & Form Error Announcements

| Step | User / Screen-Reader Action | DOM Element & ARIA Attributes | Expected / Verified Screen-Reader Announcement |
|------|-----------------------------|-------------------------------|------------------------------------------------|
| 1 | `Tab` to identifier field on **Resident login** | `<input id="resident-identifier" aria-describedby="resident-identifier-hint">` + `<label for="resident-identifier">` | Announces label *"Mock Resident Identifier, edit text"* followed by hint *"Enter a synthetic mock identifier… Do not enter any real Aadhaar or government ID number."* |
| 2 | Press `Enter` with fewer than 4 characters | `<input aria-invalid="true" aria-describedby="resident-identifier-hint login-validation-error">` + `<p id="login-validation-error" role="alert">` | `role="alert"` immediately announces *"Please enter at least 4 characters for the mock identifier."* and marks the input *"invalid entry"*. |
| 3 | Type `9999-0000-1234` and press `Enter` | `<div role="status" data-testid="otp-result">` | Announces *"OTP Dispatched (Demo): Synthetic OTP dispatched for verified human session."* |

### 2.3 Step-Up Challenge Dialog Announcements (`@botguard/sdk`)

When a session scores in the `medium` risk band (`decision: "challenge"`), the SDK mounts the accessible step-up verification modal (`sdk/src/challenge.ts`):

| Step | User / Screen-Reader Action | DOM Element & ARIA Attributes | Expected / Verified Screen-Reader Announcement |
|------|-----------------------------|-------------------------------|------------------------------------------------|
| 1 | Modal opens | `<div role="dialog" aria-modal="true" aria-labelledby="botguard-challenge-title" aria-describedby="botguard-challenge-desc">` | Announces dialog title *"Quick Verification Required, dialog"* and description *"Please press and hold the button below for X.X seconds to continue."* Focus automatically lands on `[data-testid="stepup-hold-btn"]`. |
| 2 | Hold `Space`/`Enter` on **Press and Hold to Verify** | `<div role="status" aria-live="polite" data-testid="stepup-status">` + `<div role="progressbar" aria-valuemin="0" aria-valuemax="900" aria-valuenow="...">` | Live region announces *"Holding… keep pressing."* $\to$ when `hold_ms` is reached, announces *"Hold complete — release to finish."* and updates button label to *"Release to Complete"*. |
| 3 | Early release before `hold_ms` | `<div role="status" aria-live="polite">` | Announces *"Released too early (N ms). Please hold for X.X s."* and resets progress bar `aria-valuenow="0"`. |
| 4 | `Tab` to **Use Keyboard Single-Press Verify** and press `Space` or `Enter` once | `<button data-testid="stepup-kb-btn" aria-label="Use Keyboard Single-Press Verify (Keyboard accessible verification alternative)">` | Single activation disables both verify buttons to prevent double-triggering, announces *"Verifying via keyboard accessibility path…"* $\to$ *"Verification complete."*, closes the dialog, and restores focus to the triggering portal button (`previousActive.focus()`). |

---

## 3. Reproducing the Screen-Reader & Keyboard Checks Locally

```powershell
# Run automated axe-core, WCAG contrast, screen-reader live-region, and keyboard-only E2E tests:
npm --prefix portal test

# Start the live portal for manual NVDA / Windows Narrator inspection at http://127.0.0.1:5173:
python scripts/tasks.py demo
```

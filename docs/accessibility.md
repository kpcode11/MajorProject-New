# Accessibility Audit, Screen-Reader Notes, and Known Limitations (`docs/accessibility.md`)

**Project:** Passive Bot Detection to Replace CAPTCHA (SIH1672)
**Tasks covered:** `P9-09` (`axe-core` & WCAG 2.1 AA audit), `P9-10` (Keyboard-only E2E login/OTP flow), `P9-11` (Screen-reader smoke test notes), `P9-12` (Missing-modality E2E verification), `P9-13` (Known accessibility limitations).

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

## 3. Missing-Modality Policy & Keyboard-Only Fairness (`P9-10`, `P9-12`)

Traditional behavioural bot detectors often penalise sessions that lack mouse movement trajectories, inadvertently blocking blind screen-reader users, keyboard-only power users, and switch-access users. BotGuard enforces three end-to-end guarantees (`backend/app/scoring.py`, `backend/tests/test_missing_modality_e2e.py`, `portal/test/keyboard_e2e.test.tsx`):

1. **Absent Mouse Is Never Treated as Bot (`mouse_score = None`):**
   - If a session contains fewer than `MIN_MOUSE_MOVE_POINTS` (`8`) mouse movement samples and no pre-extracted mouse features, `has_mouse` is `False` and `fuse_modality_scores` scores solely the active modality (`keyboard_score`).
   - Zero-dwell `<button>` activation clicks (`[0, 0, t, t]`) produced when pressing `Enter` or `Space` on a focused button do not trigger mouse-trajectory penalties.
2. **Sub-Window & Assistive Keyboard Navigation Cap (`MISSING_MOUSE_VALID_KB_MAX_SCORE = 0.50`):**
   - Because the keyboard classifier (`logistic_regression-v1`) was trained on Aalto typing windows of $\ge 10$ key events (`MIN_TYPING_WINDOW_KEYS = 10`), short keyboard-only navigation (such as `Tab` + `Enter` or a 6-digit PIN `560001` + `Enter`) or slow assistive-technology typing ($\sim 300\text{–}400\text{ ms}$ dwell, $\sim 800\text{–}1000\text{ ms}$ flight with natural variance `identical_interval_fraction < 0.80` and `dwell_std > 2.0`) is capped at `0.50` (`medium` band) when `has_mouse` is `False` and `untrusted_count == 0`.
   - As a result, a session with no mouse events and valid keyboard navigation is **never auto-denied** (`decision` is `"allow"` or `"challenge"` across all action sensitivity classes: `high`, `medium`, and `low`).
3. **Synthetic Keyboard Bots Are Still Caught:**
   - Constant-interval synthetic keyboard bots (`K1`, `identical_interval_fraction >= 0.80` or `dwell_std <= 2.0`), untrusted DOM key events (`R11_UNTRUSTED_EVENTS`), and headless automation (`R02_WEBDRIVER`) bypass the fairness cap and remain blocked (`decision: "deny"`, `band: "high"`).

---

## 4. Known Accessibility Limitations (`P9-13`)

In accordance with the project's scientific honesty requirements, the following limitations are documented:

1. **No Assistive-Technology Training Cohort in Public Datasets:**
   - The public datasets used to train the mouse and keyboard models (Bournemouth `web_bot_detection`, IEEE DataPort blog bots, CaptchaSolve30k, and Aalto 136M Keystrokes) were collected from general research/volunteer cohorts without documented motor impairments, screen-reader navigation, eye-gaze pointers, head-tracking pointers, or switch-scanning devices.
   - Users of specialized pointer devices (e.g., head trackers or mouth sticks with atypical curvature/velocity profiles) may receive higher mouse model scores than standard desktop mouse users and therefore experience the step-up challenge (`decision: "challenge"`) more frequently.
2. **Voice Dictation, Speech-to-Text, and Virtual On-Screen Keyboards:**
   - Browser speech-recognition tools, password managers, or OS on-screen accessibility keyboards that insert text via DOM `input` / `insertReplacementText` events without emitting physical `keydown`/`keyup` pairs may trigger `autofill_suspected = true` in `KeyboardCollector` (`sdk/src/collectors/keyboard.ts`) or yield `< 2` key events (`has_keys = False`).
   - While such sessions are not auto-denied when environment signals are clean, they cannot benefit from passive keyboard-rhythm verification and will fall back to the step-up challenge on high-sensitivity actions (`otp_request`, `details_update`).
3. **Step-Up Challenge Hold Duration vs. Single-Press Alternative Trade-Off:**
   - The primary step-up UI (`[data-testid="stepup-hold-btn"]`) requires sustaining a physical mouse, touch, or key hold for `800–1500 ms`. Users with motor tremor or OS Sticky Keys / Repeat Keys settings who cannot sustain a hold must use the explicit **`Use Keyboard Single-Press Verify`** (`[data-testid="stepup-kb-btn"]`) button.
   - The single-press alternative removes physical hold strain, but still waits `800–1500 ms` before resolving and provides less behavioural entropy against an advanced DOM-driving script than physical press-and-release jitter.
4. **Mobile Touch & Mobile Screen-Reader Gestures Out of Scope (Phase 8 Skipped):**
   - Per human decision (`docs/decision_log.md`, `P8-*` marked `SKIPPED`), no mobile touch dataset or touch ML model is included in this desktop release. Mobile screen-reader exploration gestures (Android TalkBack / iOS VoiceOver swipe-to-focus and double-tap) have not been evaluated.
5. **English-Only UI Copy in Prototype Portal and Default Modal:**
   - Although the mock **Update details** page includes a notification language field (`English`, `Hindi`, `Kannada`, `Tamil`), the demo portal interface and default step-up modal copy are rendered in English (`<html lang="en">`). A production citizen portal deployment requires localized UI strings, localized `aria-label` / `aria-live` announcements, and per-locale `lang` attributes.
6. **Automated DOM Auditing vs. Live Human Assistive-Technology Studies:**
   - CI accessibility tests (`portal/test/accessibility.test.tsx`, `portal/test/keyboard_e2e.test.tsx`) execute inside `happy-dom` using `axe-core` (`4.13.0`) and a deterministic WCAG 2.1 AA contrast calculator. While this catches structural ARIA, label, focus-trap, and colour-contrast regressions automatically, it does not replace formal usability testing with human participants using JAWS, NVDA, VoiceOver, and switch hardware.

---

## 5. Reproducing the Accessibility & Missing-Modality Checks

```powershell
# 1. Run portal axe-core, WCAG contrast, screen-reader live-region, and keyboard-only E2E tests:
npm --prefix portal test

# 2. Run backend missing-modality and keyboard-only E2E tests:
backend\.venv\Scripts\python.exe -m pytest -q backend/tests/test_missing_modality_e2e.py backend/tests/test_e2e_portal.py

# 3. Start the live portal for manual NVDA / Windows Narrator inspection at http://127.0.0.1:5173:
python scripts/tasks.py demo
```

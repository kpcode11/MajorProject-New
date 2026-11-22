"""Launch a visible Playwright Chromium browser to demonstrate live bot detection across ALL 3 portal forms.

Forms exercised visually:
  1. Resident Login     (/?page=login          -> /portal-api/otp/request)
  2. Update Details     (/?page=update-details -> /portal-api/details/update)
  3. Centre Search      (/?page=centre-search  -> /portal-api/centres/search)

Usage:
    # Make sure the demo servers (:8000, :5173, :5174) are running in Terminal 1:
    #   python scripts/tasks.py demo
    # Then in Terminal 2:
    python scripts/tasks.py demo-bot
    # Or directly with custom flags:
    backend\\.venv\\Scripts\\python.exe scripts/demo_playwright_bot.py --tier all --slow-mo 300
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.safety import validate_target_url
from simulator.tier3_stealth import TIER3_INIT_SCRIPT


def _move_mouse_straight_line(
    page: Any,
    start_xy: tuple[int, int],
    end_xy: tuple[int, int],
    steps: int = 18,
) -> None:
    """Move cursor in a perfectly straight line (straightness = 1.0, curvature = 0.0)."""
    sx, sy = start_xy
    ex, ey = end_xy
    for idx in range(steps + 1):
        frac = idx / float(max(1, steps))
        x = sx + (ex - sx) * frac
        y = sy + (ey - sy) * frac
        page.mouse.move(x, y)


def _read_verdict(page: Any) -> str:
    last_dec = page.locator('[data-testid="last-decision"]')
    if last_dec.count() > 0:
        return str(last_dec.inner_text())
    return "challenged / denied"


def _dismiss_challenge_if_open(page: Any) -> None:
    """If the step-up challenge modal opened, pause so the viewer sees it, then cancel/close."""
    cancel_btn = page.locator(".botguard-challenge-cancel-btn")
    if cancel_btn.count() > 0 and cancel_btn.is_visible():
        time.sleep(1.2)
        cancel_btn.click()
        time.sleep(0.3)


def _run_tier2_all_forms(browser: Any, clean_url: str) -> None:
    print(
        "\n[Tier 2 — Default Playwright Bot] (navigator.webdriver=true, zero mouse arc, programmatic fill)"
    )
    ctx = browser.new_context(viewport={"width": 1280, "height": 820})
    page = ctx.new_page()

    # 1. Resident Login
    print("  1/3 -> Resident Login (/?page=login): programmatic fill + click...")
    page.goto(f"{clean_url}/?page=login", wait_until="networkidle")
    time.sleep(0.6)
    page.fill('[data-testid="identifier-input"]', "999900001234")
    time.sleep(0.3)
    page.click('[data-testid="send-otp-btn"]')
    time.sleep(1.2)
    _dismiss_challenge_if_open(page)
    print(f"         Verdict: {_read_verdict(page)}")
    time.sleep(0.8)

    # 2. Update Details
    print(
        "  2/3 -> Update Details (/?page=update-details): multi-field programmatic fill + click..."
    )
    page.goto(f"{clean_url}/?page=update-details", wait_until="networkidle")
    time.sleep(0.6)
    page.fill('[data-testid="detail-name-input"]', "Automated Scraper Bot")
    page.fill('[data-testid="detail-address-input"]', "101 Headless Automation Lane")
    page.fill('[data-testid="detail-pincode-input"]', "560001")
    page.check('[data-testid="detail-confirm-checkbox"]')
    time.sleep(0.3)
    page.click('[data-testid="submit-details-btn"]')
    time.sleep(1.2)
    _dismiss_challenge_if_open(page)
    print(f"         Verdict: {_read_verdict(page)}")
    time.sleep(0.8)

    # 3. Centre Search
    print("  3/3 -> Centre Search (/?page=centre-search): programmatic fill + click...")
    page.goto(f"{clean_url}/?page=centre-search", wait_until="networkidle")
    time.sleep(0.6)
    page.fill('[data-testid="centre-query-input"]', "Bengaluru")
    time.sleep(0.3)
    page.click('[data-testid="search-centres-btn"]')
    time.sleep(1.2)
    _dismiss_challenge_if_open(page)
    print(f"         Verdict: {_read_verdict(page)}")
    time.sleep(1.0)
    ctx.close()


def _run_tier3_all_forms(browser: Any, clean_url: str) -> None:
    print(
        "\n[Tier 3 — Stealth Playwright Bot] (webdriver hidden, robotic straight-line mouse & constant-delay typing)"
    )
    ctx = browser.new_context(viewport={"width": 1280, "height": 820})
    ctx.add_init_script(TIER3_INIT_SCRIPT)
    page = ctx.new_page()

    # 1. Resident Login
    print(
        "  1/3 -> Resident Login (/?page=login): straight-line mouse + fixed 40ms typing..."
    )
    page.goto(f"{clean_url}/?page=login", wait_until="networkidle")
    time.sleep(0.6)
    _move_mouse_straight_line(page, (80, 120), (260, 240), steps=18)
    id_box = page.locator('[data-testid="identifier-input"]')
    id_box.click()
    id_box.type("999900005678", delay=40)
    _move_mouse_straight_line(page, (260, 240), (140, 320), steps=12)
    page.click('[data-testid="send-otp-btn"]')
    time.sleep(1.2)
    _dismiss_challenge_if_open(page)
    print(f"         Verdict: {_read_verdict(page)}")
    time.sleep(0.8)

    # 2. Update Details
    print(
        "  2/3 -> Update Details (/?page=update-details): straight-line mouse + fixed 35ms typing..."
    )
    page.goto(f"{clean_url}/?page=update-details", wait_until="networkidle")
    time.sleep(0.6)
    _move_mouse_straight_line(page, (90, 110), (280, 210), steps=16)
    name_box = page.locator('[data-testid="detail-name-input"]')
    name_box.click()
    name_box.type("Stealth Bot User", delay=35)

    _move_mouse_straight_line(page, (280, 210), (280, 290), steps=12)
    addr_box = page.locator('[data-testid="detail-address-input"]')
    addr_box.click()
    addr_box.type("404 Linear Trajectory Road", delay=35)

    _move_mouse_straight_line(page, (280, 290), (180, 370), steps=12)
    pin_box = page.locator('[data-testid="detail-pincode-input"]')
    pin_box.click()
    pin_box.type("560001", delay=35)

    page.check('[data-testid="detail-confirm-checkbox"]')
    _move_mouse_straight_line(page, (180, 370), (160, 520), steps=12)
    page.click('[data-testid="submit-details-btn"]')
    time.sleep(1.2)
    _dismiss_challenge_if_open(page)
    print(f"         Verdict: {_read_verdict(page)}")
    time.sleep(0.8)

    # 3. Centre Search
    print(
        "  3/3 -> Centre Search (/?page=centre-search): straight-line mouse + fixed 40ms typing..."
    )
    page.goto(f"{clean_url}/?page=centre-search", wait_until="networkidle")
    time.sleep(0.6)
    _move_mouse_straight_line(page, (100, 120), (240, 230), steps=16)
    q_box = page.locator('[data-testid="centre-query-input"]')
    q_box.click()
    q_box.type("560001", delay=40)
    _move_mouse_straight_line(page, (240, 230), (520, 230), steps=14)
    page.click('[data-testid="search-centres-btn"]')
    time.sleep(1.2)
    _dismiss_challenge_if_open(page)
    print(f"         Verdict: {_read_verdict(page)}")
    time.sleep(1.0)
    ctx.close()


def run_visible_playwright_demo(
    portal_url: str = "http://127.0.0.1:5173",
    admin_url: str = "http://127.0.0.1:5174",
    *,
    tier: str = "all",
    slow_mo_ms: int = 250,
    keep_open_seconds: int = 15,
) -> int:
    """Open a visible Playwright Chromium window, attack all 3 portal forms, and open the standalone Admin Console (:5174)."""
    clean_url = validate_target_url(portal_url).rstrip("/")
    clean_admin_url = validate_target_url(admin_url).rstrip("/")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is not installed in this Python environment.\n"
            "Install it with:\n"
            "  backend\\.venv\\Scripts\\python.exe -m pip install playwright\n"
            "  backend\\.venv\\Scripts\\python.exe -m playwright install chromium",
            file=sys.stderr,
        )
        return 1

    print("=" * 76)
    print("  Passive BotGuard — Live Visible Playwright Bot Demo (All 3 Portal Forms)")
    print("=" * 76)
    print(f"  Mock Citizen Portal (:5173) : {clean_url}")
    print(f"  Standalone Admin    (:5174) : {clean_admin_url}")
    print(
        "  Forms Tested                : Resident Login, Update Details, Centre Search"
    )
    print(f"  Bot Tier Mode               : {tier}")
    print("=" * 76)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=slow_mo_ms)

        if tier in ("tier2", "all"):
            _run_tier2_all_forms(browser, clean_url)

        if tier in ("tier3", "all"):
            _run_tier3_all_forms(browser, clean_url)

        print(
            f"\n[Admin Console] Opening Standalone Admin Console ({clean_admin_url})..."
        )
        admin_ctx = browser.new_context(viewport={"width": 1420, "height": 900})
        admin_page = admin_ctx.new_page()
        try:
            admin_page.goto(clean_admin_url, wait_until="networkidle", timeout=5000)
        except Exception:  # noqa: BLE001
            admin_page.goto(f"{clean_url}/?page=admin", wait_until="networkidle")
        time.sleep(0.8)
        kin_tab = admin_page.locator('[data-testid="admin-tab-kinematics"]')
        if kin_tab.count() > 0:
            kin_tab.click()
        print(
            f"  -> Showing captured bot sessions & Mouse/Keyboard Kinematics for {keep_open_seconds}s..."
        )
        time.sleep(max(1, keep_open_seconds))
        admin_ctx.close()
        browser.close()

    print("\nLive Playwright bot demonstration across all 3 forms finished.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--portal-url",
        default="http://127.0.0.1:5173",
        help="Local mock citizen portal URL (default: http://127.0.0.1:5173).",
    )
    parser.add_argument(
        "--admin-url",
        default="http://127.0.0.1:5174",
        help="Standalone Admin Dashboard URL (default: http://127.0.0.1:5174).",
    )
    parser.add_argument(
        "--tier",
        choices=("tier2", "tier3", "all"),
        default="all",
        help="Which visible Playwright bot tier to demonstrate across all 3 forms (default: all).",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=250,
        help="Playwright slow_mo delay in milliseconds so movements are visible (default: 250).",
    )
    parser.add_argument(
        "--keep-open",
        type=int,
        default=15,
        help="Seconds to keep the Admin Kinematics Console open at the end (default: 15).",
    )
    args = parser.parse_args()
    return run_visible_playwright_demo(
        args.portal_url,
        args.admin_url,
        tier=args.tier,
        slow_mo_ms=args.slow_mo,
        keep_open_seconds=args.keep_open,
    )


if __name__ == "__main__":
    raise SystemExit(main())

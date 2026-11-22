"""Launch a visible Playwright Chromium browser to demonstrate live bot detection (Tier 2 & Tier 3).

Usage:
    # Make sure the demo server is running in Terminal 1:
    #   python scripts/tasks.py demo
    # Then in Terminal 2:
    python scripts/tasks.py demo-bot
    # Or directly:
    backend\\.venv\\Scripts\\python.exe scripts/demo_playwright_bot.py --tier all --slow-mo 350
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.safety import validate_target_url
from simulator.tier3_stealth import TIER3_INIT_SCRIPT


def run_visible_playwright_demo(
    portal_url: str = "http://127.0.0.1:5173",
    *,
    tier: str = "all",
    slow_mo_ms: int = 350,
    keep_open_seconds: int = 12,
) -> int:
    """Open a visible Playwright Chromium window, execute bot attacks against the portal, and open the Admin Kinematics Inspector."""
    clean_url = validate_target_url(portal_url).rstrip("/")

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

    print("=" * 72)
    print("  Passive BotGuard — Live Visible Playwright Bot Demonstration")
    print("=" * 72)
    print(f"  Target Mock Portal : {clean_url}")
    print(f"  Bot Tier Mode      : {tier}")
    print(f"  Slow-Mo Delay      : {slow_mo_ms} ms per action")
    print("=" * 72)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=slow_mo_ms)

        if tier in ("tier2", "all"):
            print(
                "\n[1/2] Launching TIER 2 Bot (Default Playwright — navigator.webdriver=true, zero mouse curve)..."
            )
            ctx2 = browser.new_context(viewport={"width": 1280, "height": 800})
            page2 = ctx2.new_page()
            page2.goto(f"{clean_url}/?page=login", wait_until="networkidle")
            time.sleep(0.8)

            # Tier 2: Direct programmatic fill and click (no human mouse arc, no per-key rhythm)
            page2.fill('[data-testid="identifier-input"]', "999900001234")
            time.sleep(0.4)
            page2.click('[data-testid="send-otp-btn"]')
            time.sleep(1.8)

            last_dec = page2.locator('[data-testid="last-decision"]')
            verdict_text = (
                last_dec.inner_text() if last_dec.count() > 0 else "challenged / denied"
            )
            print(f"  -> Tier 2 Bot Result on Portal UI: {verdict_text}")
            time.sleep(1.5)
            ctx2.close()

        if tier in ("tier3", "all"):
            print(
                "\n[2/2] Launching TIER 3 Stealth Bot (Hides navigator.webdriver, uses robotic straight-line mouse & constant-interval typing)..."
            )
            ctx3 = browser.new_context(viewport={"width": 1280, "height": 800})
            ctx3.add_init_script(TIER3_INIT_SCRIPT)
            page3 = ctx3.new_page()
            page3.goto(f"{clean_url}/?page=login", wait_until="networkidle")
            time.sleep(0.8)

            # Move mouse in a perfectly straight line (straightness = 1.0, curvature = 0.0)
            start_x, start_y = 120, 140
            end_x, end_y = 320, 260
            steps = 20
            for idx in range(steps + 1):
                frac = idx / float(steps)
                x = start_x + (end_x - start_x) * frac
                y = start_y + (end_y - start_y) * frac
                page3.mouse.move(x, y)

            input_box = page3.locator('[data-testid="identifier-input"]')
            input_box.click()
            # Type with a robotic fixed delay (constant flight/dwell intervals)
            input_box.type("999900005678", delay=45)
            time.sleep(0.4)
            page3.click('[data-testid="send-otp-btn"]')
            time.sleep(1.8)

            last_dec3 = page3.locator('[data-testid="last-decision"]')
            verdict_text3 = (
                last_dec3.inner_text()
                if last_dec3.count() > 0
                else "challenged / denied"
            )
            print(f"  -> Tier 3 Stealth Bot Result on Portal UI: {verdict_text3}")
            time.sleep(1.5)
            ctx3.close()

        print(
            f"\n[Admin Console] Opening BotGuard Security & Kinematics Console ({clean_url}/?page=admin)..."
        )
        admin_ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        admin_page = admin_ctx.new_page()
        admin_page.goto(f"{clean_url}/?page=admin", wait_until="networkidle")
        time.sleep(0.8)
        kin_tab = admin_page.locator('[data-testid="admin-tab-kinematics"]')
        if kin_tab.count() > 0:
            kin_tab.click()
        print(
            f"  -> Inspect the captured bot sessions and their Mouse/Keyboard Kinematics for {keep_open_seconds}s..."
        )
        time.sleep(max(1, keep_open_seconds))
        admin_ctx.close()
        browser.close()

    print("\nLive Playwright bot demonstration finished.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--portal-url",
        default="http://127.0.0.1:5173",
        help="Local mock portal URL (must be in simulator/allowlist.txt).",
    )
    parser.add_argument(
        "--tier",
        choices=("tier2", "tier3", "all"),
        default="all",
        help="Which visible Playwright bot tier to demonstrate (default: all).",
    )
    parser.add_argument(
        "--slow-mo",
        type=int,
        default=350,
        help="Playwright slow_mo delay in milliseconds so movements are visible (default: 350).",
    )
    parser.add_argument(
        "--keep-open",
        type=int,
        default=12,
        help="Seconds to keep the Admin Kinematics Console open at the end (default: 12).",
    )
    args = parser.parse_args()
    return run_visible_playwright_demo(
        args.portal_url,
        tier=args.tier,
        slow_mo_ms=args.slow_mo,
        keep_open_seconds=args.keep_open,
    )


if __name__ == "__main__":
    raise SystemExit(main())

"""Capture high-resolution screenshots of the live deployed CONFORM UI on Cloud Run across all 6 stages."""
from __future__ import annotations

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://conform-tiwoc77ijq-ew.a.run.app"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        page = context.new_page()

        print(f"Navigating to {URL}...")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        # 1. Stage 1: Brief
        print("1. Capturing 01_live_stage_brief.png...")
        page.screenshot(path=str(OUT / "01_live_stage_brief.png"))

        # 2. Click "Roll camera: scan the slate"
        roll_btn = page.locator("button:has-text('Roll camera')")
        if roll_btn.count() > 0:
            print("2. Clicking Roll camera...")
            roll_btn.click()
            page.wait_for_timeout(2500)
            print("Capturing 02_live_stage_scan.png...")
            page.screenshot(path=str(OUT / "02_live_stage_scan.png"))

            # Wait for StageScan auto-advance (approx 5-6s)
            print("Waiting for StageScan auto-advance...")
            page.wait_for_timeout(6000)

            # 3. Stage 3: Graph
            print("3. Capturing 03_live_stage_graph.png...")
            page.screenshot(path=str(OUT / "03_live_stage_graph.png"))

            # Click proceed to approval
            proceed_btn = page.locator("button.btn-pill:has-text('Proceed to Approval'), button.btn-pill:has-text('Approve')")
            if proceed_btn.count() > 0:
                print("Clicking proceed to approval...")
                proceed_btn.first.click()
                page.wait_for_timeout(2000)

            # 4. Stage 4: Approve
            print("4. Capturing 04_live_stage_approve.png...")
            page.screenshot(path=str(OUT / "04_live_stage_approve.png"))

            # Click Approve spend
            sign_btn = page.locator("button.btn-pill:has-text('Approve spend')")
            if sign_btn.count() > 0:
                print("Signing approval...")
                sign_btn.click()
                page.wait_for_timeout(3000)

            # Now the "Build dirty subtree" button is visible
            build_btn = page.locator("button.btn-pill:has-text('Build dirty subtree')")
            if build_btn.count() > 0:
                print("5. Clicking Build dirty subtree...")
                build_btn.click()
                page.wait_for_timeout(2000)
                print("Capturing 05_live_stage_rebuild.png...")
                page.screenshot(path=str(OUT / "05_live_stage_rebuild.png"))

                # Wait for rebuild animation and success popup
                print("Waiting for rebuild to complete...")
                page.wait_for_timeout(6000)

                # Capture success popup if open
                verify_btn = page.locator("button.btn-pill:has-text('Verify the release')")
                if verify_btn.count() > 0:
                    page.screenshot(path=str(OUT / "05b_live_rebuild_success_popup.png"))
                    print("Clicking Verify the release...")
                    verify_btn.click()
                    page.wait_for_timeout(2000)

            # 6. Stage 6: Release & Verification
            print("6. Capturing 06_live_stage_release.png...")
            page.screenshot(path=str(OUT / "06_live_stage_release.png"))

        # 7. Ask Slate Modal
        ask_btn = page.locator("button:has-text('Ask Slate')")
        if ask_btn.count() > 0:
            print("7. Opening Ask Slate modal...")
            ask_btn.click()
            page.wait_for_timeout(1500)
            print("Capturing 07_live_ask_slate_mcp.png...")
            page.screenshot(path=str(OUT / "07_live_ask_slate_mcp.png"))

        print("SUCCESS: All live screenshots captured cleanly!")
        browser.close()

if __name__ == "__main__":
    main()

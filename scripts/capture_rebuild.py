from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
    page.goto("https://conform-tiwoc77ijq-ew.a.run.app", wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.locator("button:has-text('Roll camera')").click()
    page.wait_for_timeout(7000)
    page.locator("button.btn-pill:has-text('Proceed to Approval'), button.btn-pill:has-text('Approve')").first.click()
    page.wait_for_timeout(2000)
    page.locator("button.btn-pill:has-text('Approve spend')").click()
    page.wait_for_selector("button:has-text('Build dirty subtree')", timeout=15000).click()
    page.wait_for_timeout(2500)
    page.screenshot(path="docs/screenshots/05_live_stage_rebuild.png")
    print("SUCCESS: 05_live_stage_rebuild.png captured!")
    browser.close()

/**
 * CONFORM — Automated Demo Video Recorder
 *
 * Launches a high-DPI browser at 1920x1080, records a video of the full
 * 8-beat blockbuster hackathon demo narrative on http://localhost:8080,
 * and saves the recording to docs/demo_recording.webm.
 */

const fs = require("fs");
const path = require("path");
const playwrightPath = path.resolve(__dirname, "..", "web", "node_modules", "playwright");
const { chromium } = require(playwrightPath);

async function record() {
  const outputDir = path.resolve(__dirname, "..", "docs", "video_raw");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log("Launching browser for video recording...");
  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: outputDir,
      size: { width: 1920, height: 1080 },
    },
  });

  const page = await context.newPage();
  page.setDefaultTimeout(60000);

  console.log("Navigating to CONFORM on http://localhost:8080...");
  await page.goto("http://localhost:8080", { waitUntil: "networkidle" });
  await page.waitForTimeout(3000);

  // -------------------------------------------------------------------------
  // Beat 1: The Problem & The Slate (0:00 - 0:25)
  // -------------------------------------------------------------------------
  console.log("Beat 1: The Problem & The Slate...");
  // Show header and status bar
  await page.waitForTimeout(2000);

  // Switch to Dependency Graph tab
  await page.click("nav button:has-text('Dependency Graph')");
  await page.waitForTimeout(3000);

  // Filter to Campaign A
  await page.selectOption("select", "campaign_a");
  await page.waitForTimeout(2500);

  // Click on a master node to inspect
  const circle = await page.$("circle");
  if (circle) {
    await circle.click();
    await page.waitForTimeout(3000);
  }

  // Switch back to All Campaigns
  await page.selectOption("select", "all");
  await page.waitForTimeout(2000);

  // -------------------------------------------------------------------------
  // Beat 2: The Change & The Blast Radius (0:25 - 0:55)
  // -------------------------------------------------------------------------
  console.log("Beat 2: The Change & The Blast Radius...");
  await page.click("nav button:has-text('Change & Approval')");
  await page.waitForTimeout(2000);

  // Click the EU Regulation Change Preset Card
  const euCard = await page.$(".scenario-card:has-text('EU Regulation Change')");
  if (euCard) {
    await euCard.click();
    await page.waitForTimeout(2000);
  }

  // Click Compute Blast Radius
  console.log("Computing blast radius...");
  await page.click("button:has-text('Compute Blast Radius')");
  await page.waitForTimeout(4000);

  // Scroll down to showcase the blast radius and savings callout
  await page.evaluate(() => window.scrollBy({ top: 400, behavior: "smooth" }));
  await page.waitForTimeout(3500);

  // Click View on Graph
  const viewGraphBtn = await page.$("button:has-text('View on Graph')");
  if (viewGraphBtn) {
    await viewGraphBtn.click();
    await page.waitForTimeout(4000);
  }

  // -------------------------------------------------------------------------
  // Beat 3: The Human Approval Gate (0:55 - 1:15)
  // -------------------------------------------------------------------------
  console.log("Beat 3: The Human Approval Gate...");
  await page.click("nav button:has-text('Change & Approval')");
  await page.waitForTimeout(2000);

  // Scroll to approval gate
  await page.evaluate(() => window.scrollBy({ top: 800, behavior: "smooth" }));
  await page.waitForTimeout(2500);

  // Click Approve Spend
  console.log("Approving spend...");
  await page.click("button:has-text('Approve Spend')");
  await page.waitForTimeout(3000);

  // -------------------------------------------------------------------------
  // Beat 4: Incremental Rebuild & Cache Proof (1:15 - 1:40)
  // -------------------------------------------------------------------------
  console.log("Beat 4: Incremental Rebuild...");
  // Click Build Dirty Subtree
  await page.click("button:has-text('Build Dirty Subtree')");
  console.log("Building dirty subtree...");
  await page.waitForTimeout(8000); // Wait for build to complete and navigate to timeline

  // Timeline view should now be visible
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  await page.waitForTimeout(3000);

  // Filter to Rebuilt Only
  const rebuiltChip = await page.$(".chip:has-text('Rebuilt Only')");
  if (rebuiltChip) {
    await rebuiltChip.click();
    await page.waitForTimeout(3000);
  }

  // Filter to Cache Hits Reused
  const reusedChip = await page.$(".chip:has-text('Cache Hits Reused')");
  if (reusedChip) {
    await reusedChip.click();
    await page.waitForTimeout(3500);
  }

  // Filter back to All Runs
  const allChip = await page.$(".chip:has-text('All Runs')");
  if (allChip) {
    await allChip.click();
    await page.waitForTimeout(2000);
  }

  // -------------------------------------------------------------------------
  // Beat 5: Dynamic Fault Injection & Retry Taxonomy (1:40 - 2:05)
  // -------------------------------------------------------------------------
  console.log("Beat 5: Dynamic Fault Injection...");
  const faultToggle = await page.$("button:has-text('Fault injection for next build')");
  if (faultToggle) {
    await faultToggle.click();
    await page.waitForTimeout(2500);
    // Toggle back
    await faultToggle.click();
    await page.waitForTimeout(2000);
  }

  // -------------------------------------------------------------------------
  // Beat 6: ClickHouse Analytics & Natural Language Analyst (2:05 - 2:35)
  // -------------------------------------------------------------------------
  console.log("Beat 6: ClickHouse Analytics & Natural Language Analyst...");
  // Go to Slate Analytics
  await page.click("nav button:has-text('Slate Analytics')");
  await page.waitForTimeout(4000);

  // Scroll through analytics
  await page.evaluate(() => window.scrollBy({ top: 350, behavior: "smooth" }));
  await page.waitForTimeout(3500);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  await page.waitForTimeout(1500);

  // Go to Ask the Slate
  await page.click("nav button:has-text('Ask the Slate')");
  await page.waitForTimeout(2500);

  // Click suggestion: Spend across models
  console.log("Asking analyst agent: spend across models...");
  const spendChip = await page.$(".chip:has-text('What is our spend across models?')");
  if (spendChip) {
    await spendChip.click();
    await page.waitForTimeout(4000);
  }

  // Click suggestion: How many nodes were reused vs rebuilt?
  console.log("Asking analyst agent: reuse count...");
  const reuseSuggestion = await page.$(".chip:has-text('How many nodes were reused vs rebuilt?')");
  if (reuseSuggestion) {
    await reuseSuggestion.click();
    await page.waitForTimeout(4000);
  }

  // -------------------------------------------------------------------------
  // Beat 7: Release Verification & Tamper Proof (2:35 - 2:55)
  // -------------------------------------------------------------------------
  console.log("Beat 7: Release Verification & Tamper Proof...");
  // Go back to Build & Verify
  await page.click("nav button:has-text('Build & Verify')");
  await page.waitForTimeout(2500);

  // Scroll to Verification studio
  await page.evaluate(() => window.scrollBy({ top: 500, behavior: "smooth" }));
  await page.waitForTimeout(2000);

  // Click Verify Release (Byte-Exact)
  console.log("Verifying intact release...");
  await page.click("button:has-text('Verify Release')");
  await page.waitForTimeout(4000);

  // Click Corrupt 1 Byte (Tamper Demo)
  console.log("Injecting tamper corruption...");
  await page.click("button:has-text('Corrupt 1 Byte in Storage')");
  await page.waitForTimeout(3000);

  // Click Verify Release again -> should fail with MISMATCH
  console.log("Verifying tampered release (should fail red)...");
  await page.click("button:has-text('Verify Release')");
  await page.waitForTimeout(5000);

  // -------------------------------------------------------------------------
  // Beat 8: Outro (2:55 - 3:00)
  // -------------------------------------------------------------------------
  console.log("Beat 8: Outro...");
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  await page.click("nav button:has-text('Change & Approval')");
  await page.waitForTimeout(3000);

  console.log("Closing page and finalizing video recording...");
  await page.close();
  await context.close();
  await browser.close();

  // Find the recorded video in outputDir
  const files = fs.readdirSync(outputDir).filter((f) => f.endsWith(".webm"));
  if (files.length > 0) {
    const recordedPath = path.join(outputDir, files[0]);
    const finalWebm = path.resolve(__dirname, "..", "docs", "demo_recording.webm");
    fs.copyFileSync(recordedPath, finalWebm);
    console.log(`Video recorded successfully: ${finalWebm}`);
  }
}

record().catch((err) => {
  console.error("Recording failed:", err);
  process.exit(1);
});

# CONFORM — Hackathon Demo Video Script & Storyboard

**Contest**: Agentic Cinema: The Blockbuster Hackathon (Devpost)  
**Track**: ClickHouse Partner Track  
**Target Duration**: 2:45 – 3:00  
**Video File**: `docs/demo_recording.mp4`  

---

## Storyboard & Narration Breakdown

### Beat 1: The Problem & The Slate (0:00 – 0:25)
- **On-Screen**:
  - Open `http://localhost:8080`.
  - Header shows truthful integration status: Vertex AI, ClickHouse writer, MCP read reader, and Artifact store.
  - Switch to **Dependency Graph** tab (`🕸️ Dependency Graph`).
  - View the 252 nodes across 3 advertising campaigns (`campaign_a`, `campaign_b`, `campaign_c`).
  - Show the creative spine: `source` $\to$ `shot_plan` $\to$ `keyframe` $\to$ `clip` fanning out to 40 localized territory variants.
  - Click on a node to reveal the **Provenance Inspector** rail displaying its exact SHA-256 content-addressed fingerprint.
- **Voiceover Script**:
  > *"When an advertising studio produces a global campaign slate across 40 territories, each variant fans out from master video clips down to localized disclaimers and packages. Today, when a single regional regulation or prompt changes—say, Germany and France require a longer allergy disclaimer—existing AI pipelines have no idea what depends on what. So they regenerate everything. That burns enormous compute and money because video generation is so costly. CONFORM changes this: it's a compiler for generative media pipelines."*

---

### Beat 2: The Change & The Blast Radius (0:25 – 0:55)
- **On-Screen**:
  - Switch to **Change & Approval** tab (`⚡ Change & Approval`).
  - Click the pre-configured scenario: **🇪🇺 EU Regulation Change (Main Demo)**.
  - Text: `new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40`.
  - Click **"⚡ Compute Blast Radius"**.
  - Review the blast radius metrics: **12 / 252 dirty nodes, 240 reused byte-for-byte**.
  - Showcase the **Compilation Savings Callout**: Estimated spend is **$0.0030** instead of the naive **$0.0630** (95% cost saved!).
  - Click **"View on Graph ➔"**: The 12 dirty nodes pulse amber across Germany and France, while clean nodes recede into the background.
- **Voiceover Script**:
  > *"Here, a new EU regulation lands requiring longer disclaimers in Germany and France. Before spending a single dollar or calling any generative API, CONFORM canonicalizes the change using RFC 8785 JSON canonicalization and computes the exact blast radius. Out of 252 assets across the slate, exactly 12 are dirty, and 240 are guaranteed clean. Naive regeneration would cost over 20 times more. On the graph, the dirty subtree pulses amber while everything else is marked for byte-exact reuse."*

---

### Beat 3: The Human Approval Gate (0:55 – 1:15)
- **On-Screen**:
  - Switch back to **Change & Approval** tab.
  - Scroll down to the **Human Approval Gate**.
  - Show simulated role: `producer (simulated)` and budget compliance check.
  - Click **"✓ Approve Spend ($0.0030)"**.
  - The build button unlocks and transitions to **"🚀 Build Dirty Subtree (Approved)"**.
- **Voiceover Script**:
  > *"CONFORM enforces a strict architectural boundary: language models interpret text, but pure deterministic code computes costs and graphs. Crucially, no generative provider call can ever happen before explicit human approval. Our producer approves the estimated three-cent spend, unlocking the build engine."*

---

### Beat 4: Incremental Rebuild & Cache Proof (1:15 – 1:40)
- **On-Screen**:
  - Click **"🚀 Build Dirty Subtree (Approved)"**.
  - Automatically transitions to the **Build & Verify** timeline.
  - Show build summary: 12 nodes rebuilt, 240 nodes reused from cache with **$0.00** cost badges.
  - Filter by **"Rebuilt Only"** to show the 12 rebuilt copy and package nodes.
  - Filter by **"Cache Hits Reused"** to prove the 240 untouched artifacts were pulled directly from content-addressed storage.
- **Voiceover Script**:
  > *"The build runs. CONFORM recompiles only the dirty subtree. The 12 localized copy and package assets are generated, while the other 240 assets—including the costly Veo video clips and Imagen keyframes—are reused byte-for-byte from cache at zero cost. That is cache determinism in action."*

---

### Beat 5: Self-Healing Retry Taxonomy (1:40 – 2:05)
- **On-Screen**:
  - Toggle the **Dynamic Fault Injection Switch** (`Simulate Transient 503: ACTIVE`).
  - Explain the retry classification taxonomy: transient vs permanent vs policy.
  - Highlight automatic retry recovery with `parent_run_id` lineage.
- **Voiceover Script**:
  > *"Generative endpoints fail frequently with rate limits and 503 timeouts. CONFORM implements a rigorous retry taxonomy. Transient errors automatically retry with deterministic backoff while preserving parent run lineage, completing without human intervention, while permanent prompt errors fail immediately."*

---

### Beat 6: ClickHouse Analytics & Natural Language Analyst (2:05 – 2:35)
- **On-Screen**:
  - Switch to **Slate Analytics** tab (`📊 Slate Analytics`).
  - Showcase the 4 KPI cards: Avoided Spend ($ saved), Incurred Spend, Cache Hit Rate (95%), and the Compilation Efficiency Gauge.
  - Review the AI Model spend breakdown table (Veo, Imagen, Gemini, FFmpeg) and Campaign runs table.
  - Switch to **Ask the Slate** tab (`💬 Ask the Slate (MCP)`).
  - Click suggestion chip: *"What is our spend across models?"*.
  - View the Analyst Agent's natural language response, the executed read-only SQL, and the live ClickHouse data table.
- **Voiceover Script**:
  > *"Every single attempt, cache hit, and provider call is streamed into ClickHouse. In the analytics dashboard, we see the cumulative avoided spend and model cost breakdowns. Through the official ClickHouse MCP server, our natural-language Analyst Agent lets producers ask questions over slate history. The agent generates read-only, guard-railed SQL and explains the results grounded strictly in ClickHouse rows."*

---

### Beat 7: Release Verification & Tamper Proof (2:35 – 2:55)
- **On-Screen**:
  - Switch back to **Build & Verify** tab (`🔨 Build & Verify`).
  - In the Verification Studio, click **"🔍 Verify Release (SHA-256 Byte-Exact)"**.
  - Shows green banner: `✓ All artifacts verified byte-exact against immutable manifest`.
  - Click **"⚠️ Corrupt 1 Byte in Storage (Tamper Demo)"**.
  - Notice alert: First byte corrupted in storage.
  - Click **"🔍 Verify Release (SHA-256 Byte-Exact)"** again.
  - Instant red failure: `✗ Verification FAILED — Cryptographic hash mismatch detected!`.
  - Shows specific tampered artifact flagged in red as `✗ MISMATCH (TAMPERED)`.
- **Voiceover Script**:
  > *"Finally, releases in CONFORM are cryptographically verifiable. When we click Verify Release, every artifact is re-downloaded from storage and hashed against the recorded SHA-256. To prove tamper detection, we corrupt just one byte in storage. When we re-verify, CONFORM immediately flags the tampered artifact in red. What you approved is mathematically what gets shipped."*

---

### Beat 8: Outro (2:55 – 3:00)
- **On-Screen**:
  - Return to the overview header showing green verified status.
- **Voiceover Script**:
  > *"CONFORM brings compiler discipline to generative media. Compile your media—don't regenerate it. Check out the open-source repository on GitHub and our live demo."*

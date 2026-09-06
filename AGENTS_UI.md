# AGENTS_UI.md — CONFORM Frontend & UX Architecture

Guidance for AI agents working on the CONFORM web interface (`web/`).
Assumes no prior knowledge of the project. Read this file alongside [`AGENTS.md`](file:///c:/Users/adeto/Documents/CONFORM/AGENTS.md) and [`docs/PRD.md`](file:///c:/Users/adeto/Documents/CONFORM/docs/PRD.md).

---

## 1. What This Document Is

This document defines the **frontend architecture, the narrative mental model, the user experience (UX) flow, and the interaction state transitions** of CONFORM.

It tells an agent:
- What CONFORM's interface actually does.
- The real-world problem and demo story it communicates.
- How the user moves through the 6-stage workflow.
- The UI state machine and component hierarchy.
- The technical constraints and invariant laws that the frontend must strictly enforce.

*(Note: This file does not prescribe cosmetic redesign recommendations; it documents the functional UX contracts and narrative architecture as designed.)*

---

## 2. What CONFORM Is (The Mental Model)

CONFORM is a **compiler for generative media pipelines**, built for the **Agentic Cinema Hackathon** (ClickHouse Track).

### The Real-World Problem
In global advertising and film production, a master campaign (brief → shot plan → keyframe stills → video clips → copy → voiceover → music → final muxed packages) fans out across **40 localized territory variants**. 

A single slate contains **over 250 individual media assets**. Generating video clips using AI (e.g. Google Veo) is the single most computationally expensive and time-consuming operation in the pipeline.

When an advertising regulation changes—for example, a new European Union Directive mandates a longer disclaimer text in Germany and France:
- **Traditional generative workflows** do not track fine-grained input dependencies. Because they cannot isolate what changed, they **regenerate everything** across all 40 countries, burning thousands of dollars in redundant GPU compute.
- **The "40 Cakes" Analogy**: It is equivalent to baking 40 cakes, discovering that one cherry in France needs to be replaced, and throwing all 40 cakes in the trash to re-bake them all from scratch.

### The CONFORM Solution
CONFORM treats the media production slate as a **Directed Acyclic Graph (DAG)** with **content-addressed caching (JCS RFC 8785 + SHA-256)**:
1. It analyzes the exact **blast radius** of a prompt or rule change.
2. It detects that only **12 copy/package assets** are dirty, while **240 assets** (including all expensive video clips and audio) are untouched.
3. It quotes the exact rebuild bill ($0.0030) versus naive regeneration ($0.0630), proving **95%+ avoided spend**.
4. It halts at a **strict Human Approval Gate**—no generative model can be called before an authorized human signs off.
5. It rebuilds **only the 12 dirty assets**, reusing the 240 clean assets byte-for-byte from cache at **$0.00 cost**.
6. It logs every event to **ClickHouse Cloud** and provides an NL Analyst Agent querying through the official **`mcp-clickhouse`** server.
7. It cryptographically seals the release with a SHA-256 manifest and detects **1-byte storage tampering** live.

---

## 3. The 6-Stage Narrative Workflow

The frontend organizes user interaction around an explicit **6-stage guided narrative stepper**:

```
[1 · Propose Change] ➔ [2 · Blast Radius & Graph] ➔ [3 · Approval Gate]
         ➔ [4 · Rebuild & Retries] ➔ [5 · Byte-Exact Verify] ➔ [6 · Slate Analytics]
```

### Stage 1: Propose Change (`ChangeView.tsx`)
- **User Action**: The user selects one of three preset demo scenarios or types a custom instruction:
  1. *🇪🇺 EU Regulation Change* (R-DISC-004 on de/fr copy: 12 dirty, 240 reused, ~$0.0030 spend).
  2. *🎬 Master Clip Reshoot* (Hero prompt edit: 41 dirty, 211 reused).
  3. *🇯🇵 Japan Winter Retargeting* (Tokyo text edit: 2 dirty, 250 reused).
- **Interactive Transition**: Clicking a scenario card populates the prompt, illuminates the card, and prompts the user to calculate the impact.
- **Agent Integration**: Features both deterministic analysis and autonomous multi-step execution via the `POST /api/agents/adk/execute` endpoint using Google ADK (`google-adk`).

### Stage 2: Blast Radius & 3D Graph (`GraphView.tsx`)
- **User Action**: Clicking **"⚡ Compute Blast Radius"** calls `POST /api/changes` followed by `POST /api/changes/{id}/estimate`.
- **System Response**:
  - Highlights the **12 dirty nodes** in amber with pulsing glows.
  - Dims clean nodes to indicate cache reuse.
  - Displays the **Compilation Savings Callout** ($0.0030 spend vs $0.0630 naive spend; 95% spend avoided).
  - Offers **"🧊 Inspect 3D Graph (Step 2) ➔"** to view the multi-campaign DAG.
- **Graph View**:
  - SVG layout with master spines on the left and 40 territory variants gridded on the right.
  - Features an interactive **"🧊 3D Hologram Tilt"** toggle that projects the DAG in 3D isometric perspective.
  - Nodes are styled as 3D specular spheres with radial gradients.
  - Clicking any node opens the **Provenance Inspector Rail** (`NodeInspector.tsx`), showing exact SHA-256 fingerprints, parent dependencies, and invalidation reason codes.

### Stage 3: Human Approval Gate (`ChangeView.tsx`)
- **Invariant**: The LLM / Deterministic Boundary strictly forbids generative API calls before human authorization.
- **User Action**: The user reviews the quoted cost and clicks **"✓ Approve Spend ($0.0030)"** (or "Reject").
- **Interactive Transition**:
  - Calls `POST /api/changes/{id}/approve` with actor role `"producer (simulated)"`.
  - The gate status badge switches from amber `🛑 Awaiting Human Approval` to glowing green `✓ Approved by Producer`.
  - Unlocks and illuminates the **"🚀 Build Dirty Subtree (Step 4) ➔"** button with an electric pulsing glow.

### Stage 4: Surgical Rebuild & Retries (`TimelineView.tsx`)
- **User Action**: The user clicks **"🚀 Build Dirty Subtree"**.
- **System Response**:
  - Calls `POST /api/changes/{id}/build`.
  - Automatically navigates the user directly to the **Build & Verify** tab (`TimelineView.tsx`).
  - Executes rebuild for dirty nodes only; clean nodes are recorded as `cache_hit: 1` ($0.00 spend).
  - Displays run rows with attempt numbers and indented retry lineage (`↳ node_id ← parent parent_run_id`).
  - Includes a **Dynamic Fault Injection Switch** (`POST /api/system/fault-injection`) to simulate transient HTTP 503 errors and prove automatic retry resilience.

### Stage 5: Byte-Exact Verification & Tamper Studio (`TimelineView.tsx`)
- **Purpose**: Demonstrates zero-trust release integrity.
- **User Action**:
  - Clicking **"Verify Release"** calls `GET /api/releases/{id}/verify`. All artifacts are re-downloaded and re-hashed against the immutable SHA-256 release manifest (`VERIFIED (BYTE-EXACT)`).
  - Clicking **"Corrupt 1 Byte (Tamper Demo)"** calls `POST /api/system/tamper`, intentionally flipping the first byte of an artifact in storage.
  - Clicking **"Re-verify Release"** immediately detects the corruption and renders an instant **red `MISMATCH (TAMPERED)`** security alert.

### Stage 6: Slate Analytics & Ask the Slate (`AnalyticsView.tsx`, `AskView.tsx`)
- **Analytics View**:
  - Queries ClickHouse materialized views (`GET /api/analytics/summary`).
  - Displays Total Spend ($) vs Avoided Spend ($), Cache Hit Rate %, and visual Compilation Efficiency Gauge.
  - Tabulates model spend (Gemini, Imagen, Veo, Chirp, Lyria) and per-campaign spend.
- **Ask the Slate (MCP NL Analyst)**:
  - User types a natural language question (or clicks one of 6 suggestion chips).
  - Calls `POST /api/analytics/ask`, where the Analyst Agent translates NL to guarded `SELECT` SQL.
  - Queries ClickHouse Cloud through the official `mcp-clickhouse` MCP server via JSON-RPC 2.0.
  - Returns a natural language explanation grounded in real table rows with direct SQL inspection.

---

## 4. Frontend Component Hierarchy

```
web/src/
├── App.tsx                     # Top-level state, header, status chips, 6-stage stepper, tab router
├── api.ts                      # Typed API client (13 endpoints mapping to FastAPI)
├── types.ts                    # TypeScript interfaces mirroring backend domain schemas
├── styles.css                  # Global design system: dark cyber-cinema aesthetic, 3D perspectives, neon accents
├── components/
│   └── DirectorStoryGuide.tsx  # Plain-English walkthrough banner explaining each step's context
└── views/
    ├── ChangeView.tsx          # Step 1 & Step 3: Preset scenarios, blast radius estimate, approval gate, ADK trigger
    ├── GraphView.tsx           # Step 2: SVG DAG canvas, 3D isometric tilt mode, filters, sphere nodes
    ├── NodeInspector.tsx       # Step 2: Slide-out provenance rail for inspected nodes
    ├── TimelineView.tsx        # Step 4 & Step 5: Execution runs, retry hierarchy, fault toggle, tamper studio
    ├── AnalyticsView.tsx       # Step 6: ClickHouse telemetry dashboard, KPI cards, efficiency gauge
    └── AskView.tsx             # Step 6: Natural language to SQL analyst querying ClickHouse MCP
```

---

## 5. Non-Negotiable UX Invariants

When modifying or extending the frontend, AI agents must preserve these rules:

1. **The Approval Gate Invariant**:
   - The UI must never allow the build to trigger without approval on record.
   - If an estimate has not been approved, the build action must remain disabled or gated behind `approve()`.
2. **Deterministic Honesty & Truthful Labelling**:
   - Fallback modes must be visibly tagged (e.g. `fallback_stub`, `fallback_sqlite`, `fallback_direct`). Never disguise offline fallbacks as live integrations.
   - Actor roles must be clearly labelled as simulated (e.g. `"producer (simulated)"`).
3. **Currency & Financial Precision**:
   - Currency values (`estimated_cost_usd`, `total_spend_usd`, `avoided_spend_usd`) must be handled as strings or exact decimals to preserve backend `Decimal` precision. Never round with floating-point math on cross-boundary contracts.
4. **Contextual Plain-English Continuity**:
   - The `DirectorStoryGuide` must remain connected to `activeStep`. When the step or tab changes, the plain-English explanation must update to reflect the user's current stage in the narrative.
5. **No Third-Party AI Integrations**:
   - Do not add client-side SDKs or API calls to non-Google AI services (OpenAI, Anthropic, fal, Replicate, ElevenLabs, etc.). Only Google Cloud AI endpoints and the official ClickHouse MCP reader are permitted.

# CONFORM — Devpost Submission Package

**Hackathon**: Agentic Cinema: The Blockbuster Hackathon  
**Track**: ClickHouse Partner Track  
**Repository**: Public GitHub Repository (Apache-2.0 License)  

---

## 1. Submission Overview

- **Project Title**: CONFORM — Compiler for Generative Media Slates
- **Tagline / Short Pitch**: A deterministic compiler and Google ADK agent for generative cinema pipelines that computes exact blast radiuses, prevents redundant generation spend, and proves cryptographic release integrity.
- **Partner Track**: ClickHouse Partner Track

---

## 2. Devpost Form Answers

### Inspiration
In global entertainment and advertising production, creative slates fan out exponentially. A single master campaign—composed of brief, shot plan, keyframe stills, video clips, voiceover, music, and muxed packages—expands across 40 localized territory variants.

When a regional advertising regulation changes (e.g. European Union Directive requiring a longer allergy disclaimer in Germany and France), existing AI pipelines face a catastrophic dilemma: because modern workflows do not track fine-grained input dependencies, studios are forced to **regenerate everything**.

Video generation models like Veo are the single most computationally expensive component in the pipeline. Re-generating unchanged video clips and keyframe renders for a disclaimer text edit burns thousands of dollars in redundant compute. We asked ourselves: *Why don't generative media pipelines have a compiler like software engineering has had for 50 years?*

---

### What It Does
**CONFORM** models an entire global media production slate as a content-addressed **Directed Acyclic Graph (DAG)**.

1. **JCS + SHA-256 Fingerprinting**: Every node in the pipeline is fingerprinted over its exact inputs and recipe using RFC 8785 JSON Canonicalization Scheme (JCS) and SHA-256.
2. **Pre-Spend Blast Radius & Cost Estimation**: When a prompt or compliance rule changes, CONFORM computes the exact dirty subtree across all campaigns and territories. On an EU regulation change, CONFORM isolates that only **12 of 252 assets** are dirty, and **240 assets are clean**.
3. **95%+ Cost Avoidance**: CONFORM shows producers the exact rebuild cost ($0.0030) versus naive regeneration ($0.0630)—quantifying over 95% in avoided spend before calling a single generative API.
4. **Enforced Human Approval Gate**: The system strictly forbids generative model invocation until an authorized human producer reviews the blast radius and approves the spend.
5. **Incremental Rebuild with Proven Reuse**: CONFORM rebuilds only the 12 dirty assets. The untouched 240 assets (including expensive video clips and audio) are reused byte-for-byte directly from content-addressed storage at $0.00 cost.
6. **Telemetry in ClickHouse via Official MCP Server**: Every attempt, cache hit, and provider call is streamed into ClickHouse Cloud. A natural-language **Analyst Agent** answers questions over slate history by generating guarded, read-only SQL executed through the official `mcp-clickhouse` server.
7. **Cryptographic Release Verification**: Releases are immutable manifests. CONFORM re-downloads every artifact from storage and verifies its SHA-256 byte-exact. In our live demo, flipping a single byte in storage triggers an instant red `MISMATCH (TAMPERED)` verdict, proving zero-tampering.

---

### How We Built It

- **Google Cloud & Gemini Agent Platform**:
  - **`google-adk` (Google Agent Development Kit v2.8.0)**: Powers autonomous multi-step agent orchestration with typed tools (`interpret_and_estimate`, `approve_spend`, `build_dirty_subtree`, `verify_release`, `query_slate_history`).
  - **`google-genai` (v2.22.0)**: Connects to Vertex AI for Gemini 3 Pro (shot planning, schema-constrained structured output), Gemini 3.1 Flash (copy generation), Imagen 4 (keyframes), and Veo 3.1 (video).
  - **Google Cloud Storage (`google-cloud-storage`)**: Content-addressed artifact storage addressed strictly by SHA-256 hex digest.
- **ClickHouse Cloud & Model Context Protocol (MCP)**:
  - **Write Path**: `clickhouse-connect` streams batched events into real-time analytical tables (`node_runs`, `provider_calls`, `build_events`, and the `build_savings_mv` materialized view).
  - **Read Path**: The Analyst Agent queries ClickHouse exclusively through the official **`mcp-clickhouse` Model Context Protocol (MCP) server** via JSON-RPC 2.0 (`run_select_query`).
  - **Guarded SQL**: Pure-Python AST allowlist enforcing single, read-only `SELECT` queries with row ceilings and mutation blocklists.
- **Deterministic Core (Pure Python)**:
  - Strict architectural law: `app/core/` contains **zero LLM or provider dependencies**, enforced by an automated AST boundary test (`test_boundary.py`).
  - Canonicalization follows RFC 8785; graph closure and dirty-set resolution are pure deterministic graph theory.
- **Frontend & Visual DAG Visualizer**:
  - React 19 + TypeScript + Vite with custom canvas/SVG DAG rendering.
  - Interactive multi-campaign filter toolbar, dirty-set amber glow rings, and real-time provenance inspector rail.

---

### Challenges We Ran Into

1. **The Determinism Fallacy**: Generative AI models are fundamentally non-deterministic; identical prompts produce different pixels or audio frames. We solved this with **cache determinism**: the fingerprint covers exact inputs plus the recipe. Once an artifact is generated and content-addressed, its bytes are immutable. Identical inputs + identical recipe reuse existing bytes without regeneration.
2. **Preserving the Deterministic Boundary**: Ensuring that LLMs never hallucinate numbers, costs, or blast radiuses. We instituted a strict architectural rule: Gemini may only *interpret* unstructured text into typed contracts and *explain* results it was handed. All arithmetic, graph traversal, and verification verdicts are pure deterministic code.
3. **MCP Protocol Integration**: Connecting our natural-language agent to the official ClickHouse MCP server over HTTP streaming transports while enforcing strict read-only SQL safety contracts.

---

### Accomplishments That We're Proud Of

- **116 automated tests** with 100% pass rate, including AST architectural boundary enforcement and mocked MCP server round-trip tests.
- **95%+ spend reduction** proven live on realistic multi-campaign 40-territory fixtures.
- **Cryptographic tamper detection**: A visceral demo feature where flipping 1 byte in storage immediately causes release verification to fail red.
- **Production-grade container**: Multi-stage Dockerfile with Node 22 frontend compilation, Python 3.12 runtime, and FFmpeg media packaging ready for Google Cloud Run.
- **Zero prohibited AI dependencies**: 100% Google Cloud AI + ClickHouse partner technology.

---

### What We Learned
Applying classic compiler design (lexing/parsing → dependency graph → topological sort → dirty subtree resolution → content-addressed caching → bytecode verification) completely transforms generative AI from an unpredictable, budget-burning prototype into a dependable, enterprise-grade engineering discipline.

---

## 3. Technology Stack & Integration Details

| Category | Technology | Usage |
|---|---|---|
| **Agent Platform** | `google-adk==2.8.0` | Autonomous multi-step compilation orchestration and tool calling |
| **Generative AI** | `google-genai==2.22.0` | Gemini 3 Pro, Gemini 3.1 Flash, Imagen 4, Veo 3.1 on Vertex AI |
| **Object Storage** | `google-cloud-storage==3.13.1` | Content-addressed SHA-256 artifact store |
| **Partner Database** | `clickhouse-connect==1.8.0` | ClickHouse Cloud event logging and materialized cost analytics |
| **Partner Protocol**| `mcp-clickhouse` | Official Model Context Protocol reader for natural language SQL agent |
| **Backend API** | FastAPI + Uvicorn | High-performance async Python backend with typed Pydantic v2 schemas |
| **Frontend UI** | React 19 + TypeScript + Vite | Cinematic glassmorphism DAG visualizer and verification studio |
| **Deployment** | Docker on Google Cloud Run | Multi-stage production container with embedded FFmpeg packaging |

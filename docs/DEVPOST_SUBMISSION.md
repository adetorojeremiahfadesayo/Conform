# CONFORM — Devpost Submission Package

**Hackathon**: Agentic Cinema: The Blockbuster Hackathon  
**Track**: ClickHouse Partner Track  
**Repository**: [https://github.com/adetorojeremiahfadesayo/Conform](https://github.com/adetorojeremiahfadesayo/Conform) (Apache-2.0 License)  
**Live Hosted Demo**: [https://conform-tiwoc77ijq-ew.a.run.app](https://conform-tiwoc77ijq-ew.a.run.app)  

---

## Inspiration

If you edit one typo on page 42 of a printed book, you don't pay an author to rewrite the entire book from chapter one. You just reprint page 42.

Yet in modern AI video production, that is exactly what happens. In global advertising, a single master commercial fans out across **40 localized country variants** (different languages, regional disclaimers, and local voiceovers). When an advertising regulation changes—for instance, a new European Union directive mandating a longer battery recycling disclaimer in Germany and France—current AI media pipelines face a catastrophic dilemma: because existing workflows lack dependency tracking, studios are forced to **regenerate everything from scratch**.

Generative video models like **Google Veo 3.1** are the single most computationally intensive and expensive component in AI today ($0.05+ per clip, 30–60 seconds of GPU time). Re-rendering unchanged car chases, landscapes, and character scenes across 40 countries just to update a text disclaimer burns thousands of dollars in wasted cloud credits and introduces random visual errors.

We asked ourselves: *Software engineering has had incremental build compilers (`make`, `webpack`, `turborepo`) for 50 years. Why are generative video pipelines still regenerating everything like it's 1970?*

We built **CONFORM** to be the first smart build compiler and Google ADK orchestrator for AI video slates.

---

## What it does

**CONFORM** turns chaotic generative media pipelines into an organized, deterministic **production graph (DAG)**. It tracks the exact recipe of every asset, figures out what actually changed, shows you the bill before you spend a dime, and rebuilds only what is necessary.

Here is how it works:

1. **Maps the Production Flowchart (The Recipe Tree):** Models the entire campaign across all 40 countries as a connected pipeline: Brief $\rightarrow$ Shot Plan $\rightarrow$ Imagen 4 Keyframes $\rightarrow$ Veo 3.1 Video Clips $\rightarrow$ Gemini Localized Copy $\rightarrow$ Chirp 3 HD Voiceovers $\rightarrow$ Lyria 2 Music $\rightarrow$ Final Packaged MP4.
2. **Finds the Splash Zone (Blast Radius):** When a creative prompt or compliance rule changes, CONFORM traces the exact ripple effect. For an EU disclaimer update, CONFORM isolates that only **12 of 252 assets** need updating—**240 assets are completely clean**.
3. **Shows the Bill Before Spending (Pre-Spend Estimation):** Quotes the exact rebuild cost (**$0.0030**) versus naive regeneration (**$0.0630**)—quantifying over **95.2% in avoided cloud spend** before touching a single generative API.
4. **The Credit-Card Safeguard (Human Approval Gate):** All video generation calls are physically locked. It is impossible for the AI to call video models or charge money until an authorized human producer reviews the quote and clicks "Approve".
5. **Incremental Rebuild with Proven Reuse:** Rebuilds only the 12 dirty text and package files in 2 seconds. The 240 clean assets (including expensive Veo video clips, Imagen stills, and music tracks) are fetched instantly from storage at **$0.00 cost**.
6. **Real-Time Financial Accountant (ClickHouse Telemetry via Official MCP):** Every millisecond, token count, retry attempt, and fractional cent is streamed into ClickHouse Cloud. An AI Analyst answers questions over slate history in plain English (*"What did we spend across models?"*, *"Which countries had the highest cache hit rate?"*) through the official **`mcp-clickhouse`** server.
7. **The Digital Tamper-Seal (Byte-Exact Verification):** Cryptographically re-hashes every delivered file against expected SHA-256 digests. In our live demo, flipping a single byte in storage triggers an instant red `MISMATCH (TAMPERED)` verdict, giving clients proof of delivery integrity.

---

## How we built it

We engineered CONFORM around a strict architectural law: **Gemini interprets human intent and explains data; pure deterministic Python and ClickHouse handle all math, fingerprints, and verification.**

### 1. The Generative Foundation AI Crew (Google Cloud / Vertex AI)
- **Google Veo 3.1 (`veo-3.1-fast-generate-001`):** *The Cinematographer.* Generates 4–8 second high-motion cinematic footage. Because it represents >80% of pipeline compute, CONFORM freezes Veo outputs in content-addressed storage and reuses them across 40 countries at $0.00 cost whenever visual content doesn't change.
- **Google Imagen 4 (`imagen-4`):** *The Concept Artist.* Generates crisp reference still frames from the shot plan, anchoring actor appearance, lighting, and wardrobe so video generation never suffers from visual drift.
- **Google Gemini 3 Pro:** *The Film Director.* Interprets messy briefs into structured contracts, plans 8-axis camera coverage (lens, focal length, blocking, lighting), and powers the natural-language analytical assistant.
- **Google Gemini 3.1 Flash:** *The Multilingual Copywriter.* Generates localized headlines, callouts, and legal disclosures across 40 countries in milliseconds under strict JSON schema constraints.
- **Google Chirp 3 HD & Lyria 2:** *The Voice Actors & Orchestra.* Produces studio-grade multilingual voiceover timed to video shot boundaries, plus custom soundtrack scores.
- **FFmpeg (Zero AI):** *The Post-Production Video Editor.* Handles final media muxing, audio leveling (-24 LKFS), and timed subtitle burning using pure deterministic binaries—guaranteeing zero AI hallucinations at the packaging step.

### 2. Autonomous Agent Orchestration (`google-adk==2.8.0`)
- Built on the official **Google Agent Development Kit**.
- Defines 6 typed tools (`interpret_and_estimate`, `approve_spend`, `build_dirty_subtree`, `verify_release`, `query_slate_history`, `tamper_artifact`).
- Features an agentic **Pause & Resume Gate**: multi-step workflows autonomously analyze briefs and quote costs, but halt at `AWAITING_APPROVAL`, returning a resumption token that requires human confirmation before spending.

### 3. Telemetry & Financial Engine (ClickHouse Partner Track)
- **Write Path (`clickhouse-connect` v1.8.0):** Batches and streams execution telemetry into ClickHouse Cloud (`node_runs`, `provider_calls`, `build_events`).
- **Materialized Savings Engine (`build_savings_mv`):** Computes live cumulative dollars saved by comparing baseline regeneration costs against incremental execution.
- **Official MCP Read Path (`mcp-clickhouse` v0.6.0):** The AI Analyst Agent queries ClickHouse exclusively through the official Python MCP server running as an authenticated loopback sidecar (`app/serve.py`) over streamable HTTP JSON-RPC 2.0.
- **AST-Guarded SQL:** In-process SQL parsing enforces read-only `SELECT` statements with mandatory `LIMIT` clauses, preventing query injection.

### 4. Deterministic Core & Frontend
- **Cryptographic Fingerprinting:** Pure Python RFC 8785 JSON Canonicalization Scheme (JCS) + SHA-256 DAG hashing. AST boundary tests (`tests/test_boundary.py`) ensure calculation code imports zero LLMs.
- **Visual Slate Studio:** React 19 + TypeScript + Vite DAG visualizer with amber dirty-glow indicators, inspection rails, and live tamper demonstration studio.
- **Production Deployment:** Multi-stage Dockerfile packaging frontend, backend, FFmpeg, and official MCP sidecar deployed to **Google Cloud Run** in Public Judge Mode.

---

## Challenges we ran into

1. **The Determinism Fallacy (AI Models are Random):** Generative video models never produce identical frames twice. Claiming model determinism is dishonest. We solved this with **Cache Determinism**: fingerprints cover exact inputs plus the recipe. Once generated, artifacts are content-addressed and immutable. Identical inputs + recipe reuse existing bytes without re-running the model.
2. **The LLM / Deterministic Boundary:** LLMs hallucinate numbers, costs, and hashes. We established a non-negotiable boundary: Gemini only interprets unstructured text and explains data. Graph traversal, dirty-set resolution, Decimal cost math, retry classification, and verification verdicts are pure deterministic code.
3. **Official ClickHouse MCP Integration:** Connecting an autonomous agent to the official ClickHouse MCP server required establishing an authenticated loopback HTTP sidecar with zero client-side credential exposure and strict AST-based read-only SQL safety guards.
4. **Protecting Cloud Budgets in a Public Demo:** Public evaluators need to test the workflow live without draining the studio's cloud credits. We engineered **Public Judge Mode**: running under a `conform-judge` service account with storage object-viewer access only and **zero Vertex AI permissions**. Uncached requests are safely rejected, while cached generation, approval gates, ClickHouse MCP queries, and in-memory byte tampering remain 100% interactive.

---

## Accomplishments that we're proud of

- **125 Automated Tests (100% Pass Rate):** Comprehensive test suite in `pytest` covering AST import boundaries, Public Judge Mode security, concurrency lifecycle, and ClickHouse MCP streaming round-trips.
- **95.2% Proven Cost Reduction:** Demonstrating live that an EU regulation update rebuilds 12 assets for $0.0030 instead of $0.0630 across 252 nodes.
- **Zero Disallowed AI Frameworks:** 100% compliant with hackathon rules—powered exclusively by Google Cloud AI (`google-genai`, `google-adk`) and ClickHouse partner technology. No OpenAI, Anthropic, or third-party video APIs.
- **Visceral Tamper Studio:** A live demo feature where corrupting a single byte of storage immediately turns release verification bright red (`MISMATCH / TAMPERED`), proving mathematical delivery integrity.
- **Clean Architecture & Apache-2.0 License:** Public, cold-cloneable open-source repository with zero hardcoded secrets and complete documentation.

---

## What we learned

- **Classic compiler design transforms AI:** Applying principles from traditional compilers (lexing $\rightarrow$ dependency graph $\rightarrow$ topological sort $\rightarrow$ dirty subtree resolution $\rightarrow$ content-addressed caching $\rightarrow$ bytecode verification) turns generative AI from an unpredictable, budget-burning novelty into an enterprise-grade engineering discipline.
- **Video AI is too expensive to run naively:** Video generation is the single biggest cost bottleneck in AI. Pre-spend cost estimation and enforced human approval gates are essential for making generative media commercially viable.
- **Columnar databases are born for AI telemetry:** ClickHouse's sub-millisecond aggregations over high-cardinality multi-territory pipeline runs make real-time financial auditing and natural-language analysis seamless.

---

## What's next for CONFORM

- **Direct Ad-Network Publishing:** Pushing compiled, verified media releases directly into Google Ads, YouTube Campaigns, and Meta Ads Manager with automated geo-targeting.
- **Real-Time Video A/B Compiler:** Compiling branching visual variants (e.g. 3 hook openings $\times$ 2 call-to-actions) while caching and sharing the expensive main body of the video.
- **Multi-Studio Distributed Cache:** Enabling global production teams to share content-addressed Veo video and Imagen assets across regional Google Cloud Storage buckets.
- **Expanded Media Formats:** Adding 3D Gaussian splats and interactive video nodes into the compilation graph.

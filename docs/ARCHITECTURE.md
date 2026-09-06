# ARCHITECTURE — CONFORM

**A Compiler for Generative Media Pipelines.**

Submitted to the **Agentic Cinema: The Blockbuster Hackathon** — **ClickHouse Partner Track**.

---

## 1. System Overview

Generative media production for multi-territory advertising campaigns suffers from high regeneration costs. When an advertising regulation, disclaimer, or creative prompt changes in a few territories, existing tools regenerate the entire campaign slate because they lack asset-level dependency awareness.

CONFORM introduces **compilation semantics** to generative pipelines:
1. Represents the campaign slate as an explicit **directed acyclic graph (DAG)**.
2. Fingerprints each node deterministically from its exact inputs, recipe, and parent fingerprints using **JCS canonicalization (RFC 8785) + SHA-256**.
3. Evaluates project compliance rules and user edits to compute an exact **blast radius** before any generation occurs.
4. Enforces an **explicit human approval gate** before spending money.
5. Rebuilds **only the dirty subtree**, reusing clean artifacts byte-for-byte from cache.
6. Emits structured telemetry for every node attempt and model call into **ClickHouse**.
7. Provides an **Analyst Agent** querying slate history through the official **ClickHouse MCP server**.
8. Produces **independently verifiable releases** with byte-exact SHA-256 tamper detection.

---

## 2. The Core Law: The LLM / Deterministic Boundary

A core principle of CONFORM is strict separation between probabilistic language models and deterministic computation:

```
Brief / Rule Change Text
           │
           ▼
┌──────────────────────────────────────────────┐
│  LLM / Interpretation Layer (Google Gemini)  │  ◄── Allowed ONLY to interpret text
│  - Change text → typed ChangeIntent contract │      into typed contracts or explain
│  - Analyst question → SQL query generation   │      returned database rows.
│  - Query rows → row-grounded explanation     │
└──────────────────────┬───────────────────────┘
                       │ Validated Pydantic Contracts
                       ▼
┌──────────────────────────────────────────────┐
│  Deterministic Core Engine (Pure Python/SQL) │  ◄── Zero LLM imports allowed.
│  - JCS Canonicalization (RFC 8785 subset)   │      Guaranteed by test_boundary.py
│  - SHA-256 content-addressed fingerprinting  │
│  - DAG traversal & Kahn topological sort     │
│  - Transitive closure & blast radius matrix  │
│  - Rule engine predicate evaluation          │
│  - Cost & time arithmetic (Decimal, no float)│
│  - Retry taxonomy & backoff classification   │
│  - Byte-exact SHA-256 verification verdicts │
└──────────────────────┬───────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌───────────────────┐       ┌───────────────────────────────────┐
│ Vertex AI / Local │       │ ClickHouse Telemetry & Analytics  │
│ - Veo 3.1 (video) │       │ - Writes: clickhouse-connect      │
│ - Imagen 4 (image)│       │ - Reads:  mcp-clickhouse MCP      │
│ - Gemini (copy)   │       │ - Materialized views for savings  │
│ - FFmpeg (package)│       │ - Row-grounded analyst queries    │
└───────────────────┘       └───────────────────────────────────┘
```

### Invariants Enforced in Code
- An LLM must **never** compute a fingerprint, cost, blast radius, or verification verdict.
- Any unvalidated LLM output is rejected at the Pydantic schema boundary.
- All monetary arithmetic uses Python `Decimal`, never IEEE 754 floating-point numbers.
- Automated tests (`test_boundary.py`) inspect the AST of `app/core/` to guarantee no imports of `google.genai`, `app.providers`, or `app.agents`.

---

## 3. Fingerprinting & Cache Determinism

Generative models are inherently non-deterministic. CONFORM does not claim generative model determinism; instead, it implements **cache determinism**:

$$ \text{Fingerprint} = \text{SHA-256}(\text{JCS}(\text{inputs} \mathbin{\Vert} \text{recipe} \mathbin{\Vert} \text{parent\_fingerprints})) $$

- **RFC 8785 Canonical JSON (JCS)**: Keys are lexicographically sorted; whitespace is eliminated; numbers use exact representations. Serializations are identical across processes, languages, and platforms.
- **Parent Propagation**: A node's fingerprint cryptographically commits to all upstream dependencies. If an upstream master clip changes, all downstream localized packages automatically get new fingerprints.
- **Content Addressing**: Artifacts in Google Cloud Storage or local storage are keyed by content fingerprint. If a node's computed fingerprint already exists in the artifact store, it is reused by reference—zero API calls and zero USD spent.

---

## 4. Graph Structure & 40-Way Territory Fan-Out

A production slate consists of multiple master campaigns (e.g. `campaign_a`, `campaign_b`, `campaign_c`).

Each master campaign defines an upstream creative spine:
$$\text{source} \longrightarrow \text{shot\_plan} \longrightarrow \text{keyframe} \longrightarrow \text{clip}$$

The expensive video clip fans out to 40 territory variants (`us`, `gb`, `de`, `fr`, `jp`, etc.):
$$\text{clip} + \text{copy}_{territory} \longrightarrow \text{package}_{territory}$$

When a regulation changes in the EU (e.g. France and Germany require expanded disclaimers):
- Only `copy.de`, `copy.fr`, `package.de`, and `package.fr` are dirty (12 of 252 nodes across 3 campaigns).
- Upstream `source`, `shot_plan`, `keyframe`, and `clip` remain clean.
- All non-EU territories remain clean.
- **240 of 252 nodes are reused byte-for-byte.**

---

## 5. ClickHouse Dual-Path Architecture

ClickHouse serves as the append-only event store for slate telemetry:

1. **Write Path (Driver)**:
   - Pipeline build runs emit batched telemetry via `clickhouse-connect` directly to ClickHouse Cloud.
   - Tables: `node_runs`, `provider_calls`, `artifacts`, `graph_closure`, `rule_findings`.
   - `build_savings_mv` (SummingMergeTree) aggregates real-time metrics on nodes reused, nodes rebuilt, spend incurred, and spend avoided.
2. **Read Path (MCP Server)**:
   - The Analyst Agent reads build history exclusively through the official `mcp-clickhouse` server over HTTP JSON-RPC.
   - All analyst queries are strictly guard-railed: single `SELECT` statement only, enforced row limits, and rejection of write/DDL keywords.
   - The frontend displays the exact executed SQL alongside the MCP reader status.

---

## 6. Verification & Tamper Detection

Releases in CONFORM are immutable sets of content-addressed artifacts:
- When a build finishes, it outputs `release_NNN`.
- `verify_release()` downloads every artifact from GCS/local storage, computes `SHA-256(bytes)`, and verifies it matches the build record.
- **Tamper Demonstration**: A dedicated tamper endpoint corrupts one byte in storage. Re-running verification immediately flags that specific artifact as `MISMATCH` in red, proving tamper detection.

---

## 7. Deployment

- **Container**: Multi-stage `Dockerfile` compiles the Vite/React TypeScript application into static assets and packages the FastAPI application.
- **Hosting**: Cloud Run serves both backend API endpoints and frontend SPA routes from a single unified container.
- **Graceful Fallback**: If deployed without cloud credentials, CONFORM functions in fully labelled fallback modes (`fallback_stub`, `fallback_sqlite`, `fallback_direct`), enabling cold evaluation.

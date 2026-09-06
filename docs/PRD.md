# CONFORM — Product Requirements Document

**Version:** 1.0
**Date:** 2026-08-28
**Status:** Controlling specification. Where this document and `AGENTS.md` conflict, this wins.
**Target:** Agentic Cinema: The Blockbuster Hackathon — **ClickHouse partner track**
**Deadline:** Sep 9, 2026 @ 2:00 PM PT · **target submission Sep 8**

---

## 1. Summary

**CONFORM compiles generative media instead of regenerating it.**

An advertising studio runs a slate of campaigns. Each is produced by an AI pipeline
(brief → shot plan → keyframes → clips → copy → voiceover → music → package) and each master
fans out to ~40 territory variants. When an advertising **regulation changes**, current systems
cannot tell which assets depend on the changed rule, so they regenerate everything — at enormous
cost, since video generation dominates the bill.

CONFORM models the slate as a dependency graph, fingerprints every node from its exact inputs and
recipe, computes the precise **blast radius** of a change, quotes the **cost before any spend**,
waits for **human approval**, then rebuilds **only what is dirty** — reusing everything else
byte-for-byte. Every build event lands in **ClickHouse**, where an analyst agent answers questions
over the slate's history through the official **ClickHouse MCP server**.

### Non-technical framing

> Right now, changing one word in an AI-generated advert means paying to remake the whole thing.
> CONFORM works out what actually needs remaking — usually a small fraction — shows you the bill
> before you commit, and keeps a tamper-proof record of everything it produced.

---

## 2. Problem statement

| # | Problem | Consequence today |
|---|---|---|
| P1 | No dependency awareness in generative pipelines | One-line change regenerates the entire slate |
| P2 | Cost is discovered *after* generation | Budget overruns are found in the invoice, not the plan |
| P3 | Regulation changes propagate invisibly | Non-compliant assets stay live; discovery is manual |
| P4 | No provenance on delivered assets | Cannot prove a delivered file is the approved one |
| P5 | Build history is unqueryable | "What did that change cost us?" gets a shrug |
| P6 | Transient provider failures need babysitting | Engineers manually restart long generative builds |

---

## 3. Users

| Persona | Needs | Primary surface |
|---|---|---|
| **Production lead** | Know the blast radius and bill before approving spend | Graph canvas + change preview |
| **Compliance reviewer** | See exactly which assets a rule change affects, with evidence | Rule change view + findings |
| **Finance / ops** | Understand spend across the slate; find waste | Analytics + Ask-the-slate |
| **Delivery / QA** | Prove a delivered file is byte-identical to what was approved | Verify release |

All roles are **simulated and labelled as simulated**. No authentication is in scope.

---

## 4. Scope

### 4.1 In scope (must ship)

1. Deterministic DAG with JCS + SHA-256 content-addressed fingerprinting.
2. Territory fan-out: master campaign → N territory variants sharing upstream nodes.
3. Demo compliance rule engine; a **rule change** marks affected nodes dirty.
4. Blast-radius computation with cost and duration estimation, **before** any generation.
5. Explicit human approval gate. **Zero provider calls before approval.**
6. Incremental rebuild of the dirty subtree only, with byte-exact reuse of clean artifacts.
7. Vertex AI generation for every generative leaf; ffmpeg (no AI) for packaging.
8. ClickHouse event store: writes via driver, **reads via the official `mcp-clickhouse` server**.
9. Natural-language analyst agent over build history, showing the SQL it generated.
10. Retry taxonomy — transient / permanent / policy — with automatic retry and preserved
    `parent_run_id` lineage.
11. Release verification: re-download from GCS, re-hash, byte-exact verdict.
12. Immutable releases with diffs between them.
13. Web UI (six views, §7) deployed at a public hosted URL.
14. Audit log with trace IDs; truthful mode labelling throughout.

### 4.2 Out of scope (explicitly)

Authentication and real user accounts · real regulatory/legal compliance claims · photorealistic
or broadcast-grade output · non-Google AI providers · real-time collaborative editing ·
multi-tenancy beyond one demo tenant · a full NLE timeline editor · mobile apps.

### 4.3 Cut order (if time runs short)

Cut from the bottom. **Never cut anything in §4.1 items 1–8.**

1. Diff-between-releases view
2. Ask-the-slate free-form NL (keep 4 canned questions hitting MCP)
3. Analytics view beyond a single spend chart
4. Music node (`lyria-2`)
5. Voiceover node — fall back to silent packages

---

## 5. Functional requirements

### FR-1 Slate and graph
- **FR-1.1** Load a seed slate: 3 campaigns × 40 territories, ~180 nodes total, from
  `data/seed_slate.json`.
- **FR-1.2** Build a DAG of typed nodes: `source`, `shot_plan`, `keyframe`, `clip`, `copy`,
  `voiceover`, `music`, `package`.
- **FR-1.3** Territory variants share upstream nodes and diverge at the localisable nodes
  (`copy`, `voiceover`, `package`). This sharing is what makes reuse dramatic.
- **FR-1.4** Maintain a transitive closure table so blast radius is an indexed lookup.
- **FR-1.5** Reject cycles with an explicit typed error.

### FR-2 Fingerprinting
- **FR-2.1** Canonicalise node inputs and recipe with **JCS (RFC 8785)**.
- **FR-2.2** Fingerprint = `SHA-256(canonical(inputs ‖ recipe))`, lowercase hex.
- **FR-2.3** Fingerprints must be **stable across processes, key order, whitespace, and
  serialization round-trips**.
- **FR-2.4** A node's fingerprint incorporates its parents' fingerprints, so change propagates
  transitively by construction.

### FR-3 Rule engine and change trigger
- **FR-3.1** Load demo rules from `data/demo_rules.json`, each with a stable ID
  (e.g. `R-DISC-001`), a scope (node kinds, territories), and a deterministic predicate.
- **FR-3.2** A **rule change** (new/edited/removed rule) is a first-class change type alongside
  asset edits.
- **FR-3.3** Evaluating a changed rule marks matching nodes dirty and emits **findings** carrying
  evidence: node ID, territory, rule ID, and the specific reason.
- **FR-3.4** Rule evaluation is **100% deterministic**. No LLM involvement.
- **FR-3.5** All UI and API language says "demo compliance checks" / "project rules", never
  "regulatory compliance", and carries a not-professional-review disclaimer.

### FR-4 Blast radius and estimate
- **FR-4.1** Given a change, compute the exact dirty set via closure lookup.
- **FR-4.2** Produce an `Estimate`: nodes dirty, nodes reused, estimated USD, estimated seconds,
  per-model breakdown, and a `graph_hash` of the state it was computed against.
- **FR-4.3** Present reuse prominently — "rebuilds 23 of 180, reuses 157" is the headline.
- **FR-4.4** If estimated cost exceeds `BUILD_BUDGET_USD`, block and require explicit override.

### FR-5 Approval gate
- **FR-5.1** A change enters `AWAITING_APPROVAL` with its estimate attached.
- **FR-5.2** **No generative provider call may occur before approval.** Enforced in code and
  asserted in tests with a spy provider.
- **FR-5.3** Approval records actor (simulated, labelled), timestamp, and the `graph_hash`.
- **FR-5.4** If `graph_hash` no longer matches at build time, **refuse to build** and require
  re-estimation. Stale approvals must never spend money.

### FR-6 Build execution
- **FR-6.1** Execute dirty nodes only, in topological order, with bounded parallelism.
- **FR-6.2** A node whose fingerprint is unchanged is **never** regenerated — the existing
  artifact is reused by reference.
- **FR-6.3** `build()` is **idempotent**: re-running yields the same release and zero new
  provider calls.
- **FR-6.4** Classify every failure as `transient`, `permanent`, or `policy`. Retry transient
  automatically with backoff, on a fresh attempt row, preserving `parent_run_id` lineage.
- **FR-6.5** Provide a fault-injection switch to force a transient provider timeout — required
  for the demo video.
- **FR-6.6** Emit a `node_runs` row per attempt and a `provider_calls` row per Vertex call.

### FR-7 Artifacts and verification
- **FR-7.1** Store artifacts in GCS keyed by content hash.
- **FR-7.2** Record `uri`, `sha256`, `bytes`, `content_type` in the `artifacts` table.
- **FR-7.3** `verify_release(release_id)` re-downloads every artifact, re-hashes, and returns a
  per-artifact byte-exact verdict.
- **FR-7.4** Provide a tamper switch that corrupts one byte, so the demo can show verification
  failing red.

### FR-8 ClickHouse and the analyst agent
- **FR-8.1** Apply `schema.sql` idempotently at startup.
- **FR-8.2** **Writes** via `clickhouse-connect`, batched.
- **FR-8.3** **Reads** exclusively via the official **`mcp-clickhouse` MCP server**
  (`run_select_query`, `list_databases`, `list_tables`). Read-only; never enable MCP writes.
- **FR-8.4** The analyst agent turns a natural-language question into SQL, executes it through
  MCP, and explains the returned rows. **It must not invent numbers** — every figure it states
  must be traceable to a returned row.
- **FR-8.5** Display the generated SQL alongside the answer. Transparency is a scoring asset.
- **FR-8.6** Guard generated SQL: `SELECT` only, parameterised, enforced `LIMIT`.
- **FR-8.7** Seed synthetic historical builds so analytics are populated from day one. Seeded
  rows must be **labelled as seeded** in the data.

### FR-9 Releases
- **FR-9.1** A successful approved build produces an immutable `release_NNN`.
- **FR-9.2** Releases are never mutated; every build creates a new one.
- **FR-9.3** Provide a diff between two releases: nodes changed, added, removed, cost delta.

### FR-10 API
FastAPI, typed errors mapped to a consistent `ApiError` envelope:

```
GET  /api/system/status               # truthful mode reporting
GET  /api/campaigns                   # slate
GET  /api/campaigns/{id}/graph        # nodes + edges + fingerprints + state
POST /api/changes                     # submit rule change or asset edit
GET  /api/changes/{id}/estimate       # blast radius + cost (no spend)
POST /api/changes/{id}/approve        # gate
POST /api/changes/{id}/reject
POST /api/builds                      # execute approved change
GET  /api/builds/{id}                 # timeline, attempts, retries, lineage
GET  /api/releases/{id}/verify        # byte-exact verdict
GET  /api/releases/{a}/diff/{b}
POST /api/analytics/ask               # NL → SQL → MCP → answer + SQL shown
GET  /api/analytics/summary           # headline metrics from the MV
```

---

## 6. Data model (ClickHouse)

```sql
CREATE TABLE node_runs (
    tenant         LowCardinality(String),
    campaign_id    LowCardinality(String),
    territory      LowCardinality(String),
    build_id       UUID,
    run_id         UUID,
    parent_run_id  Nullable(UUID),          -- retry lineage
    node_id        String,
    node_kind      LowCardinality(String),
    fingerprint    FixedString(64),
    inputs_hash    FixedString(64),
    recipe_hash    FixedString(64),
    status         LowCardinality(String),  -- ok|failed|skipped|running
    cache_hit      UInt8,
    attempt        UInt8,
    error_class    LowCardinality(String),  -- none|transient|permanent|policy
    is_seeded      UInt8,                   -- truthful labelling of synthetic history
    started_at     DateTime64(3),
    ended_at       DateTime64(3),
    duration_ms    UInt32,
    cost_usd       Decimal(12, 6),
    bytes_out      UInt64
) ENGINE = MergeTree
ORDER BY (tenant, campaign_id, started_at, node_id);

CREATE TABLE provider_calls (
    run_id        UUID,
    build_id      UUID,
    model         LowCardinality(String),
    modality      LowCardinality(String),   -- video|image|text|audio|music
    region        LowCardinality(String),
    latency_ms    UInt32,
    input_tokens  UInt32,
    output_tokens UInt32,
    media_seconds Float32,
    cost_usd      Decimal(12, 6),
    http_status   UInt16,
    retryable     UInt8,
    is_seeded     UInt8,
    called_at     DateTime64(3)
) ENGINE = MergeTree
ORDER BY (called_at, model);

CREATE TABLE artifacts (
    fingerprint  FixedString(64),
    build_id     UUID,
    node_id      String,
    uri          String,
    sha256       FixedString(64),
    bytes        UInt64,
    content_type LowCardinality(String),
    verify_ok    Nullable(UInt8),
    verified_at  Nullable(DateTime64(3)),
    created_at   DateTime64(3)
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (fingerprint, node_id);

CREATE TABLE graph_closure (
    campaign_id LowCardinality(String),
    build_id    UUID,
    ancestor    String,
    descendant  String,
    depth       UInt8
) ENGINE = MergeTree
ORDER BY (campaign_id, build_id, ancestor, depth);

CREATE TABLE rule_findings (
    change_id   String,
    rule_id     LowCardinality(String),
    node_id     String,
    territory   LowCardinality(String),
    severity    LowCardinality(String),
    reason      String,
    detected_at DateTime64(3)
) ENGINE = MergeTree
ORDER BY (change_id, rule_id, node_id);

CREATE MATERIALIZED VIEW build_savings_mv
ENGINE = SummingMergeTree
ORDER BY (campaign_id, build_id) AS
SELECT campaign_id,
       build_id,
       countIf(cache_hit = 1)         AS nodes_reused,
       countIf(cache_hit = 0)         AS nodes_rebuilt,
       sumIf(cost_usd, cache_hit = 0) AS spend_usd,
       sumIf(cost_usd, cache_hit = 1) AS avoided_usd
FROM node_runs
GROUP BY campaign_id, build_id;
```

### Canned analyst questions (must work on stage)

```sql
-- "What does the new disclaimer rule affect?"
SELECT territory, count() AS assets FROM rule_findings
WHERE change_id = {c:String} GROUP BY territory ORDER BY assets DESC;

-- "What did that change cost us?"
SELECT nodes_rebuilt, nodes_reused, spend_usd, avoided_usd
FROM build_savings_mv WHERE build_id = {b:UUID};

-- "Which nodes are cache-hostile across the slate?"
SELECT node_id, count() AS runs, avg(cache_hit) AS hit_rate, sum(cost_usd) AS burn
FROM node_runs GROUP BY node_id HAVING runs > 5 ORDER BY burn DESC LIMIT 20;

-- "What's our cost per finished second of video?"
SELECT sum(cost_usd) / sum(media_seconds) FROM provider_calls WHERE modality = 'video';
```

---

## 7. UI requirements

Build in this order. Views 1–3 are mandatory; 4–6 are progressive enhancement.

| # | View | Must show | Priority |
|---|---|---|---|
| 1 | **Graph canvas** | 180 nodes, 40-way fan-out, colour-coded clean / dirty / reused / building / failed. Dirty subtree lights up **before** any spend. The single most important screen. | P0 |
| 2 | **Change preview + approve** | "Rebuilds 23 of 180 · reuses 157 · ~$X · ~Ys", per-model breakdown, findings with rule IDs and evidence, one Approve button, budget warning. | P0 |
| 3 | **Build timeline** | Per-node attempts, cache hits snapping in instantly, retry rows nested under parents, error classification badges. | P0 |
| 4 | **Analytics** | Spend by model, cache-hit-rate trend, cost per finished second, avoided spend. | P1 |
| 5 | **Ask the slate** | NL box, the answer, and **the generated SQL** side by side, labelled as executed via the ClickHouse MCP server. | P1 |
| 6 | **Verify release** | Per-artifact green/red, plus the tamper demo showing red. | P1 |

Global requirements: a persistent status bar showing live vs fallback mode per integration
(Vertex, ClickHouse/MCP, GCS), and a visible "demo checks, not legal review" disclaimer.

---

## 8. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Blast radius for 180 nodes computes in < 500 ms |
| NFR-2 | Analyst SQL round-trip through MCP returns in < 3 s |
| NFR-3 | Graph canvas renders 180 nodes at interactive frame rates |
| NFR-4 | Cold-clone setup works from the README with no undocumented steps |
| NFR-5 | App starts and is usable with **zero** env vars, in labelled fallback mode |
| NFR-6 | All money as `Decimal`; no float arithmetic on cost anywhere |
| NFR-7 | Total demo build stays within `BUILD_BUDGET_USD` (default `$5.00`) |
| NFR-8 | `ruff check .` clean; full test suite green before every push |

---

## 9. Delivery plan

### Day 0 — Aug 28 (do today; several items are externally time-boxed)

- [ ] **Google Cloud $100 credit form — closes Aug 31, 11:59 PM PST.** Highest urgency.
- [ ] Register on Devpost; select the **ClickHouse** track.
- [ ] GCP project; enable Vertex AI, Cloud Storage, Cloud Run. Pick one region.
- [ ] ClickHouse Cloud instance (free trial); note the region; test connectivity.
- [ ] New **public** GitHub repo + **Apache-2.0 LICENSE**; confirm GitHub's About panel shows it.
- [ ] **Verify current Vertex model IDs and regional availability.** Blocks §5 provider work.

### Day 1–2 — Aug 29–30 · Deterministic core
JCS canonicalisation, fingerprinting, DAG, closure, dirty resolution, rule engine, cost model.
Tests for fingerprint stability, blast radius (incl. diamond deps + 40-way fan-out), and the
`app/core/` import-boundary test. **No LLM, no providers, no network.**

### Day 3 — Aug 31 · ClickHouse
Schema, writer, MV, `mcp-clickhouse` read client, seeded synthetic history (labelled).
Round-trip test writing via driver and reading via MCP.

### Day 4–5 — Sep 1–2 · Vertex AI + artifacts
Provider layer, per-call cost accounting, GCS content-addressed store, retry taxonomy with
fault injection, verification. Providers stubbed in the default test suite.

### Day 6 — Sep 3 · Agent + API
ADK coordinator, state machine, typed tools, analyst agent with SQL guarding, full API, audit log.

### Day 7–9 — Sep 4–6 · Frontend
Views 1–3 first and complete. Then 4–6. **Checkpoint Sep 5: if views 1–3 are not done, cut §4.3.**

### Day 10 — Sep 7 · Deploy + docs
Cloud Run deploy, public URL, cold-clone rehearsal, README, ARCHITECTURE.md, end-to-end run-through.

### Day 11 — Sep 8 · Record and submit
Record the video, write the Devpost submission, run the §11 checklist, **submit**.

### Day 12 — Sep 9 · Buffer only. Do not plan work here.

---

## 10. Demo video (≤ 3:00)

Judges asked explicitly for the product **functioning**, not a cinematic trailer.

| Time | Beat |
|---|---|
| 0:00–0:20 | The slate: 3 campaigns, 40 territories, 180 assets. A new EU disclaimer rule lands. Naive pipeline regenerates all 180 — show that bill. |
| 0:20–0:50 | Load the rule change. **23 of 180 light up on the graph, before any spend.** Findings list rule IDs and territories. "Rebuilds 23 · reuses 157 · $X." |
| 0:50–1:05 | Approve. Emphasise: nothing generated until this click. |
| 1:05–1:40 | Build runs. Cached nodes snap in instantly; only dirty nodes call Vertex. Live counter of provider calls avoided. |
| 1:40–2:05 | Inject a provider timeout. Classified **transient**, auto-retried on a fresh attempt, lineage preserved, build completes with no human intervention. |
| 2:05–2:35 | Ask the slate a question. Show the generated SQL executing through the **ClickHouse MCP server**, plus the spend chart. |
| 2:35–3:00 | Verify the release — all green. Flip one byte, verification fails red. Close on the architecture diagram and the LLM/deterministic boundary. |

---

## 11. Submission checklist

- [ ] New project, new repo — no reuse of any prior codebase
- [ ] **Zero non-Google AI dependencies** — grep the lockfile to confirm
- [ ] `google-genai` and/or `google-adk` imported and called at runtime
- [ ] `mcp-clickhouse` connection present and exercised in code
- [ ] Public repo; Apache-2.0 LICENSE visible in GitHub's About panel
- [ ] Live hosted URL, reachable cold by a judge
- [ ] Video ≤ 3:00, public, English or subtitled, shows real functionality
- [ ] ClickHouse track selected on the submission form
- [ ] README works from a cold clone
- [ ] Text description: features, tech, data sources, findings and learnings
- [ ] Submitted **Sep 8**, not Sep 9

---

## 12. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Veo burns the $100 credit | High | `veo-3.1-fast`, 4–8 s clips, small slate, `BUILD_BUDGET_USD` cap, always demo against a warm cache — the cache **is** the product |
| Vertex model IDs shifted in 2026 | High | Verify Day 0; keep IDs in config, never in call sites |
| Frontend overruns the schedule | High | Views 1–3 only by Sep 5 checkpoint; §4.3 cut order |
| Judge challenges determinism | Medium | Cache determinism, stated plainly (AGENTS.md §2). Never claim model determinism |
| ClickHouse Cloud latency on stage | Medium | Nearest region, pre-warm, MV keeps headline queries cheap, cache canned answers |
| Analyst agent hallucinates a number | Medium | Every figure must trace to a returned row; show the SQL; test for it |
| "Isn't this a prior project?" | Medium | New repo, new product, no code reuse. Be upfront if asked |
| Graph canvas perf at 180 nodes | Low | Canvas not DOM; precomputed layout |

---

## 13. Success criteria

**Minimum viable submission** — all of: blast radius before spend, approval gate with zero
pre-approval provider calls, incremental rebuild with demonstrated reuse, ClickHouse reads through
the MCP server, release verification, hosted URL, video, compliant repo.

**Competitive submission** — the above plus: the 40-way fan-out visualised, automatic transient
retry with preserved lineage, the analyst agent with visible SQL, a real headline reuse number
from a live run, and a README that states the LLM/deterministic boundary explicitly.

**The number to land on the video:** *"Rebuilds 23 of 180. Reuses 157. Provider calls: N → M."*
Whatever the true figures are on the night — **report them honestly.**

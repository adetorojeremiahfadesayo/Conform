# AGENTS.md — CONFORM

Guidance for AI coding agents working in this repository. Assumes **no prior knowledge** of the
project. Read this file completely before writing any code, then read [docs/PRD.md](./docs/PRD.md)
for product requirements.

---

## 1. What this project is

**CONFORM** is a **compiler for generative media pipelines**, built for the
**Agentic Cinema: The Blockbuster Hackathon** (Google Cloud + partners, on Devpost),
submitted to the **ClickHouse partner track**.

### The problem in one paragraph

An advertising studio runs a slate of campaigns. Each campaign is produced by an AI pipeline:
brief → shot plan → keyframes → video clips → on-screen copy → voiceover → music → final package.
Each master campaign then fans out to ~40 territory variants. When an advertising **regulation
changes** — say, a new rule requires a longer allergy disclaimer in EU territories — current
systems have no idea which assets actually depend on that rule, so they **regenerate everything**.
That is enormously expensive, because video generation is the single most costly step.

### What CONFORM does

CONFORM models the whole slate as a **dependency graph (DAG)** and fingerprints every node from
its exact inputs and recipe using **JCS canonicalisation + SHA-256**. When a rule changes, it:

1. Computes the exact **blast radius** — which nodes across which territories are now dirty.
2. Estimates **cost and time** for the rebuild, and shows what will be **reused**.
3. **Waits for explicit human approval.** Nothing generates before a human approves the spend.
4. Rebuilds **only the dirty subtree**, reusing every clean artifact byte-for-byte.
5. Records every event to **ClickHouse**, so an agent can answer questions over slate history.
6. Produces **independently verifiable** releases — re-download, re-hash, byte-exact verdict.

### The demo narrative (build toward this)

> A new EU advertising regulation lands. CONFORM marks **23 of 180** assets across 3 campaigns
> and 40 territories as non-compliant, shows the blast radius lit up on the graph, quotes the
> rebuild bill, waits for approval, rebuilds only those 23, and proves the output is untampered.

---

## 2. The core architectural law: the LLM / deterministic boundary

**This is the most important rule in the repository. Violating it is a correctness bug.**

- **Gemini may only:** interpret unstructured text into typed contracts, and *explain* results
  it was handed. That is all.
- **Everything else is pure deterministic Python or SQL:** fingerprints, graph traversal, blast
  radius, dirty-set resolution, cost arithmetic, rule evaluation, retry classification,
  verification verdicts, and diffing.
- An LLM must **never** produce a number, a hash, a cost, a dirty-set, or a pass/fail verdict.
- Unvalidated LLM output must **never** reach the build engine. Validate against the pydantic
  contract, retry once, then fail explicitly.
- A tool failure surfaces as an **explicit typed error**. Never invent a success. Never silently
  degrade.
- Fallback / mock / offline paths must be **labelled as such in the data itself**
  (e.g. `interpretation_mode="fallback_deterministic"`), never disguised as live integrations.

### The determinism honesty rule

Generative models are **not deterministic**. CONFORM's determinism is **cache determinism**:

> The fingerprint covers **inputs + recipe**. Artifacts are content-addressed and immutable once
> produced. Identical inputs + identical recipe ⇒ **the existing bytes are reused, never
> regenerated.**

Never claim model determinism anywhere — code, UI copy, README, or video. Judges will probe this.
State the cache-determinism framing explicitly in the README.

### The compliance-language rule

The rule engine implements **demo project rules only**. Never claim regulatory, legal, or
advertising-standards compliance anywhere in code, UI, or docs. Use "demo compliance checks" or
"project rules", and carry a visible disclaimer that this is not professional legal review.

---

## 3. Non-negotiable hackathon constraints

These are **disqualification risks**, not preferences. Re-read before every commit.

| Constraint | Detail |
|---|---|
| **Google-only AI** | Only Google Cloud AI tools plus ClickHouse's built-in AI features. **No OpenAI, Anthropic, AWS, Microsoft, fal, Replicate, ElevenLabs, Runway, or any other AI/agent framework or API.** Non-AI third-party services (hosting, databases, web frameworks) are fine. Grep the lockfile before submitting. |
| **Accepted Google SDKs** | `google-adk`, `google-genai`, `google-generativeai`, `google-cloud-aiplatform`. Must be **imported and actually called at runtime** — not merely named in the README. |
| **ClickHouse track requirement** | Must actively use ClickHouse at runtime **via the official `mcp-clickhouse` MCP server**, against ClickHouse Cloud or self-hosted. A README mention does not satisfy this. |
| **New project only** | Created during the contest period; must not be a modification or extension of any existing work. **Do not import, copy, or reference code from any prior project**, including TakeGraph or BIM-Agent-Demo. Patterns and lessons may be re-applied; source code may not be reused. |
| **Open source** | Public repo with an **Apache-2.0 LICENSE detectable in the GitHub About panel**. |
| **Platform** | Must run on web. Needs a **live hosted URL** a judge can open cold. |
| **Video** | ≤ 3:00, public on YouTube/Vimeo, English or subtitled, showing the product **actually functioning** (explicitly not a cinematic trailer). |
| **Deadline** | **Sep 9, 2026 @ 2:00 PM PT.** Target submission **Sep 8**. |

---

## 4. Repository layout

```
CONFORM/
├── AGENTS.md                    # this file
├── AGENTS_UI.md                 # frontend & UX architecture, narrative model, and state transitions
├── LICENSE                      # Apache-2.0 — must be detectable by GitHub
├── README.md                    # cold-clone run instructions + architecture + boundary statement
├── pyproject.toml               # pytest + ruff config
├── requirements.txt             # pinned deps
├── Dockerfile                   # Cloud Run image (uvicorn on $PORT)
├── .env.example                 # variable NAMES only, never values
├── app/
│   ├── config.py                # env-driven Config; never logs secrets
│   ├── domain/
│   │   └── schemas.py           # ALL pydantic contracts, single source of truth
│   ├── core/                    # DETERMINISTIC CORE — no LLM imports allowed here
│   │   ├── canonical.py         # JCS (RFC 8785) canonicalisation
│   │   ├── fingerprint.py       # SHA-256 over canonical(inputs ‖ recipe)
│   │   ├── graph.py             # DAG construction, topological order
│   │   ├── closure.py           # transitive closure maintenance
│   │   ├── dirty.py             # blast radius / dirty-subtree resolution
│   │   ├── rules.py             # compliance rule engine (demo rules)
│   │   ├── cost.py              # cost + duration estimation
│   │   ├── retry.py             # transient|permanent|policy error taxonomy
│   │   └── verify.py            # re-download, re-hash, byte-exact verdict
│   ├── providers/               # Vertex AI leaf nodes (the ONLY generative code)
│   │   ├── base.py              # Provider protocol; every call emits a ProviderCall
│   │   ├── text.py              # gemini-3.1-flash / gemini-3-pro
│   │   ├── image.py             # imagen-4 / gemini-3-pro-image
│   │   ├── video.py             # veo-3.1-fast / veo-3.1-lite
│   │   ├── audio.py             # chirp-3-hd / Gemini TTS
│   │   ├── music.py             # lyria-2
│   │   └── package.py           # ffmpeg mux/encode — NO AI, fully deterministic
│   ├── store/
│   │   ├── clickhouse_writer.py # WRITE path: clickhouse-connect, batched inserts
│   │   ├── mcp_client.py        # READ path: official mcp-clickhouse MCP server
│   │   ├── schema.sql           # DDL, applied idempotently at startup
│   │   └── artifacts.py         # GCS content-addressed object store
│   ├── agents/
│   │   ├── coordinator.py       # explicit workflow state machine + typed tools
│   │   ├── interpreter.py       # brief/rule text → typed contract (LLM or fallback)
│   │   ├── analyst.py           # NL question → SQL → mcp-clickhouse → explanation
│   │   └── prompts.py
│   ├── observability/
│   │   ├── audit.py             # append-only audit log, trace IDs
│   │   └── logging.py
│   └── api/
│       ├── main.py              # create_app factory + typed ApiError mapping
│       ├── deps.py
│       └── routers/             # campaigns, changes, builds, analytics, verify, system
├── web/                         # Vite + React + TypeScript frontend
│   ├── src/
│   │   ├── api/                 # generated/typed client
│   │   ├── views/               # graph, preview, timeline, analytics, ask, verify
│   │   └── components/
│   └── package.json
├── data/
│   ├── demo_rules.json          # demo compliance rule set
│   └── seed_slate.json          # 3 campaigns × 40 territories fixture
├── tests/
│   ├── fixtures/
│   └── test_*.py
└── docs/
    ├── PRD.md                   # product requirements — READ THIS SECOND
    ├── ARCHITECTURE.md
    ├── WORKLOG.md               # stage-by-stage record — KEEP UPDATED
    ├── DECISIONS.md             # numbered decisions D1, D2, … — record tradeoffs
    └── DEVIATIONS.md            # departures from the PRD: reason, consequence, follow-up
```

---

## 5. Technology stack

- **Backend:** Python ≥ 3.12, FastAPI + uvicorn, pydantic v2 for every cross-boundary payload.
- **Generation:** `google-genai` against Vertex AI. `google-adk` for the agent layer.
- **Analytics:** ClickHouse Cloud. Writes via `clickhouse-connect`; reads via `mcp-clickhouse`.
- **Artifacts:** Google Cloud Storage, content-addressed by SHA-256.
- **Frontend:** Vite + React + TypeScript. Graph rendering via a canvas/SVG DAG layout.
- **Deploy:** Cloud Run (backend + frontend), one region, nearest to the demo machine.

### Model IDs

**Verify these on day 1 before building around them** — the Vertex media endpoints moved during
2026. Keep all model IDs in config, never hardcoded in call sites.

| Node | Model |
|---|---|
| `source`, `shot_plan` | `gemini-3-pro` (schema-constrained structured output) |
| `copy` | `gemini-3.1-flash` |
| `keyframe` | `imagen-4` or `gemini-3-pro-image` |
| `clip` | `veo-3.1-fast`, fall back `veo-3.1-lite` |
| `voiceover` | `chirp-3-hd` or Gemini TTS |
| `music` | `lyria-2` |
| `package` | **ffmpeg — no AI** |

---

## 6. Commands

All commands run from `CONFORM/`.

```bash
# setup
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# tests
.venv/Scripts/python.exe -m pytest

# lint
.venv/Scripts/python.exe -m ruff check .

# serve API
.venv/Scripts/python.exe -m uvicorn app.api.main:app --port 8080

# frontend
cd web && npm install && npm run dev
```

Environment variables (see `.env.example` — names only, never values):
`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`, `VERTEX_*_MODEL`, `CLICKHOUSE_HOST`,
`CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DATABASE`, `ARTIFACT_BUCKET`,
`PORT`, `WEB_ORIGIN`, `BUILD_BUDGET_USD`.

The app must start and run in a clearly-labelled offline/fallback mode with none of these set.

---

## 7. Code style and conventions

- Python 3.12. `from __future__ import annotations` in every module. Full type hints.
- Every module opens with a short docstring stating its responsibility **and its side of the
  deterministic/LLM boundary**.
- ruff: line-length 110, rules `E, F, I, W`, target `py312`.
- **`app/core/` must not import any LLM or provider module.** Enforce this with a test that
  walks the import graph. It is the single clearest guarantee of the boundary.
- **Money:** `Decimal`, never `float`. **Hashes:** lowercase hex, 64 chars.
  **Times:** UTC, `DateTime64(3)` in ClickHouse.
- **IDs:** content-derived and stable for nodes and artifacts; `campaign_…`, `build_…`,
  `change_…`, and sequential `release_001` for releases.
- All cross-module payloads are pydantic models. The coordinator calls a fixed set of typed tools.
- **No silent scope.** Anything in a brief or rule change that cannot be handled goes into
  `deferred_requirements` and is surfaced in the UI. Never dropped.

---

## 8. Workflow state machine (`app/agents/coordinator.py`)

```
slate_loaded → change_received → change_interpreted → rules_evaluated
  → blast_radius_computed → estimate_ready → AWAITING_APPROVAL
  → approved | rejected → build_running → build_complete
  → release_verified → artifacts_ready
```

Invariants that must hold and must be tested:

1. A change is `AWAITING_APPROVAL` before `approve()` may be called.
2. `build()` is **idempotent** — re-running produces the same release, not a new one.
3. `build()` **refuses** if the approved estimate's graph hash no longer matches current state.
4. **No generative provider call may occur before approval.** Assert this in tests.
5. A node whose fingerprint is unchanged is **never** regenerated.
6. Releases are immutable; a new build creates a new release, never mutates one.
7. Budget cap: if estimated cost exceeds `BUILD_BUDGET_USD`, block and require override.

---

## 9. Testing

- pytest; `testpaths = ["tests"]`. `httpx` TestClient for API tests.
- Required coverage areas:
  - **Boundary test** — `app/core/` imports nothing from `app/providers/` or `app/agents/`.
  - **Fingerprint stability** — same inputs ⇒ same hash across processes and serialization
    round-trips; key order and whitespace must not matter (this is what JCS buys you).
  - **Blast radius correctness** — hand-built graphs with known expected dirty sets, including
    diamond dependencies and the 40-way territory fan-out.
  - **No-spend-before-approval** — provider layer stubbed with a spy that fails the test if
    called pre-approval.
  - **Idempotency** — build twice, assert one release and zero new provider calls.
  - **Retry taxonomy** — injected timeout classifies transient, retries, preserves
    `parent_run_id` lineage, completes without human input.
  - **Verification** — flip one byte in a stored artifact, assert verification fails.
  - **ClickHouse round-trip** — write events, read them back **through the MCP client**.
  - **API flow** — full happy path plus negative paths.
- Providers must be stubbed by default in tests. Live Vertex calls run only behind an explicit
  opt-in marker, never in the default suite.

---

## 10. Security

- **Never commit secrets.** `.env`, `*.key`, `service-account*.json` are gitignored.
  `.env.example` holds names and explanations only.
- `Config.public_status()` returns modes only — never values. Never log a credential.
- ClickHouse credentials and Google credentials stay server-side. Nothing secret reaches the
  browser bundle or any log line.
- The MCP read path must be **read-only**. Do not enable MCP write access.
- LLM-generated SQL is untrusted: allowlist to `SELECT`, parameterise, cap `LIMIT`, and run it
  through the read-only MCP path only.
- No authentication is implemented — deliberately out of demo scope. Actor roles are simulated
  and must be **labelled as simulated** in the audit log and UI.

---

## 11. Working agreements

- [docs/PRD.md](./docs/PRD.md) is the controlling specification. Where this file and the PRD
  conflict, **the PRD wins** — and record the conflict in `docs/DECISIONS.md`.
- Record every departure from the PRD in `docs/DEVIATIONS.md` with reason, consequence, and
  follow-up. Record stage progress in `docs/WORKLOG.md`. Record tradeoffs in `docs/DECISIONS.md`.
- **Isolation:** `../BIM-Agent-Demo/`, `../kimi bim fronmt1/`, and any other project on this
  machine are **strictly out of scope**. Do not read from, copy from, or write to them.
  Write only inside `CONFORM/`.
- **Cost discipline:** Vertex video generation burns credit fast. Default to `veo-3.1-fast`,
  4–8 second clips, and a small slate. Always run against the cache. Enforce `BUILD_BUDGET_USD`.
- **Scope discipline.** Never cut these: content-addressed fingerprinting, blast-radius preview
  before spend, the human approval gate, incremental rebuild with proven reuse, ClickHouse
  history via MCP, retry taxonomy, release verification, truthful labelling.
  Explicitly out of scope: authentication, photorealism, real regulatory compliance,
  multi-tenancy beyond a demo tenant, and any non-Google AI provider.

---

## 12. Current state

**Nothing is built yet.** This repository currently contains only `AGENTS.md` and `docs/PRD.md`.

Start at PRD §9 (Delivery plan), Day 1. Before writing code, complete the Day 0 checklist in
PRD §9 — several items are externally time-boxed and block later work.

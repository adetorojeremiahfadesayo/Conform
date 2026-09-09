# CONFORM

[Open the hosted demo](https://conform-tiwoc77ijq-ew.a.run.app)

The hosted URL runs in **Judge Mode**: the prepared German/French disclaimer scenario, its live ADK
interpretation, and its real Google-generated media are cached in a private GCS bucket. The public API
accepts no custom prompts or SQL, never calls Vertex on a cache miss, and exposes no credentials. Approval,
incremental reuse, ClickHouse MCP readback, and byte verification remain demonstrable.

For local API plus authenticated official ClickHouse MCP, run `python -m app.serve` after installing
`requirements.txt`. Cloud Run uses the same entry point; no separate MCP token setup is needed.

**Compile generative media. Don't regenerate it.**

CONFORM is a build compiler for AI-generated advertising campaigns. It models an entire
campaign slate as a dependency graph, fingerprints every node from its exact inputs and
recipe (JCS canonicalisation + SHA-256), and when something changes — an edit, or a new
compliance rule — it rebuilds **only what actually depends on the change**, reusing
everything else byte-for-byte. It shows you the blast radius and the bill **before**
anything is generated, waits for explicit human approval, and keeps every build event in
ClickHouse so an agent can answer questions over the whole slate's history.

Built for the [Agentic Cinema: The Blockbuster Hackathon](https://agentic-cinema.devpost.com/)
— ClickHouse partner track.

## The one-line pitch

> Changing one word in an AI-generated advert shouldn't mean paying to remake the whole
> thing. CONFORM works out what actually needs remaking, shows you the cost before you
> commit, and keeps a tamper-proof record of everything it produced.

## Architecture and the LLM / deterministic boundary

```
brief / rule change ──▶ interpreter (Gemini, or labelled deterministic fallback)
                              │ typed ChangeIntent only
                              ▼
                    DETERMINISTIC CORE (pure Python — no LLM imports, enforced by test)
                    JCS canonicalise · SHA-256 fingerprints · DAG · transitive closure
                    blast radius · cost model · rule engine · retry taxonomy · verify
                              │ generate (dirty leaves only)        │ events
                              ▼                                    ▼
                    Vertex AI (google-genai)               ClickHouse
                    Veo / Imagen / Gemini /                write: clickhouse-connect
                    Chirp / Lyria · ffmpeg package         read:  official mcp-clickhouse MCP server
```

**The law:** the LLM interprets and explains. It never computes a fingerprint, a blast
radius, a cost, or a pass/fail verdict. Those are pure Python + SQL.

**On determinism:** generative models are not deterministic. CONFORM's determinism is
*cache determinism* — fingerprints cover inputs + recipe, artifacts are content-addressed
and immutable, so identical inputs reuse identical bytes instead of regenerating.

**On compliance:** the rule engine implements *demo project rules only*. Nothing here is
legal, regulatory, or advertising-standards review.

## Quickstart (cold clone, zero credentials)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows; adjust for your shell
.venv/Scripts/python -m uvicorn app.api.main:app --port 8080
```

With no environment variables set, the app runs in **clearly labelled fallback modes**
(stub generator, SQLite event store, local artifacts, direct SQL reads) — check
`GET /api/system/status` to see exactly which mode each integration is in.

## Running with mcp-clickhouse (live MCP reads)

By default the app reads ClickHouse directly. To switch the analytics read
path to the **official mcp-clickhouse MCP server** (required for the
ClickHouse partner track):

1. **Install and start the official Python MCP server in HTTP mode**:

   ```bash
   python -m pip install mcp-clickhouse
   CLICKHOUSE_MCP_SERVER_TRANSPORT=http \
   CLICKHOUSE_MCP_AUTH_TOKEN="replace-with-a-generated-secret" \
   python -m mcp_clickhouse.main
   ```

   HTTP transport listens on port 8000 by default and requires authentication.
   Keep `CLICKHOUSE_ALLOW_WRITE_ACCESS` disabled so the MCP path remains read-only.

2. **Set the environment variable** (in `.env` or your shell):

   ```bash
   CLICKHOUSE_MCP_URL=http://localhost:8000
   CLICKHOUSE_MCP_AUTH_TOKEN=replace-with-the-same-generated-secret
   ```

3. **Verify the connection** — start the app and hit the status endpoint:

   ```bash
   curl http://localhost:8080/api/system/status
   ```

   The status is `configured_unverified` until a query succeeds. Exercise
   `POST /api/analytics/ask`, then confirm the reader changes to `live_mcp`.
   `error` means the configured server or authentication could not complete
   the MCP query.

## The demo flow

```bash
# A new EU disclaimer rule lands
curl -X POST localhost:8080/api/changes \
  -d '{"text": "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40"}'

# Blast radius BEFORE any spend: dirty set, reuse count, estimated cost
curl -X POST localhost:8080/api/changes/{change_id}/estimate

# Build is refused here — the approval gate
curl -X POST localhost:8080/api/changes/{change_id}/build        # → 409 NOT_APPROVED

# Approve, then build — only dirty nodes call a provider
curl -X POST localhost:8080/api/changes/{change_id}/approve -d '{"actor": "producer (simulated)"}'
curl -X POST localhost:8080/api/changes/{change_id}/build

# Prove the release: re-download, re-hash, byte-exact
curl localhost:8080/api/releases/release_001/verify

# Ask the slate (Natural language analyst or guarded SELECT via ClickHouse MCP)
curl -X POST localhost:8080/api/analytics/ask \
  -d '{"query": "What is our spend across models?"}'

# Corrupt 1 byte in storage to demonstrate tamper detection
curl -X POST localhost:8080/api/system/tamper \
  -d '{"release_id": "release_001"}'
```

## Going live

Set the variables in `.env.example` (copy to `.env`): a GCP project enables Vertex AI
generation and GCS artifacts; ClickHouse credentials enable the Cloud writer;
`CLICKHOUSE_MCP_URL` switches analytics reads to the official `mcp-clickhouse` MCP server.
Every mode change is visible in `/api/system/status` — nothing is silently live or
silently fake.

## Tests

```bash
.venv/Scripts/python -m pytest      # 88 tests
.venv/Scripts/python -m ruff check .
```

The suite enforces the architecture, not just the behaviour: an import-boundary test
guarantees `app/core/` never imports a provider or LLM module, and a spy provider proves
no generation can happen before approval.

## Layout

See [AGENTS.md](./AGENTS.md) for the full repository guide and working agreements, and
[docs/PRD.md](./docs/PRD.md) for the product requirements.

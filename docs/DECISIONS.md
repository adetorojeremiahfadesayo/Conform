# DECISIONS — CONFORM

Numbered decisions. Read before changing behaviour.

- **D1 — Cache determinism, not model determinism.** Fingerprints cover inputs + recipe;
  artifacts are content-addressed and immutable once produced. Identical inputs reuse
  identical bytes rather than regenerating. Never claim generative-model determinism.
- **D2 — Compliance trigger is a first-class change type.** Rule changes (new/edit/remove)
  go through the same Change/Estimate/Approval path as asset edits. The rule engine is
  100% deterministic; findings carry rule_id + node_id + territory + reason as evidence.
- **D3 — Territory variants share upstream nodes.** Each campaign has one master chain
  (source->shot_plan->keyframe->clip); territories diverge only at copy/package leaves.
  This is what makes reuse dramatic and the fan-out demo legible.
- **D4 — Write path is the driver; read path is the MCP server.** mcp-clickhouse is
  read-only by default, so builds write via clickhouse-connect and the analyst agent reads
  exclusively through the MCP server — making the track-required integration load-bearing.
- **D5 — Fallback modes are first-class and labelled.** Stub generator, SQLite events,
  local artifacts, direct SQL reads: all selectable by env absence, all reported
  truthfully by /api/system/status. The app must be fully demoable with zero credentials.
- **D6 — Stale approvals refuse to spend.** Approvals pin graph_hash; run_build raises
  STALE_APPROVAL (zero provider calls) if the graph changed since approval.
- **D7 — Money is Decimal, hashes are 64-char lowercase hex, times are UTC.** No floats
  touch cost anywhere.
- **D8 — SQL shown is SQL executed.** The analyst endpoint applies the SELECT-only guard
  before execution and returns the guarded statement, so the UI can display exactly what
  ran through the MCP server.
- **D9 — Demo preset cache contains live interpretations only.** A successful Google ADK interpretation may
  be stored and replayed, but each replay creates a fresh change and deterministically recomputes its estimate.
  Fallback interpretations are excluded, and the approval gate is never cached or bypassed.
- **D10 — Generation caches are provenance-separated.** Vertex and fallback artifacts use separate object-store
  prefixes. Stub bytes can therefore never count as a cache hit for a live Vertex build.
- **D11 — Telemetry is explicit but not transactional with release creation.** If artifact generation and release
  creation succeed but ClickHouse reporting fails, the release remains successful and the typed result records
  `telemetry_status=failed`; a reporting outage must not manufacture a failed build or discard immutable output.
- **D12 — Changes compile against an isolated target graph.** The approval pins the base graph. After checking
  for stale approval, the build applies the validated contract and computes target fingerprints without
  mutating the baseline shared by independent visitors.
- **D13 — Tamper demonstrations use an in-memory overlay.** Verification for the selected release reads the
  altered bytes against the original expected hash; canonical GCS media is never mutated or written by a
  public request.
- **D14 — MCP runs as an authenticated loopback sidecar.** Startup generates a shared process-local token for
  API and official MCP server. The MCP listener remains read-only and is not publicly exposed.
- **D15 — Public Judge Mode is cached-only and least-privilege.** The public Cloud Run URL permits the prepared
  EU scenario and six fixed analytics questions only. It rejects custom changes, direct SQL, operational
  switches, live-ADK cache misses, and uncached builds. Its `conform-judge` identity has bucket object-viewer
  access only and no Vertex role; all credentials remain server-side.

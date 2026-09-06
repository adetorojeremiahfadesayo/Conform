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

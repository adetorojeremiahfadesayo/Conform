// API types mirroring app/domain/schemas.py. Money arrives as string (Decimal).

export interface SystemStatus {
  vertex: string;
  clickhouse_write: string;
  clickhouse_read_mcp: string;
  artifact_store: string;
  budget_usd: string;
  writer: string;
  reader: string;
  nodes: number;
  fault_injection?: string;
  judge_mode?: string;
}

export interface GraphNode {
  node_id: string;
  campaign_id: string;
  territory: string;
  kind: string;
  fingerprint: string;
  state: "clean" | "dirty";
  parents: string[];
}

export interface GraphView {
  nodes: GraphNode[];
  graph_hash: string;
}

export interface Finding {
  rule_id: string;
  node_id: string;
  territory: string;
  severity: string;
  reason: string;
}

export interface ModelBreakdown {
  model: string;
  modality: string;
  node_count: number;
  cost_usd: string;
}

export interface DirtyNode {
  node_id: string;
  depth: number;
  reason: "NODE_SPEC_CHANGED" | "RULE_SCOPE_HIT" | "UPSTREAM_FINGERPRINT_CHANGED";
}

export interface Estimate {
  change_id: string;
  dirty_node_ids: string[];
  dirty_nodes: DirtyNode[];
  reused_node_ids: string[];
  estimated_cost_usd: string;
  estimated_seconds: number;
  per_model: ModelBreakdown[];
  findings: Finding[];
  graph_hash: string;
  budget_exceeded: boolean;
}

export interface Change {
  change_id: string;
  kind: string;
  status: string;
  intent: { interpretation_mode: string; deferred_requirements: string[] };
}

export interface NodeRun {
  run_id: string;
  parent_run_id: string | null;
  node_id: string;
  node_kind: string;
  status: "ok" | "failed" | "skipped" | "running";
  cache_hit: boolean;
  attempt: number;
  error_class: string;
  cost_usd: string;
}

export interface ProviderCall {
  run_id: string;
  model: string;
  modality: string;
  cost_usd: string;
  http_status: number;
  retryable: boolean;
}

export interface BuildResult {
  build_id: string;
  change_id: string;
  release: { release_id: string; artifacts: { node_id: string; sha256: string; uri: string }[] } | null;
  runs: NodeRun[];
  provider_calls: ProviderCall[];
  nodes_rebuilt: number;
  nodes_reused: number;
  total_cost_usd: string;
  retries: number;
  telemetry_status?: "recorded" | "failed";
  telemetry_error?: string | null;
}

export interface VerificationReport {
  release_id: string;
  ok: boolean;
  per_artifact: { node_id: string; uri: string; ok: boolean }[];
}

export interface AskResult {
  query?: string;
  sql: string;
  rows: Record<string, unknown>[];
  answer?: string;
  reader_mode: string;
  interpretation_mode?: string;
}

export interface AnalyticsSummary {
  nodes_rebuilt: number;
  nodes_reused: number;
  total_spend_usd: string;
  avoided_spend_usd: string;
  cache_hit_rate: number;
  spend_by_model: Record<string, unknown>[];
  spend_by_campaign: Record<string, unknown>[];
}

export interface TamperResponse {
  release_id: string;
  node_id: string;
  uri: string;
  tampered_byte: number;
  message: string;
}

export interface ReleaseDiff {
  release_a: string;
  release_b: string;
  nodes_added: string[];
  nodes_removed: string[];
  nodes_changed: string[];
  cost_delta_usd: string;
}

export interface AdkExecutionResult {
  goal: string;
  steps: Array<{ tool: string; [key: string]: unknown }>;
  tools_called: string[];
  final_answer: string;
  mode: string;
  change_id?: string;
  release_id?: string;
}

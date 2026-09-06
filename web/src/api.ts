import type {
  AdkExecutionResult,
  AnalyticsSummary,
  AskResult,
  BuildResult,
  Change,
  Estimate,
  GraphView,
  ReleaseDiff,
  SystemStatus,
  TamperResponse,
  VerificationReport,
} from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const text = await resp.text();
  let body: Record<string, unknown>;
  try {
    body = JSON.parse(text);
  } catch {
    throw new ApiError(resp.status, "UNPARSEABLE_RESPONSE", `${resp.status} ${text.slice(0, 120)}`);
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, String(body.code ?? "ERROR"), String(body.message ?? "request failed"));
  }
  return body as T;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export const api = {
  status: () => req<SystemStatus>("/api/system/status"),
  campaigns: () => req<Array<{ campaign_id: string; name: string; brief?: string }>>("/api/campaigns"),
  presets: () => req<Array<{ preset_id: string; title: string; campaign_id: string; category: string; description: string }>>("/api/presets"),
  submitPreset: (presetId: string) =>
    req<Change>(`/api/presets/${presetId}/changes`, { method: "POST" }),
  getChange: (changeId: string) => req<Change>(`/api/changes/${changeId}`),
  graph: (changeId?: string) =>
    req<GraphView>(`/api/graph${changeId ? `?change_id=${changeId}` : ""}`),
  submitChange: (text: string) =>
    req<Change>("/api/changes", { method: "POST", body: JSON.stringify({ text }) }),
  estimate: (changeId: string) =>
    req<Estimate>(`/api/changes/${changeId}/estimate`, { method: "POST" }),
  approve: (changeId: string, actor: string) =>
    req<{ approval_id: string }>(`/api/changes/${changeId}/approve`, {
      method: "POST",
      body: JSON.stringify({ actor }),
    }),
  reject: (changeId: string, actor: string) =>
    req<Change>(`/api/changes/${changeId}/reject`, {
      method: "POST",
      body: JSON.stringify({ actor }),
    }),
  build: (changeId: string) =>
    req<BuildResult>(`/api/changes/${changeId}/build`, { method: "POST" }),
  verify: (releaseId: string) => req<VerificationReport>(`/api/releases/${releaseId}/verify`),
  ask: (query?: string, sql?: string) =>
    req<AskResult>("/api/analytics/ask", {
      method: "POST",
      body: JSON.stringify({ query: query || "", sql: sql || "" }),
    }),
  analyticsSummary: () => req<AnalyticsSummary>("/api/analytics/summary"),
  tamper: (releaseId: string, nodeId?: string) =>
    req<TamperResponse>("/api/system/tamper", {
      method: "POST",
      body: JSON.stringify({ release_id: releaseId, node_id: nodeId }),
    }),
  setFaultInjection: (mode: string) =>
    req<{ mode: string }>("/api/system/fault-injection", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  diffReleases: (a: string, b: string) => req<ReleaseDiff>(`/api/releases/${a}/diff/${b}`),
  adkExecute: (goal: string, autoApprove: boolean = false) =>
    req<AdkExecutionResult>("/api/agents/adk/execute", {
      method: "POST",
      body: JSON.stringify({ goal, auto_approve: autoApprove }),
    }),
  adkResume: (changeId: string) =>
    req<AdkExecutionResult>("/api/agents/adk/resume", {
      method: "POST",
      body: JSON.stringify({ change_id: changeId }),
    }),
};

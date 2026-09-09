import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { BuildResult, Estimate } from "../types";
import { normalizeBackendNodeId, type Scenario, type SlateNode } from "../data/slate";

type BuildState = "idle" | "building" | "complete" | "error";
const DEMO_STAGE_MS = 4_000;

function demoStageDelay(): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, DEMO_STAGE_MS));
}

export default function StageRebuild({
  scenario, slate, changeId, estimate, buildResult, onBuildCompleted, onDone,
}: {
  scenario: Scenario;
  slate: SlateNode[];
  changeId?: string | null;
  estimate?: Estimate | null;
  buildResult?: BuildResult | null;
  onBuildCompleted?: (result: BuildResult) => void;
  onDone: () => void;
}) {
  const [state, setState] = useState<BuildState>(buildResult ? "complete" : "idle");
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const dirtyNodeIds = estimate?.dirty_node_ids ?? [];
  const displayNodes = useMemo(() => new Map(slate.map((node) => [node.id, node])), [slate]);
  const runs = useMemo(() => new Map((buildResult?.runs ?? []).map((run) => [run.node_id, run])), [buildResult]);
  const artifacts = useMemo(
    () => new Map((buildResult?.release?.artifacts ?? []).map((artifact) => [artifact.node_id, artifact])),
    [buildResult],
  );

  const runBuild = useCallback(async () => {
    if (!changeId || !estimate) {
      setState("error");
      setError("No approved backend estimate is available. The build remains blocked.");
      return;
    }
    setState("building");
    setError(null);
    try {
      const [result] = await Promise.all([api.build(changeId), demoStageDelay()]);
      onBuildCompleted?.(result);
      setState("complete");
      setShowSuccess(true);
    } catch (err) {
      console.error("Backend build request failed", err);
      setState("error");
      setError("The backend could not finish reporting this build. No successful result is being assumed.");
    }
  }, [changeId, estimate, onBuildCompleted]);

  useEffect(() => {
    if (buildResult) setState("complete");
    else if (state === "idle") void runBuild();
  }, [buildResult, runBuild, state]);

  const complete = state === "complete" && Boolean(buildResult?.release);
  return (
    <div className="stage-enter">
      <div className="grid lg:grid-cols-[340px_1fr] gap-5">
        <div className="surface p-6">
          <div className="flex items-center gap-4">
            <div className="relative w-16 h-16 flex-none">
              <div className="absolute inset-0 rounded-full flex items-center justify-center text-2xl text-white" style={{ background: "var(--charcoal)" }}>🤖</div>
              {state === "building" && <span className="orbit-dot absolute left-1/2 top-1/2 w-3 h-3 -ml-1.5 -mt-1.5 rounded-full" style={{ background: "var(--coral)" }} />}
            </div>
            <div>
              <div className="font-display font-bold text-lg leading-tight">
                {complete ? "Rebuild complete" : state === "error" ? "Rebuild failed" : "Backend build running…"}
              </div>
              <div className="text-[13px]" style={{ color: "var(--ink-soft)" }}>
                {complete
                  ? `${buildResult?.nodes_rebuilt ?? 0} rebuilt · ${buildResult?.nodes_reused ?? 0} reused from cache`
                  : `${dirtyNodeIds.length} dirty nodes approved`}
              </div>
            </div>
          </div>

          <div className="mt-6">
            <div className="flex justify-between text-[12px] font-semibold mb-1.5">
              <span style={{ color: "var(--ink-soft)" }}>DIRTY SUBTREE</span>
              <span className="font-mono2">{state === "building" ? "RUNNING" : complete ? "100%" : "BLOCKED"}</span>
            </div>
            <div className="h-3 rounded-full overflow-hidden" style={{ background: "var(--paper-warm)" }}>
              <div className={state === "building" ? "h-full progress-shimmer" : "h-full transition-all"} style={{ width: complete ? "100%" : state === "building" ? "45%" : "0%", background: "var(--mint-deep)" }} />
            </div>
          </div>

          {state === "building" && (
            <div className="mt-5 rounded-xl p-4 text-[13px]" style={{ background: "var(--paper-warm)", color: "var(--ink-soft)" }}>
              Building the approved dirty subtree in the background…
            </div>
          )}
          {state === "error" && (
            <div className="mt-5 rounded-xl p-4 text-[13px]" style={{ background: "var(--coral-soft)", color: "var(--coral)" }}>
              {error}
            </div>
          )}
          {complete && (
            <div className="mt-5 rounded-xl p-4 text-[13px]" style={{ background: "var(--mint)", color: "var(--mint-deep)" }}>
              Release {buildResult?.release?.release_id} is ready for verification.
            </div>
          )}
          {state === "error" && <button className="btn-pill btn-coral mt-4" onClick={() => void runBuild()}>Retry backend build</button>}
        </div>

        <div className="grid sm:grid-cols-2 gap-3 content-start">
          {dirtyNodeIds.map((nodeId) => {
            const node = displayNodes.get(normalizeBackendNodeId(nodeId));
            const run = runs.get(nodeId);
            const artifact = artifacts.get(nodeId);
            const status = state === "building" ? "building" : run?.status ?? "queued";
            return (
              <div key={nodeId} className="surface p-4 transition-all" style={{ borderColor: status === "building" ? "var(--coral)" : status === "ok" ? "var(--mint-deep)" : "var(--hairline)", borderWidth: status === "queued" ? 1 : 2 }}>
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-semibold text-[14px] truncate">{node?.label ?? nodeId}</div>
                    <div className="font-mono2 text-[10.5px] break-all" style={{ color: "var(--ink-soft)" }}>{nodeId}</div>
                  </div>
                  <span className="pill" style={{ background: status === "ok" ? "var(--mint)" : status === "building" ? "var(--coral-soft)" : "var(--paper-warm)", color: status === "ok" ? "var(--mint-deep)" : status === "building" ? "var(--coral)" : "var(--ink-soft)" }}>
                    {status === "ok" ? "✓ sealed" : status}
                  </span>
                </div>
                {artifact && <div className="mt-2 font-mono2 text-[10px] break-all" style={{ color: "var(--mint-deep)" }}>sha256 {artifact.sha256}</div>}
              </div>
            );
          })}
        </div>
      </div>

      {showSuccess && buildResult?.release && (
        <SuccessPopup scenario={scenario} buildResult={buildResult} onContinue={() => { setShowSuccess(false); onDone(); }} />
      )}
    </div>
  );
}

function SuccessPopup({ scenario, buildResult, onContinue }: { scenario: Scenario; buildResult: BuildResult; onContinue: () => void }) {
  const total = buildResult.nodes_rebuilt + buildResult.nodes_reused;
  const reuseRate = total ? `${((buildResult.nodes_reused / total) * 100).toFixed(1)}%` : "0.0%";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overlay-in" style={{ background: "rgba(43,41,38,0.45)", backdropFilter: "blur(4px)" }}>
      <div className="surface pop-in relative max-w-md w-[92%] p-8 text-center" style={{ borderRadius: 28 }}>
        <div className="mx-auto w-20 h-20 rounded-full flex items-center justify-center" style={{ background: "var(--mint)" }}><span className="text-4xl">✓</span></div>
        <h3 className="font-display font-bold text-2xl mt-4">That's a wrap! 🎬</h3>
        <p className="text-[14px] mt-2" style={{ color: "var(--ink-soft)" }}>Backend release <b>{buildResult.release?.release_id}</b> completed for {scenario.title}.</p>
        <div className="grid grid-cols-3 gap-2 mt-5">
          <StatPill v={String(buildResult.nodes_rebuilt)} l="rebuilt" c="var(--coral)" />
          <StatPill v={String(buildResult.nodes_reused)} l="reused · $0.00" c="var(--mint-deep)" />
          <StatPill v={reuseRate} l="cache reuse" c="var(--mint-deep)" />
        </div>
        <div className="font-mono2 text-[12px] mt-4 rounded-xl py-2" style={{ background: "var(--paper-warm)", color: "var(--ink-soft)" }}>
          billed ${Number(buildResult.total_cost_usd).toFixed(4)} · {buildResult.release?.artifacts.length ?? 0} manifest artifacts
        </div>
        <button className="btn-pill w-full justify-center mt-5" onClick={onContinue}>Verify the release →</button>
      </div>
    </div>
  );
}

function StatPill({ v, l, c }: { v: string; l: string; c: string }) {
  return <div className="rounded-xl py-3 px-1" style={{ background: "var(--paper-warm)" }}><div className="font-mono2 font-bold text-lg" style={{ color: c }}>{v}</div><div className="text-[11px] font-medium" style={{ color: "var(--ink-soft)" }}>{l}</div></div>;
}

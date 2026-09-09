import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { Estimate, GraphView } from "../types";

const DEMO_STAGE_MS = 4_000;

function waitForRemainingStageTime(startedAt: number): Promise<void> {
  const remaining = Math.max(0, DEMO_STAGE_MS - (performance.now() - startedAt));
  return new Promise((resolve) => window.setTimeout(resolve, remaining));
}

export default function StageScan({
  changeId,
  submissionPending,
  onEstimated,
  onDone,
}: {
  changeId?: string | null;
  submissionPending: boolean;
  onEstimated?: (est: Estimate, graph: GraphView) => void;
  onDone: () => void;
}) {
  const [backendEst, setBackendEst] = useState<Estimate | null>(null);
  const [requestState, setRequestState] = useState<"loading" | "ready" | "error">("loading");
  const [requestError, setRequestError] = useState<string | null>(null);
  const startedAtRef = useRef(performance.now());
  const traceLines = useMemo(
    () => backendEst?.dirty_nodes.map((node) => ({
      path: node.node_id,
      detail: node.reason,
    })) ?? [],
    [backendEst],
  );
  const logRef = useRef<HTMLDivElement>(null);

  // Call real backend estimate if changeId is present
  useEffect(() => {
    setBackendEst(null);
    setRequestError(null);
    setRequestState("loading");
    if (!changeId) {
      if (submissionPending) return;
      setRequestState("error");
      setRequestError("Google ADK did not produce a backend change. Return to the brief and submit again.");
      return;
    }
    let active = true;
    Promise.all([
      api.estimate(changeId),
      api.graph(changeId),
      waitForRemainingStageTime(startedAtRef.current),
    ])
      .then(([est, g]) => {
        if (!active) return;
        setBackendEst(est);
        setRequestState("ready");
        onEstimated?.(est, g);
      })
      .catch((err) => {
        if (!active) return;
        setRequestState("error");
        setRequestError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      active = false;
    };
  }, [changeId, onEstimated, submissionPending]);

  const finished = requestState === "ready" && backendEst !== null;
  const dirtyFound = backendEst?.dirty_node_ids.length ?? 0;
  const scanned = backendEst ? backendEst.dirty_node_ids.length + backendEst.reused_node_ids.length : 0;

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [traceLines]);

  return (
    <div className="stage-enter">
      <div className="grid lg:grid-cols-[320px_1fr] gap-5">
        {/* ── agent status panel ── */}
        <div className="surface p-6 flex flex-col items-center text-center">
          {/* radar */}
          <div className="relative w-36 h-36 mt-2">
            <div className="absolute inset-0 rounded-full border" style={{ borderColor: "var(--hairline)" }} />
            <div className="absolute inset-4 rounded-full border" style={{ borderColor: "var(--hairline)" }} />
            <div className="absolute inset-8 rounded-full border" style={{ borderColor: "var(--hairline)" }} />
            <svg viewBox="0 0 100 100" className="absolute inset-0 radar-sweep">
              <defs>
                <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="var(--coral)" stopOpacity="0" />
                  <stop offset="100%" stopColor="var(--coral)" stopOpacity="0.35" />
                </linearGradient>
              </defs>
              <path d="M50,50 L50,2 A48,48 0 0 1 82,16 Z" fill="url(#sweep)" />
              <line x1="50" y1="50" x2="50" y2="2" stroke="var(--coral)" strokeWidth="1.4" />
            </svg>
            <div
              className="absolute w-11 h-11 rounded-full flex items-center justify-center text-white text-lg"
              style={{ background: "var(--charcoal)", left: "50%", top: "50%", transform: "translate(-50%,-50%)" }}
            >
              🕵️
            </div>
            {finished && (
              <span
                className="dot dot-pulse absolute"
                style={{ background: "var(--coral)", color: "var(--coral)", right: 22, top: 34, width: 10, height: 10 }}
              />
            )}
          </div>

          <div className="font-display font-bold text-lg mt-4">
            {requestState === "error" ? "Scan failed" : finished ? "Scan complete" : "Dependency agent scanning…"}
          </div>
          <div className="text-[13px] mt-1" style={{ color: "var(--ink-soft)" }}>
            {requestState === "error"
              ? "No estimate was produced and the workflow remains blocked."
              : finished
              ? "The blast radius is mapped. Ready to visualize."
              : submissionPending
              ? "Google ADK is interpreting the change in the background…"
              : "Waiting for the deterministic backend estimate…"}
          </div>

          <div className="w-full mt-6 space-y-3">
            <Stat label="Nodes evaluated" value={finished ? String(scanned) : "—"} />
            <Stat
              label="Dirty files found"
              value={String(dirtyFound)}
              accent={dirtyFound > 0 ? "var(--coral)" : undefined}
            />
            <Stat label="Cache re-usable" value={backendEst ? String(backendEst.reused_node_ids.length) : "—"} accent="var(--mint-deep)" />
          </div>

          {!finished && (
            <div className="mt-5 font-mono2 text-[11px]" style={{ color: "var(--ink-soft)" }}>
              JCS RFC 8785 → SHA-256<span className="caret">▌</span>
            </div>
          )}
        </div>

        {/* ── scan log ── */}
        <div className="surface overflow-hidden flex flex-col">
          <div className="hairline-b px-5 py-3 flex items-center justify-between">
            <span className="font-mono2 text-[11px] font-semibold tracking-widest" style={{ color: "var(--ink-soft)" }}>
              AGENT TRACE · deterministic estimate
            </span>
            <span
              className="pill"
              style={{
                background: finished ? "var(--mint)" : "var(--amber-soft)",
                color: finished ? "var(--mint-deep)" : "#96690f",
              }}
            >
              <span className={`dot ${finished ? "" : "dot-pulse"}`} style={{ background: finished ? "var(--mint-deep)" : "var(--amber)", color: "var(--amber)" }} />
              {requestState === "error" ? "ERROR" : finished ? "ESTIMATE READY" : "SCANNING"}
            </span>
          </div>
          <div ref={logRef} className="relative p-4 space-y-1.5 overflow-y-auto font-mono2 text-[12.5px]" style={{ maxHeight: 380, minHeight: 380 }}>
            {traceLines.map((l, i) => (
              <div key={i} className="rise-in flex items-center gap-3 rounded-lg px-3 py-2"
                style={{ background: "var(--coral-soft)" }}>
                <span style={{ color: "var(--coral)" }}>
                  ✗
                </span>
                <span className="flex-1 truncate" style={{ color: "var(--coral)" }}>
                  {l.path}
                </span>
                <span className="text-[11px] flex-none" style={{ color: "var(--coral)" }}>
                  {l.detail}
                </span>
              </div>
            ))}
            {requestState === "loading" && (
              <div className="rounded-xl p-4 flex items-center gap-3" style={{ background: "var(--paper-warm)", color: "var(--ink)" }}>
                <span className="dot dot-pulse" style={{ background: "var(--coral)" }} />
                <span className="font-medium text-[13.5px]">Analyzing dependencies and calculating blast radius...</span>
              </div>
            )}
            {requestState === "error" && (
              <div className="rounded-xl p-4" style={{ background: "var(--coral-soft)", color: "var(--coral)" }}>
                ⚠ {requestError ?? "The backend estimate request failed."}
              </div>
            )}
            {finished && (
              <div className="rise-in rounded-xl p-4 mt-3" style={{ background: "var(--coral-soft)", border: "1px solid #f6c3d0" }}>
                <span className="font-sans font-semibold text-[14px]" style={{ color: "var(--coral)", fontFamily: "Figtree" }}>
                  ⚑ {dirtyFound} dirty assets located — everything else is cache-clean.
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex justify-end mt-6">
        <button className="btn-pill" disabled={!finished} onClick={onDone}>
          Open dependency graph →
        </button>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between rounded-xl px-4 py-2.5" style={{ background: "var(--paper-warm)" }}>
      <span className="text-[12.5px] font-medium" style={{ color: "var(--ink-soft)" }}>{label}</span>
      <span className="font-mono2 font-bold text-[15px]" style={{ color: accent ?? "var(--ink)" }}>{value}</span>
    </div>
  );
}

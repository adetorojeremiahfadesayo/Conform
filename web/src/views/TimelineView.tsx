import { useState } from "react";
import { api } from "../api";
import type { BuildResult, VerificationReport } from "../types";

interface Props {
  build: BuildResult | null;
  onVerified?: () => void;
}

type Filter = "all" | "rebuilt" | "reused" | "retries";

export function TimelineView({ build, onVerified }: Props) {
  const [report, setReport] = useState<VerificationReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [tamperMsg, setTamperMsg] = useState<string | null>(null);
  const [faultMode, setFaultMode] = useState<string>("off");
  const [filter, setFilter] = useState<Filter>("all");

  async function toggleFault() {
    const next = faultMode === "off" ? "transient_once" : "off";
    await api.setFaultInjection(next);
    setFaultMode(next);
  }

  async function handleTamper() {
    if (!build?.release) return;
    setBusy(true);
    try {
      const res = await api.tamper(build.release.release_id);
      setTamperMsg(res.message);
    } catch (e) {
      setTamperMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify() {
    if (!build?.release) return;
    setBusy(true);
    try {
      const rep = await api.verify(build.release.release_id);
      setReport(rep);
      if (rep.ok && onVerified) {
        onVerified();
      }
    } finally {
      setBusy(false);
    }
  }

  if (!build) {
    return (
      <div>
        <div className="panel">
          <h2>4 · Build Subtree & Timeline</h2>
          <p style={{ color: "var(--dim)", fontSize: 13, margin: 0 }}>
            No build executed in this session yet. Go to <strong>Change & Approval</strong>, compute the blast radius,
            and click <strong>Build Dirty Subtree</strong>.
          </p>

          {/* Fault injection toggle even when no build yet */}
          <div
            style={{
              marginTop: 18,
              padding: "14px 16px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "rgba(18, 24, 38, 0.6)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <span style={{ fontWeight: 600, fontSize: 13 }}>Dynamic Fault Injection Switch (FR-6.5)</span>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--dim)" }}>
                Toggle simulated transient timeout (HTTP 503) on the clip model for the next build run.
              </p>
            </div>
            <button
              className="chip"
              style={{
                cursor: "pointer",
                padding: "6px 14px",
                background: faultMode === "transient_once" ? "rgba(239, 68, 68, 0.2)" : undefined,
                borderColor: faultMode === "transient_once" ? "#ef4444" : undefined,
                color: faultMode === "transient_once" ? "#fca5a5" : undefined,
              }}
              onClick={toggleFault}
            >
              Simulate Transient 503: {faultMode === "transient_once" ? "ACTIVE" : "OFF"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Filter runs according to active filter
  const visibleRuns = build.runs.filter((r) => {
    if (filter === "rebuilt") return !r.cache_hit;
    if (filter === "reused") return r.cache_hit;
    if (filter === "retries") return r.attempt > 1 || r.status === "failed";
    return true;
  });

  return (
    <div>
      {/* Build Summary Panel */}
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
          <div>
            <h2>4 · Build Execution · {build.build_id}</h2>
            <p style={{ margin: 0, fontSize: 12, color: "var(--dim)" }}>
              Release: <strong>{build.release?.release_id ?? "none"}</strong> · Change: {build.change_id}
            </p>
          </div>

          <button
            className="chip"
            style={{
              cursor: "pointer",
              background: faultMode === "transient_once" ? "rgba(239, 68, 68, 0.2)" : undefined,
              borderColor: faultMode === "transient_once" ? "#ef4444" : undefined,
              color: faultMode === "transient_once" ? "#fca5a5" : undefined,
            }}
            onClick={toggleFault}
          >
            Fault injection for next build: {faultMode === "transient_once" ? "TRANSIENT 503 ON" : "OFF"}
          </button>
        </div>

        <div className="stats">
          <div className="stat">
            <div className="num">{build.nodes_rebuilt}</div>
            <div className="lbl">rebuilt nodes</div>
          </div>
          <div className="stat reused">
            <div className="num">{build.nodes_reused}</div>
            <div className="lbl">reused from cache</div>
          </div>
          <div className="stat">
            <div className="num">${build.total_cost_usd}</div>
            <div className="lbl">actual incurred cost</div>
          </div>
          <div className="stat accent">
            <div className="num">{build.retries}</div>
            <div className="lbl">automatic retries</div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div style={{ display: "flex", gap: 8, margin: "16px 0 8px", borderBottom: "1px solid var(--border)", paddingBottom: 10 }}>
          <button
            className={`chip ${filter === "all" ? "live" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("all")}
          >
            All Runs ({build.runs.length})
          </button>
          <button
            className={`chip ${filter === "rebuilt" ? "fallback" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("rebuilt")}
          >
            Rebuilt Only ({build.nodes_rebuilt})
          </button>
          <button
            className={`chip ${filter === "reused" ? "live" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("reused")}
          >
            Cache Hits Reused ({build.nodes_reused})
          </button>
          <button
            className={`chip ${filter === "retries" ? "fallback" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("retries")}
          >
            Retries ({build.retries})
          </button>
        </div>

        {/* Run list */}
        <div style={{ maxHeight: 340, overflowY: "auto" }}>
          {visibleRuns.map((r) => (
            <div
              key={r.run_id}
              className="run-row"
              style={r.parent_run_id ? { marginLeft: 28, background: "rgba(245, 158, 11, 0.05)" } : undefined}
            >
              <span className="node">
                {r.parent_run_id ? "↳ " : ""}
                {r.node_id}
              </span>
              <span className={`badge ${r.status}`}>{r.status}</span>
              {r.cache_hit && <span className="badge cache">cache hit — $0.00</span>}
              {r.attempt > 1 && <span className="badge retry">attempt {r.attempt} (auto-recovered)</span>}
              {r.error_class !== "none" && <span className="badge err">{r.error_class}</span>}
              <span style={{ color: "var(--dim)", marginLeft: "auto", fontFamily: "var(--font-mono)" }}>
                ${r.cost_usd}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Verification & Tamper Detection Studio (FR-7.4) */}
      {build.release && (
        <div className="panel">
          <h2>5 · Cryptographic Verification Studio (Release {build.release.release_id})</h2>
          <p style={{ color: "var(--dim)", fontSize: 13, marginBottom: 14 }}>
            Re-downloads every artifact from storage and verifies its SHA-256 hash byte-exact against the release manifest.
            Use the <strong>Tamper Demo</strong> to corrupt 1 byte in storage and prove tamper detection.
          </p>

          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <button className="primary" disabled={busy} onClick={handleVerify}>
              {busy ? "Verifying Artifacts..." : "🔍 Verify Release (SHA-256 Byte-Exact)"}
            </button>
            <button className="danger" disabled={busy} onClick={handleTamper}>
              ⚠️ Corrupt 1 Byte in Storage (Tamper Demo)
            </button>
          </div>

          {tamperMsg && (
            <div
              style={{
                marginTop: 14,
                padding: "10px 14px",
                borderRadius: 8,
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                color: "#fca5a5",
                fontSize: 12,
              }}
            >
              {tamperMsg}
            </div>
          )}

          {report && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  padding: "12px 16px",
                  borderRadius: 8,
                  background: report.ok ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.15)",
                  border: `1px solid ${report.ok ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.4)"}`,
                  color: report.ok ? "#10b981" : "#f87171",
                  fontWeight: 700,
                  fontSize: 14,
                }}
              >
                {report.ok ? "✓ All artifacts verified byte-exact against immutable manifest" : "✗ Verification FAILED — Cryptographic hash mismatch detected!"}
              </div>

              <div style={{ marginTop: 10, maxHeight: 240, overflowY: "auto" }}>
                {report.per_artifact.map((a) => (
                  <div key={a.node_id} className="run-row">
                    <span className="node">{a.node_id}</span>
                    <span className={`badge ${a.ok ? "ok" : "failed"}`}>
                      {a.ok ? "✓ VERIFIED" : "✗ MISMATCH (TAMPERED)"}
                    </span>
                    <span style={{ fontSize: 10, color: "var(--dim)", marginLeft: "auto", fontFamily: "var(--font-mono)" }}>
                      {a.uri}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import { api, ApiError } from "../api";
import type { AdkExecutionResult, BuildResult, Estimate } from "../types";

interface Scenario {
  id: string;
  title: string;
  description: string;
  text: string;
  expectedDirty: string;
  tag: string;
  analogy: string;
}

const SCENARIOS: Scenario[] = [
  {
    id: "eu-reg",
    title: "🇪🇺 EU Regulation Change (Main Demo)",
    description: "EU mandates longer allergy disclaimer in Germany & France. Only 12 of 252 assets dirty; 240 reused.",
    text: "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40",
    expectedDirty: "12 / 252 dirty (~$0.0030 spend)",
    tag: "Rule Compliance",
    analogy: "Like adding 5 words of warning text to the bottom of the German/French screen, while keeping the expensive sneaker video clip untouched.",
  },
  {
    id: "hero-clip",
    title: "🎬 Master Clip Reshoot",
    description: "Creative director updates the video clip prompt. Preserves master source, shot plan, keyframe, and 40 copy variants.",
    text: "edit node campaign_a.clip: set prompt to reshoot hero close-up at golden hour",
    expectedDirty: "41 / 252 dirty (clip + 40 packages)",
    tag: "Asset Edit",
    analogy: "Reshooting only the hero video shot. All 40 localized voiceovers and subtitles are reused from memory without re-recording.",
  },
  {
    id: "japan-copy",
    title: "🇯🇵 Japan Winter Retargeting",
    description: "Single-territory text localization. Only Japanese copy and final package are dirty.",
    text: "edit node campaign_a.copy.jp: set prompt to add Tokyo winter holiday promotion disclaimer",
    expectedDirty: "2 / 252 dirty (250 reused!)",
    tag: "Local Retargeting",
    analogy: "Changing one sentence in Tokyo. 250 assets across 39 other countries remain 100% clean and untouched.",
  },
];

interface Props {
  onGraphDirty: (changeId: string) => void;
  onBuilt: (result: BuildResult) => void;
  onEstimate: (estimate: Estimate | null) => void;
  onViewGraph?: () => void;
}

export function ChangeView({ onGraphDirty, onBuilt, onEstimate, onViewGraph }: Props) {
  const [selectedScenario, setSelectedScenario] = useState<string>(SCENARIOS[0].id);
  const [text, setText] = useState(SCENARIOS[0].text);
  const [changeId, setChangeId] = useState<string | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [approved, setApproved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [adkResult, setAdkResult] = useState<AdkExecutionResult | null>(null);

  async function guard(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError ? `${e.code}: ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  }

  const submit = () =>
    guard(async () => {
      const change = await api.submitChange(text);
      setChangeId(change.change_id);
      setEstimate(null);
      setApproved(false);
      setAdkResult(null);
      const est = await api.estimate(change.change_id);
      setEstimate(est);
      onEstimate(est);
      onGraphDirty(change.change_id);
    });

  const approve = () =>
    guard(async () => {
      if (!changeId) return;
      await api.approve(changeId, "producer (simulated)");
      setApproved(true);
    });

  const reject = () =>
    guard(async () => {
      if (!changeId) return;
      await api.reject(changeId, "producer (simulated)");
      setApproved(false);
      setEstimate(null);
      onEstimate(null);
      setChangeId(null);
      onGraphDirty("");
    });

  const build = () =>
    guard(async () => {
      if (!changeId) return;
      const result = await api.build(changeId);
      onBuilt(result);
    });

  const runAdkAgent = () =>
    guard(async () => {
      const res = await api.adkExecute(text, true);
      setAdkResult(res);
      if (res.change_id) {
        setChangeId(res.change_id);
        const est = await api.estimate(res.change_id);
        setEstimate(est);
        onEstimate(est);
        onGraphDirty(res.change_id);
      }
    });

  // Naive full rebuild cost estimate ($0.00025 avg per node * 252 nodes)
  const naiveSpend = 0.063;
  const actualEst = estimate ? parseFloat(estimate.estimated_cost_usd) : 0;
  const avoidedEst = (naiveSpend - actualEst).toFixed(4);
  const percentSaved = Math.max(0, Math.round(((naiveSpend - actualEst) / naiveSpend) * 100));
  const activeScenario = SCENARIOS.find((s) => s.id === selectedScenario);

  return (
    <div>
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <h2>1 · Propose Creative or Compliance Change</h2>
          <span className="chip live">⚡ Real-Time Graph Analysis</span>
        </div>
        <p style={{ color: "var(--text-muted)", fontSize: 13.5, marginBottom: 16 }}>
          Choose a one-click scenario to see how CONFORM detects the exact blast radius and saves your budget:
        </p>

        {/* 3D Scenario Preset Cards */}
        <div className="scenario-grid">
          {SCENARIOS.map((s) => (
            <div
              key={s.id}
              className={`scenario-card ${selectedScenario === s.id ? "active" : ""}`}
              onClick={() => {
                setSelectedScenario(s.id);
                setText(s.text);
                setEstimate(null);
                setApproved(false);
              }}
            >
              <div>
                <div className="scenario-title">{s.title}</div>
                <p className="scenario-desc">{s.description}</p>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "var(--neon-cyan)", fontStyle: "italic", marginBottom: 8 }}>
                  💡 {s.analogy}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className="scenario-badge">{s.tag}</span>
                  <span style={{ fontSize: 11.5, color: "var(--dirty)", fontWeight: 800 }}>{s.expectedDirty}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 14 }}>
          <label style={{ fontSize: 12, fontWeight: 700, color: "var(--neon-cyan)", display: "block", marginBottom: 6 }}>
            INSTRUCTION PAYLOAD (NATURAL LANGUAGE OR REGULATION DSL)
          </label>
          <textarea
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setSelectedScenario("");
            }}
            placeholder="e.g. new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40"
          />
        </div>

        <div style={{ marginTop: 16, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button className="primary" onClick={submit} disabled={busy || !text.trim()}>
            {busy ? "Analyzing Blueprint..." : "⚡ Compute Blast Radius (Find Dirty Files)"}
          </button>

          <button
            className="secondary"
            onClick={runAdkAgent}
            disabled={busy || !text.trim()}
            style={{
              borderColor: "var(--purple)",
              color: "#fff",
              background: "linear-gradient(135deg, rgba(192, 132, 252, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%)",
            }}
          >
            🤖 Run with Google ADK Agent
          </button>

          {activeScenario && (
            <span style={{ fontSize: 12.5, color: "var(--dim)", fontWeight: 600 }}>
              👉 Ready! Click the button above to discover what changed.
            </span>
          )}
        </div>

        {error && <div className="error">{error}</div>}
      </div>

      {/* ADK Agent Result Box */}
      {adkResult && (
        <div
          className="panel"
          style={{
            borderColor: "var(--purple)",
            background: "linear-gradient(135deg, rgba(20, 27, 50, 0.95) 0%, rgba(30, 20, 50, 0.95) 100%)",
          }}
        >
          <h2>🤖 Google ADK Agent Multi-Step Execution</h2>
          <p style={{ fontSize: 13.5, color: "var(--text-muted)", margin: "0 0 12px" }}>
            The Google Agent Development Kit autonomous compiler executed the following tool chain:
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            {adkResult.tools_called.map((tool, i) => (
              <span key={i} className="chip live" style={{ color: "var(--purple)", borderColor: "var(--purple)" }}>
                Step {i + 1}: {tool}()
              </span>
            ))}
          </div>
          <div
            style={{
              padding: "12px 16px",
              background: "rgba(0,0,0,0.3)",
              borderRadius: 8,
              fontFamily: "var(--font-mono)",
              fontSize: 12.5,
              color: "#e2e8f0",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            {adkResult.final_answer}
          </div>
        </div>
      )}

      {/* 2. Blast Radius & Cost Estimate */}
      {estimate && (
        <div className="panel" style={{ borderColor: "rgba(0, 242, 254, 0.4)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <div>
              <h2>2 · Blast Radius & Pre-Spend Cost Quote</h2>
              <span style={{ fontSize: 12.5, color: "var(--clean)", fontWeight: 700 }}>
                ✓ Clean assets are recycled from cache for $0.00 — zero wasted compute
              </span>
            </div>
            {onViewGraph && (
              <button
                className="primary"
                onClick={onViewGraph}
                style={{
                  background: "linear-gradient(135deg, #00f2fe 0%, #38bdf8 100%)",
                  padding: "8px 16px",
                  fontSize: 12.5,
                }}
              >
                🧊 Inspect 3D Graph (Step 2) ➔
              </button>
            )}
          </div>

          <div className="stats">
            <div className="stat dirty">
              <div className="num">{estimate.dirty_node_ids.length}</div>
              <div className="lbl">DIRTY (REBUILD REQUIRED)</div>
            </div>
            <div className="stat clean">
              <div className="num">{estimate.reused_node_ids.length}</div>
              <div className="lbl">CLEAN (REUSED AT $0.00)</div>
            </div>
            <div className="stat cost">
              <div className="num">${estimate.estimated_cost_usd}</div>
              <div className="lbl">ESTIMATED REBUILD BILL</div>
            </div>
            <div className="stat saved">
              <div className="num">{percentSaved}%</div>
              <div className="lbl">SPEND AVOIDED</div>
            </div>
          </div>

          {/* Compilation Savings Comparison Box */}
          <div className="savings-callout">
            <div>
              <div style={{ fontWeight: 800, fontSize: 15, color: "#ffffff", marginBottom: 4 }}>
                💰 Compilation Savings: 95%+ Avoided Spend
              </div>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)", lineHeight: 1.4 }}>
                A naive system would throw away all 252 files and regenerate everything, costing <strong>${naiveSpend.toFixed(4)}</strong>.
                CONFORM rebuilds only the {estimate.dirty_node_ids.length} dirty files for <strong>${estimate.estimated_cost_usd}</strong>,
                saving you <strong>${avoidedEst}</strong>.
              </p>
            </div>
            <div className="savings-num">{percentSaved}% SAVED</div>
          </div>

          {/* 3. Human Approval Gate */}
          <div
            style={{
              background: approved
                ? "linear-gradient(135deg, rgba(0, 255, 157, 0.1) 0%, rgba(20, 27, 50, 0.95) 100%)"
                : "rgba(15, 21, 38, 0.95)",
              border: approved ? "1px solid var(--clean)" : "1px solid var(--border)",
              borderRadius: 14,
              padding: "20px",
              marginTop: 20,
              boxShadow: approved ? "0 8px 30px var(--clean-glow)" : "0 4px 16px rgba(0,0,0,0.3)",
              transition: "all 0.3s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontWeight: 900, fontSize: 16, color: "#fff" }}>3 · Human Approval Gate</span>
                  <span className={`chip ${approved ? "live" : "fallback"}`}>
                    {approved ? "✓ Approved by Producer" : "🛑 Awaiting Human Approval"}
                  </span>
                </div>
                <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--text-muted)", lineHeight: 1.4 }}>
                  {approved
                    ? "Budget approved! The spend barrier is lifted. You can now trigger the surgical rebuild."
                    : "The AI is locked from spending money. Review the bill ($" + estimate.estimated_cost_usd + ") and approve to proceed."}
                </p>
              </div>

              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                {!approved ? (
                  <>
                    <button className="primary approve-btn" onClick={approve} disabled={busy}>
                      ✓ Approve Spend (${estimate.estimated_cost_usd})
                    </button>
                    <button className="reject-btn secondary" onClick={reject} disabled={busy}>
                      Reject Change
                    </button>
                  </>
                ) : (
                  <button
                    className="primary build-pulse"
                    onClick={build}
                    disabled={busy}
                    style={{
                      padding: "12px 28px",
                      fontSize: 15,
                      fontWeight: 900,
                      background: "linear-gradient(135deg, #00f2fe 0%, #3b82f6 100%)",
                    }}
                  >
                    {busy ? "Compiling Subtree..." : "🚀 Build Dirty Subtree (Step 4) ➔"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

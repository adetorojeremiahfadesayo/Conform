import { useState } from "react";
import { api, ApiError } from "../api";
import type { AdkExecutionResult } from "../types";

const GOAL_PRESETS = [
  {
    title: "EU Regulation R-DISC-004",
    goal: "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40",
    desc: "Enforce 40-char allergy & sustainability disclaimer in German & French markets.",
  },
  {
    title: "Hero Clip Reshoot",
    goal: "edit node campaign_a.clip: set prompt to Sunset coastal highway turn with dynamic aerial tracking camera and warm golden glow",
    desc: "Art director reshoot note: Replace coastal road turn with golden hour drone footage.",
  },
  {
    title: "Japan Market Retargeting",
    goal: "edit node campaign_a.copy.jp: set copy to Aurora EV: 静寂と革新が交差する、次世代のラグジュアリー体験。",
    desc: "Localise on-screen headline and disclaimer for Tokyo launch window.",
  },
];

interface AdkModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncToMainView?: (changeId: string) => void;
}

export default function AdkModal({ isOpen, onClose, onSyncToMainView }: AdkModalProps) {
  const [goal, setGoal] = useState(GOAL_PRESETS[0].goal);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AdkExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approvalBusy, setApprovalBusy] = useState(false);

  if (!isOpen) return null;

  async function handleExecuteGoal(customGoal?: string) {
    const activeGoal = customGoal !== undefined ? customGoal : goal;
    if (!activeGoal.trim()) return;

    setBusy(true);
    setError(null);
    try {
      // auto_approve = false enforces Invariant 4: No generative calls before approval
      const res = await api.adkExecute(activeGoal, false);
      setResult(res);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? `${e.code}: ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleApproveAndResume() {
    if (!result?.change_id) return;
    setApprovalBusy(true);
    setError(null);
    try {
      // 1. Explicit human approval gate
      await api.approve(result.change_id, "producer (adk_human_in_loop)");
      // 2. Resume ADK orchestrator to build dirty subtree and verify release
      const resumedResult = await api.adkResume(result.change_id);
      setResult(resumedResult);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.code}: ${e.message}` : String(e));
    } finally {
      setApprovalBusy(false);
    }
  }

  async function handleReject() {
    if (!result?.change_id) return;
    setApprovalBusy(true);
    try {
      await api.reject(result.change_id, "producer (adk_human_in_loop)");
      setResult(null);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.code}: ${e.message}` : String(e));
    } finally {
      setApprovalBusy(false);
    }
  }

  const isAwaitingApproval =
    result &&
    result.change_id &&
    !result.release_id &&
    result.tools_called.includes("interpret_and_estimate") &&
    !result.tools_called.includes("build_dirty_subtree");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 overlay-in"
      style={{ background: "rgba(43,41,38,0.6)", backdropFilter: "blur(8px)" }}
    >
      <div
        className="surface pop-in relative max-w-3xl w-full max-h-[92vh] flex flex-col overflow-hidden shadow-2xl"
        style={{ borderRadius: 24, border: "1px solid var(--hairline)" }}
      >
        {/* Header */}
        <div className="hairline-b p-6 flex items-center justify-between" style={{ background: "var(--paper-warm)" }}>
          <div className="flex items-center gap-3">
            <span
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-sm"
              style={{ background: "var(--charcoal)" }}
            >
              🤖
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-lg">Google ADK Autonomous Orchestrator</span>
                <span className="pill text-[10px] font-mono2" style={{ background: "var(--mint)", color: "var(--mint-deep)" }}>
                  google-adk 2.8.0
                </span>
              </div>
              <div className="text-[12.5px]" style={{ color: "var(--ink-soft)" }}>
                Multi-step autonomous agent with pause-and-resume human approval gate
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm transition-colors hover:bg-black/5"
            style={{ color: "var(--ink-soft)" }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          <p className="text-[13.5px] leading-relaxed" style={{ color: "var(--ink-soft)" }}>
            The <b>Google ADK Agent</b> uses official tool definitions to evaluate rule changes, estimate DAG blast radius,
            pause for human spend approval, incrementally rebuild dirty nodes, and verify byte-exact cryptographic manifests.
          </p>

          {/* Presets */}
          <div className="space-y-2">
            <div className="text-[11px] font-mono2 font-semibold uppercase tracking-wider" style={{ color: "var(--ink-soft)" }}>
              Select Goal Preset
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {GOAL_PRESETS.map((p) => (
                <button
                  key={p.title}
                  onClick={() => {
                    setGoal(p.goal);
                    handleExecuteGoal(p.goal);
                  }}
                  className="p-3 text-left rounded-xl border transition-all text-xs flex flex-col justify-between"
                  style={{
                    background: goal === p.goal ? "var(--paper-warm)" : "#fff",
                    borderColor: goal === p.goal ? "var(--charcoal)" : "var(--hairline)",
                  }}
                >
                  <div className="font-bold mb-1" style={{ color: "var(--ink)" }}>{p.title}</div>
                  <div className="text-[11px] leading-snug" style={{ color: "var(--ink-soft)" }}>{p.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Goal Input & Run Button */}
          <div className="space-y-2">
            <div className="text-[11px] font-mono2 font-semibold uppercase tracking-wider" style={{ color: "var(--ink-soft)" }}>
              Pipeline Goal Statement
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleExecuteGoal()}
                placeholder="Enter pipeline change instruction or regulatory rule..."
                className="flex-1 rounded-xl border px-4 py-2.5 text-[13.5px] outline-none font-mono2"
                style={{ borderColor: "var(--hairline)", background: "var(--paper)" }}
              />
              <button
                className="btn-pill flex-none font-semibold text-[13px]"
                onClick={() => handleExecuteGoal()}
                disabled={busy || !goal.trim()}
              >
                {busy ? "Agent Planning…" : "▶ Run ADK Agent"}
              </button>
            </div>
          </div>

          {/* Error display */}
          {error && (
            <div className="rounded-xl p-3 text-[13px] border" style={{ background: "var(--coral-soft)", borderColor: "var(--coral)", color: "var(--coral)" }}>
              <b>Error:</b> {error}
            </div>
          )}

          {/* Human Approval Gate (Pause & Resume) */}
          {isAwaitingApproval && (
            <div
              className="rounded-2xl p-5 border shadow-sm rise-in space-y-3"
              style={{ background: "#fffdf0", borderColor: "#f1c40f" }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xl">⏸</span>
                  <span className="font-display font-bold text-[15px]" style={{ color: "#7d5a00" }}>
                    Paused at Human Approval Gate (Invariant Enforced)
                  </span>
                </div>
                <span className="pill text-[11px] font-mono2" style={{ background: "#fef9e7", color: "#b7950b" }}>
                  AWAITING_APPROVAL
                </span>
              </div>
              <p className="text-[13px] leading-relaxed" style={{ color: "#7d5a00" }}>
                The Google ADK Agent has interpreted the goal and calculated the exact blast radius.
                In accordance with <b>AGENTS.md Invariant 4</b>, no generative spend or rebuild may proceed without explicit human authorization.
              </p>
              <div className="flex items-center gap-3 pt-1">
                <button
                  onClick={handleApproveAndResume}
                  disabled={approvalBusy}
                  className="btn-pill text-[13px] py-2 px-5 flex items-center gap-2"
                  style={{ background: "var(--mint-deep)", color: "#fff" }}
                >
                  {approvalBusy ? "Building & Verifying…" : "✓ Approve Spend & Resume ADK Agent"}
                </button>
                <button
                  onClick={handleReject}
                  disabled={approvalBusy}
                  className="pill text-[13px] py-2 px-4 hover:bg-black/5"
                  style={{ color: "var(--coral)" }}
                >
                  ✕ Reject Goal
                </button>
              </div>
            </div>
          )}

          {/* Execution Trace */}
          {result && (
            <div className="space-y-4 pt-1">
              <div className="flex items-center justify-between">
                <div className="font-mono2 text-[11px] font-bold uppercase tracking-wider" style={{ color: "var(--ink-soft)" }}>
                  Agent Execution Trace ({result.tools_called.length} Tools Dispatched)
                </div>
                <span className="pill text-[10.5px] font-mono2" style={{ background: "var(--paper-warm)", color: "var(--ink-soft)" }}>
                  Mode: {result.mode}
                </span>
              </div>

              {/* Tool Steps List */}
              <div className="space-y-2">
                {result.steps.map((s, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border p-3 text-[12px] space-y-1.5"
                    style={{ background: "var(--paper-warm)", borderColor: "var(--hairline)" }}
                  >
                    <div className="flex items-center justify-between font-mono2">
                      <span className="font-bold flex items-center gap-1.5" style={{ color: "var(--charcoal)" }}>
                        <span className="w-5 h-5 rounded-full bg-white flex items-center justify-center text-[10px] shadow-xs">
                          {idx + 1}
                        </span>
                        tool: {s.tool}
                      </span>
                      <span className="text-[10px] text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                        COMPLETED
                      </span>
                    </div>
                    {s.output != null ? (
                      <div className="font-mono2 text-[11px] p-2 rounded bg-white/70 overflow-x-auto text-neutral-800">
                        {JSON.stringify(s.output, null, 2)}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>

              {/* Final Answer / Status */}
              <div
                className="rounded-2xl p-4 border"
                style={{
                  background: result.release_id ? "var(--mint)" : "var(--paper-warm)",
                  borderColor: result.release_id ? "#cbe9a9" : "var(--hairline)",
                }}
              >
                <div className="font-display font-bold text-[13px] mb-1" style={{ color: result.release_id ? "var(--mint-deep)" : "var(--charcoal)" }}>
                  {result.release_id ? "✓ ADK Goal Completed & Release Verified" : "ℹ ADK Agent Status"}
                </div>
                <p className="text-[13px] leading-relaxed" style={{ color: "var(--ink)" }}>
                  {result.final_answer}
                </p>
                {result.release_id && onSyncToMainView && result.change_id && (
                  <div className="pt-3">
                    <button
                      onClick={() => {
                        onSyncToMainView(result.change_id!);
                        onClose();
                      }}
                      className="btn-pill text-[12px] py-1.5 px-4"
                    >
                      Inspect in Slate Compiler View →
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { BuildResult, Estimate, GraphView, SystemStatus } from "./types";
import Stepper from "./components/Stepper";
import StoryGuide from "./components/StoryGuide";
import AskModal from "./components/AskModal";
import AdkModal from "./components/AdkModal";
import StageBrief from "./stages/StageBrief";
import StageScan from "./stages/StageScan";
import StageGraph from "./stages/StageGraph";
import StageApprove from "./stages/StageApprove";
import StageRebuild from "./stages/StageRebuild";
import StageRelease from "./stages/StageRelease";
import {
  buildSlate,
  CAMPAIGNS,
  dirtyAssets,
  SCENARIOS,
  type Scenario,
} from "./data/slate";

export default function App() {
  const slate = useMemo(buildSlate, []);
  const [stage, setStage] = useState(1);
  const [maxUnlocked, setMaxUnlocked] = useState(1);
  const [campaign, setCampaign] = useState<string | null>("aurora");
  const [scenario, setScenario] = useState<Scenario | null>(SCENARIOS[0]);
  const [approved, setApproved] = useState(false);

  // Backend state
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [changeId, setChangeId] = useState<string | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [graphView, setGraphView] = useState<GraphView | null>(null);
  const [buildResult, setBuildResult] = useState<BuildResult | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [askOpen, setAskOpen] = useState(false);
  const [adkOpen, setAdkOpen] = useState(false);
  const [faultMode, setFaultMode] = useState<string>("off");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load system status on mount
  useEffect(() => {
    api.status()
      .then((st) => {
        setSystemStatus(st);
        if (st.fault_injection) setFaultMode(st.fault_injection);
      })
      .catch((err) => console.warn("Status fetch note:", err));
  }, []);

  const activeCampaign = CAMPAIGNS.find((c) => c.id === campaign);
  const effectiveScenario: Scenario = scenario ?? {
    ...SCENARIOS[0],
    id: "custom",
    title: "Custom Change",
    emoji: "📝",
    regulation: undefined,
  };

  const dirtyCount = useMemo(() => {
    if (estimate && estimate.dirty_node_ids.length > 0) {
      return estimate.dirty_node_ids.length;
    }
    return stage >= 2 ? dirtyAssets(effectiveScenario, slate).length : 0;
  }, [stage, estimate, effectiveScenario, slate]);

  const go = (n: number) => {
    setErrorMessage(null);
    setStage(n);
    setMaxUnlocked((m) => Math.max(m, n));
  };

  const reset = () => {
    setStage(1);
    setMaxUnlocked(1);
    setCampaign("aurora");
    setScenario(SCENARIOS[0]);
    setApproved(false);
    setChangeId(null);
    setEstimate(null);
    setGraphView(null);
    setBuildResult(null);
    setErrorMessage(null);
  };

  const handleScan = async (instructionText: string) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      let ch;
      if (scenario?.id === "eu_disclaimer") {
        ch = await api.submitPreset("eu_disclaimer_2026");
      } else {
        ch = await api.submitChange(instructionText);
      }
      setChangeId(ch.change_id);
      go(2);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`Unable to submit change: ${msg}. Check backend connection.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async () => {
    setIsApproving(true);
    setErrorMessage(null);
    try {
      if (changeId) {
        await api.approve(changeId, "producer (simulated)");
      }
      setApproved(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`Approval refused: ${msg}. Gate remains locked.`);
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    if (changeId) {
      api.reject(changeId, "producer (simulated)").catch(() => undefined);
    }
    go(1);
  };

  const toggleFault = async () => {
    const nextMode = faultMode === "off" ? "timeout" : "off";
    setFaultMode(nextMode);
    try {
      await api.setFaultInjection(nextMode);
    } catch (err) {
      console.warn("Fault injection note:", err);
    }
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--paper)" }}>
      {/* ── header ── */}
      <header
        className="hairline-b sticky top-0 z-40"
        style={{ background: "rgba(252,251,250,0.9)", backdropFilter: "blur(10px)" }}
      >
        <div className="max-w-6xl mx-auto px-5 py-3 flex items-center gap-3 flex-wrap">
          <button onClick={reset} className="flex items-center gap-2.5 flex-none text-left">
            <span
              className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-display font-extrabold text-[15px]"
              style={{ background: "var(--coral)" }}
            >
              C
            </span>
            <span className="font-display font-extrabold text-lg tracking-tight">CONFORM</span>
          </button>
          <span className="font-mono2 text-[10.5px] tracking-widest hidden lg:block" style={{ color: "var(--ink-soft)" }}>
            COMPILER FOR GENERATIVE FILM SLATES
          </span>

          {/* System status chips */}
          <div className="hidden sm:flex items-center gap-1.5 font-mono2 text-[10px]">
            <span
              className="pill"
              style={{
                background: systemStatus?.vertex?.startsWith("live") ? "var(--mint)" : "var(--paper-warm)",
                color: systemStatus?.vertex?.startsWith("live") ? "var(--mint-deep)" : "var(--ink-soft)",
              }}
            >
              Vertex: {systemStatus?.vertex ?? "mock"}
            </span>
            <span
              className="pill"
              style={{
                background: systemStatus?.writer?.startsWith("live") ? "var(--mint)" : "var(--paper-warm)",
                color: systemStatus?.writer?.startsWith("live") ? "var(--mint-deep)" : "var(--ink-soft)",
              }}
            >
              ClickHouse: {systemStatus?.writer ?? "sqlite"}
            </span>
            <span
              className="pill cursor-pointer"
              title="Click to toggle transient retry fault injection"
              onClick={toggleFault}
              style={{
                background: faultMode !== "off" ? "var(--coral-soft)" : "var(--paper-warm)",
                color: faultMode !== "off" ? "var(--coral)" : "var(--ink-soft)",
              }}
            >
              Fault: {faultMode}
            </span>
          </div>

          {activeCampaign && (
            <span className="pill hidden md:inline-flex" style={{ background: "var(--beige-soft)", color: "#7a6650" }}>
              🎬 {activeCampaign.title}
            </span>
          )}

          <div className="ml-auto flex items-center gap-2">
            <button
              className="pill font-semibold text-[12px] flex items-center gap-1.5 transition-all hover:opacity-90"
              style={{ background: "var(--charcoal)", color: "#fff" }}
              onClick={() => setAdkOpen(true)}
              title="Google ADK Autonomous Agent Orchestrator"
            >
              <span>🤖</span>
              <span className="hidden sm:inline">ADK Agent</span>
            </button>
            <button
              className="pill font-semibold text-[12px] flex items-center gap-1.5"
              style={{ background: "var(--paper-warm)", color: "var(--charcoal)" }}
              onClick={() => setAskOpen(true)}
            >
              <span>💬</span>
              <span className="hidden sm:inline">Ask Slate</span>
            </button>
            <Stepper current={stage} maxUnlocked={maxUnlocked} onJump={go} />
          </div>
        </div>
      </header>

      {/* ── body ── */}
      <main className="max-w-6xl mx-auto px-5 py-7 space-y-6">
        <StoryGuide step={stage} />

        {errorMessage && (
          <div
            className="rounded-2xl p-4 flex items-center justify-between border"
            style={{ background: "var(--coral-soft)", borderColor: "var(--coral)", color: "var(--coral)" }}
          >
            <div className="flex items-center gap-3 text-sm font-medium">
              <span>⚠</span>
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs font-bold uppercase tracking-wider px-2 py-1 rounded hover:bg-black/5"
            >
              Dismiss
            </button>
          </div>
        )}

        {stage === 1 && (
          <StageBrief
            campaign={campaign}
            setCampaign={setCampaign}
            scenario={scenario}
            setScenario={setScenario}
            isSubmitting={isSubmitting}
            onScan={handleScan}
          />
        )}

        {stage === 2 && (
          <StageScan
            scenario={effectiveScenario}
            slate={slate}
            changeId={changeId}
            onEstimated={(est, g) => {
              setEstimate(est);
              setGraphView(g);
            }}
            onDone={() => go(3)}
          />
        )}

        {stage === 3 && (
          <StageGraph
            scenario={effectiveScenario}
            slate={slate}
            estimate={estimate}
            graphView={graphView}
            onApprove={() => go(4)}
          />
        )}

        {stage === 4 && (
          <StageApprove
            scenario={effectiveScenario}
            dirtyCount={dirtyCount}
            estimate={estimate}
            approved={approved}
            isApproving={isApproving}
            onApprove={handleApprove}
            onReject={handleReject}
            onBuild={() => go(5)}
          />
        )}

        {stage === 5 && (
          <StageRebuild
            scenario={effectiveScenario}
            slate={slate}
            changeId={changeId}
            buildResult={buildResult}
            onBuildCompleted={setBuildResult}
            onDone={() => go(6)}
          />
        )}

        {stage === 6 && (
          <StageRelease
            scenario={effectiveScenario}
            dirtyCount={dirtyCount}
            buildResult={buildResult}
            onOpenAsk={() => setAskOpen(true)}
          />
        )}

        <footer className="pt-6 pb-10 text-center text-[12px]" style={{ color: "var(--ink-soft)" }}>
          CONFORM · surgical rebuilds for generative film slates — live API attached · actor roles simulated
        </footer>
      </main>

      {/* ── Ask the Slate Modal ── */}
      <AskModal isOpen={askOpen} onClose={() => setAskOpen(false)} />

      {/* ── Google ADK Agent Modal ── */}
      <AdkModal
        isOpen={adkOpen}
        onClose={() => setAdkOpen(false)}
        onSyncToMainView={(cid) => {
          setChangeId(cid);
          setApproved(true);
          go(5);
        }}
      />
    </div>
  );
}

import type { Estimate } from "../types";
import type { Scenario } from "../data/slate";

export default function StageApprove({
  scenario,
  dirtyCount,
  estimate,
  approved,
  isApproving = false,
  onApprove,
  onReject,
  onBuild,
}: {
  scenario: Scenario;
  dirtyCount: number;
  estimate?: Estimate | null;
  approved: boolean;
  isApproving?: boolean;
  onApprove: () => void;
  onReject: () => void;
  onBuild: () => void;
}) {
  const cleanCount = 252 - dirtyCount;
  const spendFormatted = estimate?.estimated_cost_usd
    ? `$${Number(estimate.estimated_cost_usd).toFixed(4)}`
    : scenario.spend;
  const naiveSpend = 0.0630;
  const actualSpendNum = estimate?.estimated_cost_usd ? Number(estimate.estimated_cost_usd) : 0.0030;
  const savedPctFormatted = estimate?.estimated_cost_usd
    ? `${((Math.max(0, naiveSpend - actualSpendNum) / naiveSpend) * 100).toFixed(1)}%`
    : scenario.savedPct;

  return (
    <div className="stage-enter max-w-3xl mx-auto">
      {/* gate card */}
      <div className="surface overflow-hidden">
        <div
          className="px-7 py-5 flex items-center justify-between"
          style={{ background: approved ? "var(--mint)" : "var(--amber-soft)" }}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">{approved ? "✅" : "🛑"}</span>
            <div>
              <div className="font-display font-bold text-lg leading-none">
                {approved ? "Approved by Producer" : "Awaiting Human Approval"}
              </div>
              <div className="text-[12.5px] mt-1" style={{ color: approved ? "var(--mint-deep)" : "#96690f" }}>
                {approved
                  ? "producer (simulated) · just now"
                  : "The build is locked until a human signs off."}
              </div>
            </div>
          </div>
          <span
            className="pill"
            style={{
              background: approved ? "#fff" : "#fff",
              color: approved ? "var(--mint-deep)" : "#96690f",
            }}
          >
            <span className={`dot ${approved ? "" : "dot-pulse"}`} style={{ background: approved ? "var(--mint-deep)" : "var(--amber)", color: "var(--amber)" }} />
            {approved ? "GATE OPEN" : "GATE CLOSED"}
          </span>
        </div>

        <div className="p-7">
          <div className="font-mono2 text-[10.5px] tracking-widest mb-3" style={{ color: "var(--ink-soft)" }}>
            REBUILD QUOTE · {scenario.emoji} {scenario.title.toUpperCase()}
          </div>

          {/* bill comparison */}
          <div className="grid sm:grid-cols-3 gap-4">
            <div className="rounded-2xl p-5" style={{ background: "var(--coral-soft)" }}>
              <div className="text-[12px] font-semibold" style={{ color: "var(--coral)" }}>You pay</div>
              <div className="font-mono2 font-bold text-3xl mt-1" style={{ color: "var(--coral)" }}>{spendFormatted}</div>
              <div className="text-[12px] mt-1" style={{ color: "var(--coral)" }}>{dirtyCount} dirty assets rebuilt</div>
            </div>
            <div className="rounded-2xl p-5" style={{ background: "var(--paper-warm)" }}>
              <div className="text-[12px] font-semibold" style={{ color: "var(--ink-soft)" }}>Naive regen would cost</div>
              <div className="font-mono2 font-bold text-3xl mt-1 line-through" style={{ color: "var(--ink-soft)" }}>
                {scenario.naiveSpend}
              </div>
              <div className="text-[12px] mt-1" style={{ color: "var(--ink-soft)" }}>all 252 assets, blindly</div>
            </div>
            <div className="rounded-2xl p-5" style={{ background: "var(--mint)" }}>
              <div className="text-[12px] font-semibold" style={{ color: "var(--mint-deep)" }}>Avoided spend</div>
              <div className="font-mono2 font-bold text-3xl mt-1" style={{ color: "var(--mint-deep)" }}>{savedPctFormatted}</div>
              <div className="text-[12px] mt-1" style={{ color: "var(--mint-deep)" }}>{cleanCount} reused byte-exact · $0.00</div>
            </div>
          </div>

          <p className="text-[13px] mt-5 leading-relaxed" style={{ color: "var(--ink-soft)" }}>
            🔒 <b>Invariant:</b> no generative model (Veo, Imagen, Gemini, Chirp, Lyria) can be invoked before this gate
            is signed. The quote above is computed deterministically from the blast radius — it will not drift.
          </p>

          <div className="flex flex-wrap gap-3 mt-6">
            {!approved ? (
              <>
                <button className="btn-pill btn-mint" onClick={onApprove} disabled={isApproving}>
                  {isApproving ? "Approving…" : `✓ Approve spend (${spendFormatted})`}
                </button>
                <button className="btn-ghost" onClick={onReject} disabled={isApproving}>
                  Reject — back to brief
                </button>
              </>
            ) : (
              <button className="btn-pill btn-coral" onClick={onBuild} style={{ animation: "dotPulse 1.6s infinite" }}>
                🚀 Build dirty subtree ({dirtyCount} assets) →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

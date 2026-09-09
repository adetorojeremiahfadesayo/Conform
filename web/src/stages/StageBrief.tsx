import { useState } from "react";
import { CAMPAIGNS, SCENARIOS, type Scenario } from "../data/slate";

const CARD_TINTS = ["#f3f1ee", "#e7fec7", "#eaf3f8"];

export default function StageBrief({
  campaign,
  setCampaign,
  scenario,
  setScenario,
  onScan,
  isSubmitting = false,
  judgeMode = false,
}: {
  campaign: string | null;
  setCampaign: (id: string) => void;
  scenario: Scenario | null;
  setScenario: (s: Scenario | null) => void;
  onScan: (instruction: string) => void;
  isSubmitting?: boolean;
  judgeMode?: boolean;
}) {
  const [custom, setCustom] = useState("");
  const ready = campaign !== null && (scenario !== null || custom.trim().length > 4);

  return (
    <div className="stage-enter space-y-8">
      {/* ── campaign picker ── */}
      <section>
        <SectionHead n="1" title="Choose the campaign" sub="The master slate your change will ripple through" />
        <div className="grid md:grid-cols-3 gap-4">
          {CAMPAIGNS.map((c, i) => {
            const sel = campaign === c.id;
            return (
              <button
                key={c.id}
                onClick={() => !judgeMode && setCampaign(c.id)}
                disabled={judgeMode && c.id !== "aurora"}
                className="card-hover text-left rounded-2xl p-5 border transition-all"
                style={{
                  background: CARD_TINTS[i],
                  borderColor: sel ? "var(--charcoal)" : "transparent",
                  borderWidth: 2,
                  boxShadow: sel ? "0 0 0 3px rgba(43,41,38,.15)" : undefined,
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono2 text-[11px] font-medium px-2 py-0.5 rounded-full bg-white/70" style={{ color: "var(--ink-soft)" }}>
                    SLATE {c.slate}
                  </span>
                  {sel && (
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs" style={{ background: "var(--charcoal)" }}>
                      ✓
                    </span>
                  )}
                </div>
                <div className="font-display font-bold text-lg mt-3 leading-snug">{c.title}</div>
                <div className="text-[13px] mt-1" style={{ color: "var(--ink-soft)" }}>
                  {c.assets} assets · 40 territory variants
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* ── scenario picker ── */}
      <section>
        <SectionHead n="2" title="What changed?" sub="Pick a production note, or write your own" />
        <div className="grid md:grid-cols-3 gap-4">
          {SCENARIOS.filter((s) => !judgeMode || s.id === "eu-reg").map((s) => {
            const sel = scenario?.id === s.id;
            return (
              <button
                key={s.id}
                onClick={() => {
                  setScenario(s);
                  setCustom("");
                }}
                className="card-hover surface text-left p-5 transition-all"
                style={{
                  borderColor: sel ? "var(--coral)" : "var(--hairline)",
                  borderWidth: 2,
                  boxShadow: sel ? "0 0 0 3px var(--coral-soft)" : undefined,
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-2xl">{s.emoji}</span>
                  {sel && (
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs" style={{ background: "var(--coral)" }}>
                      ✓
                    </span>
                  )}
                </div>
                <div className="font-display font-bold text-[16px] mt-2">{s.title}</div>
                <div className="text-[13px] mt-1" style={{ color: "var(--ink-soft)" }}>
                  {s.short}
                </div>
              </button>
            );
          })}
        </div>

        {/* instruction sheet — the "change order" */}
        <div className="surface mt-5 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="font-mono2 text-[11px] font-semibold tracking-widest" style={{ color: "var(--ink-soft)" }}>
              CHANGE ORDER
            </span>
            {scenario?.regulation && (
              <span className="pill" style={{ background: "var(--amber-soft)", color: "#96690f" }}>
                <span className="dot" style={{ background: "var(--amber)" }} />
                {scenario.regulation}
              </span>
            )}
          </div>
          <textarea
            value={scenario ? scenario.instruction : custom}
            readOnly={judgeMode}
            onChange={(e) => {
              setCustom(e.target.value);
              if (scenario) setScenario(null);
            }}
            placeholder="Or type a custom change order, e.g. “Swap the end-card CTA in the Spanish markets to the new summer offer…”"
            rows={3}
            className="w-full resize-none rounded-xl border p-4 text-[14.5px] leading-relaxed outline-none transition-colors"
            style={{ borderColor: "var(--hairline)", background: "var(--paper)", fontFamily: "inherit" }}
            onFocus={(e) => (e.currentTarget.style.borderColor = "var(--charcoal)")}
            onBlur={(e) => (e.currentTarget.style.borderColor = "var(--hairline)")}
          />
          {judgeMode && <p className="text-[12px] mt-2" style={{ color: "var(--ink-soft)" }}>
            Public Judge Mode uses this prepared cached scenario. Custom changes are intentionally unavailable.
          </p>}
        </div>
      </section>

      {/* ── CTA ── */}
      <div className="flex items-center justify-between flex-wrap gap-4 pt-2">
        <div className="text-[13.5px]" style={{ color: "var(--ink-soft)" }}>
          {ready
            ? "Ready — click Roll camera to scan the slate and isolate the blast radius."
            : "Select a campaign and a change to continue."}
        </div>
        <button
          className="btn-pill"
          disabled={!ready || isSubmitting}
          onClick={() => onScan(scenario ? scenario.instruction : custom)}
          style={{ paddingLeft: "1.75rem", paddingRight: "1.75rem" }}
        >
          {isSubmitting ? "🎬 Rolling camera: scanning slate…" : "🎬 Roll camera: scan the slate →"}
        </button>
      </div>
    </div>
  );
}

export function SectionHead({ n, title, sub }: { n: string; title: string; sub: string }) {
  return (
    <div className="flex items-baseline gap-3 mb-4">
      <span
        className="font-mono2 text-[11px] font-bold w-6 h-6 rounded-full flex-none flex items-center justify-center text-white translate-y-[3px]"
        style={{ background: "var(--charcoal)" }}
      >
        {n}
      </span>
      <div>
        <h2 className="font-display font-bold text-xl leading-none">{title}</h2>
        <p className="text-[13px] mt-1" style={{ color: "var(--ink-soft)" }}>
          {sub}
        </p>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { BuildResult } from "../types";
import { dirtyAssets, fingerprint, type Scenario, type SlateNode } from "../data/slate";

const AGENT_LINES = [
  "Checking content hash against cache…",
  "Cache miss confirmed — scheduling rebuild",
  "Calling Vertex AI model endpoint…",
  "Streaming generation…",
  "Writing artifact to storage",
  "Re-hashing output (SHA-256)…",
  "Sealing into release manifest",
];

export default function StageRebuild({
  scenario,
  slate,
  changeId,
  buildResult,
  onBuildCompleted,
  onDone,
}: {
  scenario: Scenario;
  slate: SlateNode[];
  changeId?: string | null;
  buildResult?: BuildResult | null;
  onBuildCompleted?: (result: BuildResult) => void;
  onDone: () => void;
}) {
  const assets = useMemo(() => dirtyAssets(scenario, slate).slice(0, 12), [scenario, slate]);
  const total = assets.length;

  // current = index being built; everything below is done, above is queued
  const [current, setCurrent] = useState(-1);
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState<string[]>([]);
  const [showSuccess, setShowSuccess] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  const doneCount = Math.min(Math.max(current, 0), total);
  const finished = current >= total;

  const pushLog = (s: string) => setLog((l) => [...l.slice(-60), s]);

  // Trigger backend build when mounted
  useEffect(() => {
    if (!changeId || buildResult) return;
    api.build(changeId)
      .then((res) => {
        onBuildCompleted?.(res);
        pushLog(`✔ Build complete! Release ${res.release?.release_id ?? "sealed"} (${res.nodes_rebuilt} rebuilt, ${res.nodes_reused} reused)`);
      })
      .catch((err) => {
        console.warn("Backend build note:", err);
      });
  }, [changeId, buildResult, onBuildCompleted]);

  // kick off
  useEffect(() => {
    const t = setTimeout(() => setCurrent(0), 700);
    return () => clearTimeout(t);
  }, []);

  // build engine: one asset at a time, all timers cleaned per step
  useEffect(() => {
    if (current < 0) return;
    if (current >= total) {
      pushLog("✔ All dirty assets rebuilt. Release manifest sealed.");
      const t = setTimeout(() => setShowSuccess(true), 900);
      return () => clearTimeout(t);
    }
    const a = assets[current];
    pushLog(`▶ ${a.id} — rebuild started${a.model ? ` (${a.model})` : ""}`);
    setProgress(0);

    let p = 0;
    const tick = setInterval(() => {
      p = Math.min(100, p + 8 + Math.random() * 14);
      setProgress(Math.round(p));
    }, 160);

    let li = 0;
    const lineTimer = setInterval(() => {
      if (li < AGENT_LINES.length) pushLog(`   ${AGENT_LINES[li++]}`);
    }, 260);

    const dur = setTimeout(
      () => {
        pushLog(`✔ ${a.id} sealed · sha256 ${fingerprint(a.id).slice(0, 12)}…`);
        setCurrent((c) => c + 1);
      },
      1400 + Math.random() * 800
    );

    return () => {
      clearInterval(tick);
      clearInterval(lineTimer);
      clearTimeout(dur);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, total]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [log]);

  return (
    <div className="stage-enter">
      <div className="grid lg:grid-cols-[340px_1fr] gap-5">
        {/* ── agent worker panel ── */}
        <div className="surface p-6">
          <div className="flex items-center gap-4">
            <div className="relative w-16 h-16 flex-none">
              <div
                className="absolute inset-0 rounded-full flex items-center justify-center text-2xl text-white"
                style={{ background: "var(--charcoal)" }}
              >
                🤖
              </div>
              {!finished && current >= 0 && (
                <span
                  className="orbit-dot absolute left-1/2 top-1/2 w-3 h-3 -ml-1.5 -mt-1.5 rounded-full"
                  style={{ background: "var(--coral)" }}
                />
              )}
            </div>
            <div>
              <div className="font-display font-bold text-lg leading-tight">
                {finished ? "Rebuild complete" : current < 0 ? "Agent warming up…" : "Agent rebuilding…"}
              </div>
              <div className="text-[13px]" style={{ color: "var(--ink-soft)" }}>
                {doneCount} / {total} assets · {252 - total} reused from cache
              </div>
            </div>
          </div>

          {/* overall progress */}
          <div className="mt-6">
            <div className="flex justify-between text-[12px] font-semibold mb-1.5">
              <span style={{ color: "var(--ink-soft)" }}>DIRTY SUBTREE</span>
              <span className="font-mono2">{Math.round((doneCount / total) * 100)}%</span>
            </div>
            <div className="h-3 rounded-full overflow-hidden" style={{ background: "var(--paper-warm)" }}>
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${(doneCount / total) * 100}%`, background: "var(--mint-deep)" }}
              />
            </div>
          </div>

          {/* agent log */}
          <div
            className="mt-5 rounded-xl p-3 font-mono2 text-[11px] leading-relaxed overflow-y-auto"
            ref={logRef}
            style={{ background: "var(--charcoal)", color: "#d8f3c0", height: 300 }}
          >
            <div style={{ color: "#8fa382" }}>$ conform build --change {scenario.id} --approved</div>
            {log.map((l, i) => (
              <div key={i} className="rise-in">
                {l}
              </div>
            ))}
            {!finished && <span className="caret">▌</span>}
          </div>
        </div>

        {/* ── asset cards ── */}
        <div className="grid sm:grid-cols-2 gap-3 content-start">
          {assets.map((a, i) => {
            const st = i < current ? "done" : i === current ? "building" : "queued";
            return (
              <div
                key={a.id}
                className="surface p-4 transition-all"
                style={{
                  borderColor:
                    st === "building" ? "var(--coral)" : st === "done" ? "var(--mint-deep)" : "var(--hairline)",
                  borderWidth: st === "queued" ? 1 : 2,
                  opacity: st === "queued" ? 0.6 : 1,
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-semibold text-[14px] truncate">{a.label}</div>
                    <div className="font-mono2 text-[10.5px]" style={{ color: "var(--ink-soft)" }}>
                      {a.id}
                      {a.model ? ` · ${a.model}` : ""}
                    </div>
                  </div>
                  {st === "queued" && (
                    <span className="pill" style={{ background: "var(--paper-warm)", color: "var(--ink-soft)" }}>
                      queued
                    </span>
                  )}
                  {st === "building" && (
                    <span className="pill" style={{ background: "var(--coral-soft)", color: "var(--coral)" }}>
                      <span
                        className="w-3 h-3 rounded-full border-2 spin-slow inline-block"
                        style={{ borderColor: "var(--coral)", borderTopColor: "transparent" }}
                      />
                      building
                    </span>
                  )}
                  {st === "done" && (
                    <span className="pill" style={{ background: "var(--mint)", color: "var(--mint-deep)" }}>
                      ✓ sealed
                    </span>
                  )}
                </div>
                {st === "building" && (
                  <div className="mt-3 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--coral-soft)" }}>
                    <div className="h-full progress-shimmer rounded-full" style={{ width: `${progress}%` }} />
                  </div>
                )}
                {st === "done" && (
                  <div className="mt-2 font-mono2 text-[10px] break-all" style={{ color: "var(--mint-deep)" }}>
                    sha256 {fingerprint(a.id).slice(0, 24)}…
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {showSuccess && (
        <SuccessPopup
          scenario={scenario}
          dirtyCount={total}
          buildResult={buildResult}
          onContinue={() => {
            setShowSuccess(false);
            onDone();
          }}
        />
      )}
    </div>
  );
}

function SuccessPopup({
  scenario,
  dirtyCount,
  buildResult,
  onContinue,
}: {
  scenario: Scenario;
  dirtyCount: number;
  buildResult?: BuildResult | null;
  onContinue: () => void;
}) {
  const actualRebuilt = buildResult ? buildResult.nodes_rebuilt : dirtyCount;
  const actualReused = buildResult ? buildResult.nodes_reused : 252 - dirtyCount;
  const actualBilled = buildResult?.total_cost_usd
    ? `$${Number(buildResult.total_cost_usd).toFixed(4)}`
    : scenario.spend;

  const confetti = useMemo(
    () =>
      Array.from({ length: 60 }, (_, i) => ({
        left: Math.random() * 100,
        delay: Math.random() * 2.4,
        dur: 2.6 + Math.random() * 2.2,
        size: 6 + Math.random() * 8,
        color: ["#ea4467", "#e7fec7", "#c6b3a2", "#bcd8e8", "#e8a13a", "#2b2926"][i % 6],
        round: Math.random() > 0.6,
      })),
    []
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overlay-in"
      style={{ background: "rgba(43,41,38,0.45)", backdropFilter: "blur(4px)" }}
    >
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {confetti.map((c, i) => (
          <span
            key={i}
            className="confetti-piece"
            style={{
              left: `${c.left}%`,
              width: c.size,
              height: c.round ? c.size : c.size * 0.5,
              background: c.color,
              borderRadius: c.round ? "50%" : 2,
              animationDuration: `${c.dur}s`,
              animationDelay: `${c.delay}s`,
            }}
          />
        ))}
      </div>

      <div className="surface pop-in relative max-w-md w-[92%] p-8 text-center" style={{ borderRadius: 28 }}>
        <div className="mx-auto w-20 h-20 rounded-full flex items-center justify-center" style={{ background: "var(--mint)" }}>
          <svg viewBox="0 0 52 52" className="w-11 h-11">
            <path
              className="check-draw"
              d="M12 27 L22 37 L40 16"
              fill="none"
              stroke="var(--mint-deep)"
              strokeWidth={5}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <h3 className="font-display font-bold text-2xl mt-4">That's a wrap! 🎬</h3>
        <p className="text-[14px] mt-2 leading-relaxed" style={{ color: "var(--ink-soft)" }}>
          The dirty subtree was rebuilt and sealed. Every clean asset was reused byte-for-byte — zero wasted compute.
        </p>
        <div className="grid grid-cols-3 gap-2 mt-5">
          <StatPill v={String(actualRebuilt)} l="rebuilt" c="var(--coral)" />
          <StatPill v={String(actualReused)} l="reused · $0.00" c="var(--mint-deep)" />
          <StatPill v={scenario.savedPct} l="spend avoided" c="var(--mint-deep)" />
        </div>
        <div
          className="font-mono2 text-[12px] mt-4 rounded-xl py-2"
          style={{ background: "var(--paper-warm)", color: "var(--ink-soft)" }}
        >
          billed {actualBilled} · naive would be {scenario.naiveSpend}
        </div>
        <button className="btn-pill w-full justify-center mt-5" onClick={onContinue}>
          Verify the release →
        </button>
      </div>
    </div>
  );
}

function StatPill({ v, l, c }: { v: string; l: string; c: string }) {
  return (
    <div className="rounded-xl py-3 px-1" style={{ background: "var(--paper-warm)" }}>
      <div className="font-mono2 font-bold text-lg" style={{ color: c }}>{v}</div>
      <div className="text-[11px] font-medium" style={{ color: "var(--ink-soft)" }}>{l}</div>
    </div>
  );
}

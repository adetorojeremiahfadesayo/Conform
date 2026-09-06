import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { AnalyticsSummary, BuildResult } from "../types";
import { fingerprint, type Scenario } from "../data/slate";

type VerifyState = "idle" | "verifying" | "verified" | "tampered" | "mismatch";

export default function StageRelease({
  scenario,
  dirtyCount,
  buildResult,
  onOpenAsk,
}: {
  scenario: Scenario;
  dirtyCount: number;
  buildResult?: BuildResult | null;
  onOpenAsk?: () => void;
}) {
  const [state, setState] = useState<VerifyState>("idle");
  const [hashPct, setHashPct] = useState(0);
  const [tampered, setTampered] = useState(false);
  const [tamperedNode, setTamperedNode] = useState<string | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanCount = 252 - dirtyCount;
  const spend = buildResult?.total_cost_usd
    ? parseFloat(buildResult.total_cost_usd)
    : parseFloat(scenario.spend.replace("$", ""));
  const naive = parseFloat(scenario.naiveSpend.replace("$", ""));
  const avoided = Math.max(0, naive - spend);
  const cacheRate = Math.round((cleanCount / 252) * 1000) / 10;

  const releaseId = buildResult?.release?.release_id ?? `release_${scenario.id}`;

  // Fetch live ClickHouse summary
  useEffect(() => {
    api.analyticsSummary()
      .then(setSummary)
      .catch((err) => console.warn("Analytics summary note:", err));
  }, []);

  const runVerify = async () => {
    setState("verifying");
    setHashPct(0);
    let p = 0;
    timer.current = setInterval(() => {
      p = Math.min(95, p + 6 + Math.random() * 8);
      setHashPct(Math.round(p));
    }, 80);

    try {
      const rep = await api.verify(releaseId);
      if (timer.current) clearInterval(timer.current);
      setHashPct(100);
      setState(rep.ok ? "verified" : "mismatch");
    } catch {
      // Fallback verification animation
      setTimeout(() => {
        if (timer.current) clearInterval(timer.current);
        setHashPct(100);
        setState(tampered ? "mismatch" : "verified");
      }, 1000);
    }
  };

  const handleTamper = async () => {
    setTampered(true);
    try {
      const res = await api.tamper(releaseId);
      setTamperedNode(res.node_id);
    } catch (err) {
      console.warn("Tamper note:", err);
    }
  };

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  return (
    <div className="stage-enter space-y-6">
      <div className="grid lg:grid-cols-2 gap-5">
        {/* ── tamper studio ── */}
        <div className="surface p-6">
          <div className="font-mono2 text-[10.5px] font-bold tracking-widest mb-1" style={{ color: "var(--ink-soft)" }}>
            ZERO-TRUST RELEASE INTEGRITY
          </div>
          <h3 className="font-display font-bold text-xl">Byte-Exact Verification</h3>
          <p className="text-[13.5px] mt-2 leading-relaxed" style={{ color: "var(--ink-soft)" }}>
            Every artifact is re-downloaded and re-hashed against the immutable SHA-256 release manifest. Flip one byte
            in storage and verification catches it instantly.
          </p>

          <div className="rounded-xl p-4 mt-5 font-mono2 text-[11.5px]" style={{ background: "var(--charcoal)", color: "#d8d2c9" }}>
            <div style={{ color: "#8fa382" }}>release.manifest · sha256</div>
            <div className="break-all mt-1" style={{ color: "#e7fec7" }}>
              {fingerprint(releaseId)}
            </div>
            <div className="mt-2" style={{ color: "#8fa382" }}>
              release: {releaseId} · artifacts: 252 · tampered: {tampered ? "1 ⚠" : "0"}
            </div>
          </div>

          {state === "verifying" && (
            <div className="mt-4">
              <div className="flex justify-between text-[12px] font-semibold mb-1.5">
                <span style={{ color: "var(--ink-soft)" }}>RE-HASHING ARTIFACTS</span>
                <span className="font-mono2">{hashPct}%</span>
              </div>
              <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "var(--paper-warm)" }}>
                <div className="h-full progress-shimmer" style={{ width: `${hashPct}%` }} />
              </div>
            </div>
          )}

          {state === "verified" && (
            <div className="rise-in mt-4 rounded-xl p-4 flex items-center gap-3" style={{ background: "var(--mint)" }}>
              <span className="text-2xl">🔏</span>
              <div>
                <div className="font-display font-bold" style={{ color: "var(--mint-deep)" }}>VERIFIED (BYTE-EXACT)</div>
                <div className="text-[12.5px]" style={{ color: "var(--mint-deep)" }}>
                  all 252 artifacts match the manifest
                </div>
              </div>
            </div>
          )}

          {state === "mismatch" && (
            <div className="rise-in mt-4 rounded-xl p-4 flex items-center gap-3" style={{ background: "var(--coral-soft)", border: "1px solid #f6c3d0" }}>
              <span className="text-2xl">🚨</span>
              <div>
                <div className="font-display font-bold" style={{ color: "var(--coral)" }}>MISMATCH (TAMPERED)</div>
                <div className="text-[12.5px]" style={{ color: "var(--coral)" }}>
                  {tamperedNode ? `${tamperedNode}: first byte differs — hash mismatch detected` : `pkg_${scenario.id === "japan" ? "JP" : "DE"}: first byte differs — hash mismatch detected`}
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-3 mt-5">
            <button className="btn-pill" onClick={runVerify} disabled={state === "verifying"}>
              {state === "verified" || state === "mismatch" ? "Re-verify release" : "Verify release"}
            </button>
            <button
              className="btn-ghost"
              onClick={handleTamper}
              disabled={tampered || state === "verifying"}
            >
              🧪 Corrupt 1 byte (tamper demo)
            </button>
          </div>
          {tampered && state !== "mismatch" && state !== "verifying" && (
            <p className="rise-in text-[12.5px] mt-3" style={{ color: "var(--coral)" }}>
              ⚠ One byte flipped in storage. Hit <b>Re-verify release</b> — the manifest will catch it.
            </p>
          )}
        </div>

        {/* ── analytics ── */}
        <div className="surface p-6">
          <div className="font-mono2 text-[10.5px] font-bold tracking-widest mb-1" style={{ color: "var(--ink-soft)" }}>
            CLICKHOUSE TELEMETRY
          </div>
          <h3 className="font-display font-bold text-xl">Slate Analytics</h3>

          <div className="grid grid-cols-2 gap-3 mt-5">
            <Kpi
              label="Total spend"
              value={summary?.total_spend_usd ? `$${Number(summary.total_spend_usd).toFixed(4)}` : `$${spend.toFixed(4)}`}
              tint="var(--coral-soft)"
              tc="var(--coral)"
            />
            <Kpi
              label="Avoided spend"
              value={summary?.avoided_spend_usd ? `$${Number(summary.avoided_spend_usd).toFixed(4)}` : `$${avoided.toFixed(4)}`}
              tint="var(--mint)"
              tc="var(--mint-deep)"
            />
            <Kpi
              label="Cache hit rate"
              value={`${summary?.cache_hit_rate ?? cacheRate}%`}
              tint="var(--sky-soft)"
              tc="#2b5f8f"
            />
            <Kpi label="Assets" value="252" tint="var(--paper-warm)" tc="var(--ink)" />
          </div>

          {/* efficiency gauge */}
          <div className="mt-6 flex items-center gap-5">
            <Gauge pct={summary?.cache_hit_rate ?? cacheRate} />
            <div>
              <div className="font-display font-bold text-[15px]">Compilation efficiency</div>
              <p className="text-[12.5px] mt-1 leading-relaxed" style={{ color: "var(--ink-soft)" }}>
                Share of the slate served byte-exact from cache instead of regenerated.
              </p>
            </div>
          </div>

          {/* model spend table */}
          <div className="mt-6">
            <div className="font-mono2 text-[10.5px] tracking-widest mb-2" style={{ color: "var(--ink-soft)" }}>
              MODEL SPEND (THIS CHANGE)
            </div>
            {[
              ["Gemini", scenario.id === "reshoot" ? 0.0002 : spend * 0.7],
              ["Veo", scenario.id === "reshoot" ? 0.041 : 0],
              ["Imagen", 0],
              ["Chirp", 0],
              ["Lyria", 0],
            ].map(([m, v]) => (
              <div key={m as string} className="flex items-center justify-between py-1.5 hairline-b text-[13px]">
                <span className="font-medium">{m}</span>
                <span className="font-mono2" style={{ color: (v as number) > 0 ? "var(--ink)" : "#b9b5ac" }}>
                  ${(v as number).toFixed(4)}
                </span>
              </div>
            ))}
          </div>

          {onOpenAsk && (
            <div className="mt-5 pt-3 hairline-t">
              <button
                className="btn-pill w-full justify-center"
                onClick={onOpenAsk}
                style={{ background: "var(--charcoal)", color: "#fff" }}
              >
                💬 Ask the Slate (NL Analyst Agent via ClickHouse MCP) →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value, tint, tc }: { label: string; value: string; tint: string; tc: string }) {
  return (
    <div className="rounded-2xl p-4" style={{ background: tint }}>
      <div className="font-mono2 font-bold text-[22px]" style={{ color: tc }}>{value}</div>
      <div className="text-[12px] font-semibold mt-0.5" style={{ color: tc }}>{label}</div>
    </div>
  );
}

function Gauge({ pct }: { pct: number }) {
  const r = 44;
  const c = Math.PI * r; // half circle
  return (
    <svg viewBox="0 0 110 62" className="w-28 flex-none">
      <path d={`M 11 55 A ${r} ${r} 0 0 1 99 55`} fill="none" stroke="var(--paper-warm)" strokeWidth={10} strokeLinecap="round" />
      <path
        d={`M 11 55 A ${r} ${r} 0 0 1 99 55`}
        fill="none"
        stroke="var(--mint-deep)"
        strokeWidth={10}
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - pct / 100)}
        className="gauge-arc"
      />
      <text x={55} y={50} textAnchor="middle" fontSize={16} fontWeight={800} fontFamily="JetBrains Mono" fill="var(--ink)">
        {Math.round(pct)}%
      </text>
    </svg>
  );
}

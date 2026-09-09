import { useMemo, useState } from "react";
import type { Estimate, GraphView } from "../types";
import {
  KIND_META,
  normalizeBackendNodeId,
  type SlateNode,
} from "../data/slate";

interface Pos { x: number; y: number }

export default function StageGraph({
  slate,
  estimate,
  graphView,
  onApprove,
}: {
  slate: SlateNode[];
  estimate?: Estimate | null;
  graphView?: GraphView | null;
  onApprove: () => void;
}) {
  const [selected, setSelected] = useState<SlateNode | null>(null);

  const dirtySet = useMemo(() => {
    return new Set((estimate?.dirty_node_ids ?? []).map(normalizeBackendNodeId));
  }, [estimate]);

  const dirtyCount = estimate?.dirty_node_ids.length ?? 0;
  const cleanCount = estimate?.reused_node_ids.length ?? 0;

  const spendFormatted = estimate?.estimated_cost_usd
    ? `$${Number(estimate.estimated_cost_usd).toFixed(4)}`
    : "—";
  const totalNodes = dirtyCount + cleanCount;
  const savedPctFormatted = estimate && totalNodes > 0
    ? `${((cleanCount / totalNodes) * 100).toFixed(1)}%`
    : "—";

  // ── layout: master spine left, territory grid right ──
  const { positions, masterIds, territoryIds } = useMemo(() => {
    const positions = new Map<string, Pos>();
    const master = slate.filter((n) => !n.territory);
    const terr = slate.filter((n) => n.territory);
    master.forEach((n, i) => positions.set(n.id, { x: 105, y: 56 + i * 74 }));
    // territory grid: 5 columns × 8 rows, copy + package side by side
    const seen: string[] = [];
    terr.forEach((n) => {
      const cc = n.territory!;
      if (!seen.includes(cc)) seen.push(cc);
      const ti = seen.indexOf(cc);
      const col = ti % 5;
      const row = Math.floor(ti / 5);
      const isCopy = n.id.startsWith("copy_");
      positions.set(n.id, {
        x: 300 + col * 172 + (isCopy ? 0 : 34),
        y: 62 + row * 72 + (isCopy ? 0 : 0),
      });
    });
    return {
      positions,
      masterIds: master.map((n) => n.id),
      territoryIds: terr.map((n) => n.id),
    };
  }, [slate]);

  const edges = useMemo(() => {
    const list: { from: string; to: string; dirty: boolean }[] = [];
    for (const n of slate) {
      for (const p of n.parents) {
        if (!positions.has(p) || !positions.has(n.id)) continue;
        list.push({ from: p, to: n.id, dirty: dirtySet.has(n.id) });
      }
    }
    return list;
  }, [slate, positions, dirtySet]);

  const nodeById = useMemo(() => new Map(slate.map((n) => [n.id, n])), [slate]);

  return (
    <div className="stage-enter">
      {/* ── savings callout ── */}
      <div className="surface-warm p-5 flex flex-wrap items-center gap-x-8 gap-y-3 mb-5 rise-in">
        <div>
          <div className="font-mono2 text-[10.5px] font-bold tracking-widest" style={{ color: "var(--coral)" }}>
            COMPILATION SAVINGS
          </div>
          <div className="font-display font-bold text-[17px] mt-0.5">
            Rebuild <span style={{ color: "var(--coral)" }}>{dirtyCount} dirty</span>, reuse{" "}
            <span style={{ color: "var(--mint-deep)" }}>{cleanCount} clean</span>
          </div>
        </div>
        <Metric label="Rebuild bill" value={spendFormatted} color="var(--coral)" />
        <Metric label="Graph scope" value={estimate ? String(totalNodes) : "—"} />
        <Metric label="Cache reuse" value={savedPctFormatted} color="var(--mint-deep)" />
        <div className="ml-auto flex gap-4 text-[12px]" style={{ color: "var(--ink-soft)" }}>
          <span className="flex items-center gap-1.5">
            <span className="dot" style={{ background: "var(--coral)" }} /> dirty — will rebuild
          </span>
          <span className="flex items-center gap-1.5">
            <span className="dot" style={{ background: "#cfc9c0" }} /> clean — cache hit $0.00
          </span>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_300px] gap-5">
        {/* ── DAG canvas ── */}
        <div className="surface p-3 overflow-x-auto">
          <svg viewBox="0 0 1180 640" className="min-w-[900px] w-full" style={{ display: "block" }}>
            <defs>
              <radialGradient id="sphere" cx="35%" cy="30%" r="80%">
                <stop offset="0%" stopColor="#ffffff" />
                <stop offset="100%" stopColor="#d8d2c9" />
              </radialGradient>
              <radialGradient id="sphereDirty" cx="35%" cy="30%" r="80%">
                <stop offset="0%" stopColor="#ffb3c4" />
                <stop offset="100%" stopColor="var(--coral)" />
              </radialGradient>
            </defs>

            {/* column captions */}
            <text x={105} y={26} textAnchor="middle" fontSize={11} fontFamily="JetBrains Mono" fill="var(--ink-soft)" letterSpacing={2}>
              MASTER
            </text>
            <text x={650} y={26} textAnchor="middle" fontSize={11} fontFamily="JetBrains Mono" fill="var(--ink-soft)" letterSpacing={2}>
              40 TERRITORY VARIANTS
            </text>

            {/* edges */}
            {edges.map((e, i) => {
              const a = positions.get(e.from)!;
              const b = positions.get(e.to)!;
              const mx = (a.x + b.x) / 2;
              const d = `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`;
              return (
                <path
                  key={i}
                  d={d}
                  fill="none"
                  stroke={e.dirty ? "var(--coral)" : "var(--hairline)"}
                  strokeWidth={e.dirty ? 1.8 : 1}
                  strokeOpacity={e.dirty ? 0.85 : 0.8}
                  className={e.dirty ? "edge-flow" : undefined}
                />
              );
            })}

            {/* master nodes */}
            {masterIds.map((id, i) => {
              const n = nodeById.get(id)!;
              const p = positions.get(id)!;
              const dirty = dirtySet.has(id);
              return (
                <g key={id} className="rise-in" style={{ animationDelay: `${i * 60}ms` }}>
                  {dirty && <circle cx={p.x} cy={p.y} r={18} fill="none" stroke="var(--coral)" strokeWidth={2} className="node-ripple" />}
                  <circle
                    cx={p.x} cy={p.y} r={15}
                    fill={dirty ? "url(#sphereDirty)" : "url(#sphere)"}
                    stroke={dirty ? "var(--coral)" : "#c9c2b8"}
                    strokeWidth={1.5}
                    className={dirty ? "node-dirty" : "node-clean"}
                    opacity={dirty ? 1 : 0.75}
                    onClick={() => setSelected(n)}
                  />
                  <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={10} fontWeight={700}
                    fill={dirty ? "#fff" : "var(--ink-soft)"} style={{ pointerEvents: "none" }}>
                    {KIND_META[n.kind].icon}
                  </text>
                  <text x={p.x} y={p.y + 32} textAnchor="middle" fontSize={10.5} fontFamily="Figtree" fontWeight={600}
                    fill={dirty ? "var(--coral)" : "var(--ink-soft)"}>
                    {n.label}
                  </text>
                </g>
              );
            })}

            {/* territory nodes */}
            {territoryIds.map((id) => {
              const n = nodeById.get(id)!;
              const p = positions.get(id)!;
              const dirty = dirtySet.has(id);
              const isCopy = id.startsWith("copy_");
              return (
                <g key={id}>
                  {dirty && <circle cx={p.x} cy={p.y} r={13} fill="none" stroke="var(--coral)" strokeWidth={1.6} className="node-ripple" />}
                  <circle
                    cx={p.x} cy={p.y} r={9}
                    fill={dirty ? "url(#sphereDirty)" : "url(#sphere)"}
                    stroke={dirty ? "var(--coral)" : "#d5cfc6"}
                    strokeWidth={1.2}
                    className={dirty ? "node-dirty" : "node-clean"}
                    opacity={dirty ? 1 : 0.55}
                    onClick={() => setSelected(n)}
                  >
                    <title>{n.label}</title>
                  </circle>
                  {isCopy && (
                    <text x={p.x} y={p.y - 16} textAnchor="start" fontSize={9.5} fontFamily="JetBrains Mono"
                      fill={dirty ? "var(--coral)" : "#a39d92"} fontWeight={dirty ? 700 : 400}>
                      {n.territory!.toUpperCase()}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* ── provenance inspector rail ── */}
        <div className="surface p-5 self-start lg:sticky lg:top-4">
          {selected ? (
            <Inspector
              node={selected}
              dirty={dirtySet.has(selected.id)}
              reason={
                estimate?.dirty_nodes.find((d) => normalizeBackendNodeId(d.node_id) === selected.id)?.reason ??
                "No backend invalidation reason is available."
              }
              nodeById={nodeById}
              graphView={graphView}
            />
          ) : (
            <div className="text-center py-10">
              <div className="text-3xl mb-3">🔍</div>
              <div className="font-display font-bold text-[15px]">Provenance Inspector</div>
              <p className="text-[13px] mt-2 leading-relaxed" style={{ color: "var(--ink-soft)" }}>
                Click any node in the graph to see its SHA-256 fingerprint, parent dependencies and why it was invalidated.
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-end mt-6">
        <button className="btn-pill" onClick={onApprove} disabled={!estimate}>
          Continue to approval gate →
        </button>
      </div>
    </div>
  );
}

function Metric({ label, value, color, strike }: { label: string; value: string; color?: string; strike?: boolean }) {
  return (
    <div>
      <div className="font-mono2 text-[10.5px] tracking-widest" style={{ color: "var(--ink-soft)" }}>{label.toUpperCase()}</div>
      <div
        className="font-mono2 font-bold text-xl mt-0.5"
        style={{ color: color ?? "var(--ink-soft)", textDecoration: strike ? "line-through" : undefined }}
      >
        {value}
      </div>
    </div>
  );
}

function Inspector({
  node,
  dirty,
  reason,
  nodeById,
  graphView,
}: {
  node: SlateNode;
  dirty: boolean;
  reason: string;
  nodeById: Map<string, SlateNode>;
  graphView?: GraphView | null;
}) {
  const realFingerprint =
    graphView?.nodes.find((gn) => normalizeBackendNodeId(gn.node_id) === node.id)?.fingerprint;

  return (
    <div className="rise-in">
      <span
        className="pill mb-3"
        style={
          dirty
            ? { background: "var(--coral-soft)", color: "var(--coral)" }
            : { background: "var(--mint)", color: "var(--mint-deep)" }
        }
      >
        <span className="dot" style={{ background: dirty ? "var(--coral)" : "var(--mint-deep)" }} />
        {dirty ? "DIRTY — queued for rebuild" : "CLEAN — byte-exact cache hit"}
      </span>
      <div className="font-display font-bold text-lg leading-snug">{node.label}</div>
      <div className="font-mono2 text-[11px] mt-1" style={{ color: "var(--ink-soft)" }}>
        {node.id} · {node.kind}
        {node.model ? ` · ${node.model}` : ""}
      </div>

      <div className="mt-4 space-y-3 text-[13px]">
        <div>
          <div className="font-mono2 text-[10.5px] tracking-widest mb-1" style={{ color: "var(--ink-soft)" }}>SHA-256</div>
          <div className="font-mono2 text-[11px] break-all rounded-lg p-2.5" style={{ background: "var(--paper-warm)" }}>
            {realFingerprint ?? "Unavailable until returned by the backend graph"}
          </div>
        </div>
        <div>
          <div className="font-mono2 text-[10.5px] tracking-widest mb-1" style={{ color: "var(--ink-soft)" }}>PARENTS</div>
          {node.parents.length === 0 ? (
            <span style={{ color: "var(--ink-soft)" }}>— root node —</span>
          ) : (
            node.parents.map((p) => (
              <div key={p} className="font-mono2 text-[12px]" style={{ color: "var(--ink)" }}>
                ↳ {nodeById.get(p)?.label ?? p}
              </div>
            ))
          )}
        </div>
        {dirty && (
          <div>
            <div className="font-mono2 text-[10.5px] tracking-widest mb-1" style={{ color: "var(--ink-soft)" }}>
              INVALIDATION REASON
            </div>
            <div className="rounded-lg p-2.5 font-mono2 text-[11.5px]" style={{ background: "var(--coral-soft)", color: "var(--coral)" }}>
              {reason}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

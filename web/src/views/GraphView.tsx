import { useMemo, useState } from "react";
import type { GraphNode } from "../types";

const NODE_R = 10;
const CHAIN_X: Record<string, number> = { source: 80, shot_plan: 230, keyframe: 380, clip: 530 };
const GRID_COLS = 10;
const COL_W = 96;
const ROW_H = 64;
const BLOCK_H = 400;
const WIDTH = 1080;

interface Pos {
  x: number;
  y: number;
}

function layout(nodes: GraphNode[]): Map<string, Pos> {
  const campaigns = [...new Set(nodes.map((n) => n.campaign_id))].sort();
  const pos = new Map<string, Pos>();
  campaigns.forEach((cid, ci) => {
    const baseY = ci * BLOCK_H;
    const members = nodes.filter((n) => n.campaign_id === cid);
    const territories = [...new Set(members.map((n) => n.territory).filter((t) => t !== "master"))].sort();
    for (const n of members) {
      if (n.territory === "master") {
        pos.set(n.node_id, { x: CHAIN_X[n.kind] ?? 80, y: baseY + 50 });
      } else {
        const ti = territories.indexOf(n.territory);
        const col = ti % GRID_COLS;
        const row = Math.floor(ti / GRID_COLS);
        const x = 70 + col * COL_W + (n.kind === "package" ? 44 : 0);
        const y = baseY + 130 + row * ROW_H;
        pos.set(n.node_id, { x, y });
      }
    }
  });
  return pos;
}

interface Props {
  nodes: GraphNode[];
  selectedId: string | null;
  onSelect: (nodeId: string) => void;
}

export function GraphView({ nodes, selectedId, onSelect }: Props) {
  const [campaignFilter, setCampaignFilter] = useState<string>("all");
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [search, setSearch] = useState<string>("");
  const [is3D, setIs3D] = useState<boolean>(true);

  const pos = useMemo(() => layout(nodes), [nodes]);
  const campaigns = useMemo(() => [...new Set(nodes.map((n) => n.campaign_id))].sort(), [nodes]);
  const dirty = useMemo(() => new Set(nodes.filter((n) => n.state === "dirty").map((n) => n.node_id)), [nodes]);

  // Filter nodes according to toolbar
  const visibleNodes = useMemo(() => {
    return nodes.filter((n) => {
      if (campaignFilter !== "all" && n.campaign_id !== campaignFilter) return false;
      if (stateFilter === "dirty" && !dirty.has(n.node_id)) return false;
      if (stateFilter === "clean" && dirty.has(n.node_id)) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        return n.node_id.toLowerCase().includes(q) || n.territory.toLowerCase().includes(q) || n.kind.toLowerCase().includes(q);
      }
      return true;
    });
  }, [nodes, campaignFilter, stateFilter, search, dirty]);

  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.node_id)), [visibleNodes]);
  const filteredCampaigns = campaignFilter === "all" ? campaigns : [campaignFilter];
  const height = filteredCampaigns.length * BLOCK_H;

  return (
    <div>
      {/* Controls Toolbar */}
      <div className="graph-toolbar">
        <div className="graph-filters" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontSize: 11, fontWeight: 700, color: "var(--neon-cyan)", letterSpacing: "0.06em" }}>
            CAMPAIGN:
          </label>
          <select
            value={campaignFilter}
            onChange={(e) => setCampaignFilter(e.target.value)}
            style={{
              background: "var(--bg)",
              color: "var(--text)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "5px 10px",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            <option value="all">All Campaigns (3)</option>
            {campaigns.map((c) => (
              <option key={c} value={c}>
                {c.toUpperCase()}
              </option>
            ))}
          </select>

          <label style={{ fontSize: 11, fontWeight: 700, color: "var(--dim)", marginLeft: 8 }}>STATE:</label>
          <button
            className={`chip ${stateFilter === "all" ? "live" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => setStateFilter("all")}
          >
            All ({nodes.length})
          </button>
          <button
            className={`chip ${stateFilter === "dirty" ? "fallback" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => setStateFilter("dirty")}
          >
            Dirty ({dirty.size})
          </button>
          <button
            className={`chip ${stateFilter === "clean" ? "live" : ""}`}
            style={{ cursor: "pointer" }}
            onClick={() => setStateFilter("clean")}
          >
            Clean ({nodes.length - dirty.size})
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* 3D Isometric View Camera Toggle */}
          <button
            className="secondary"
            onClick={() => setIs3D(!is3D)}
            style={{
              background: is3D ? "linear-gradient(135deg, rgba(0,242,254,0.2) 0%, rgba(59,130,246,0.3) 100%)" : "rgba(255,255,255,0.05)",
              borderColor: is3D ? "var(--neon-cyan)" : "var(--border)",
              color: is3D ? "#fff" : "var(--text-muted)",
              fontWeight: 800,
              fontSize: 12,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {is3D ? "🧊 3D Hologram Tilt: ON" : "📐 Flat 2D View"}
          </button>

          <input
            type="text"
            placeholder="Search territory (de, fr, jp)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              padding: "6px 12px",
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "var(--bg)",
              color: "#fff",
              width: 180,
            }}
          />
        </div>
      </div>

      {/* 3D / 2D Graph Canvas */}
      <div className={`graph-canvas-container ${is3D ? "isometric-3d" : ""}`}>
        <svg className="graph-canvas" width={WIDTH} height={height}>
          <defs>
            {/* 3D Sphere Shading Gradients */}
            <radialGradient id="sphere-clean" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#a7f3d0" />
              <stop offset="50%" stopColor="#00ff9d" />
              <stop offset="100%" stopColor="#047857" />
            </radialGradient>
            <radialGradient id="sphere-dirty" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#fef08a" />
              <stop offset="40%" stopColor="#ff9a00" />
              <stop offset="100%" stopColor="#c2410c" />
            </radialGradient>
            <radialGradient id="sphere-selected" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="40%" stopColor="#00f2fe" />
              <stop offset="100%" stopColor="#1d4ed8" />
            </radialGradient>
            <filter id="glow-dirty" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="8" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {filteredCampaigns.map((cid) => {
            const ci = campaigns.indexOf(cid);
            const baseY = ci * BLOCK_H;
            return (
              <g key={cid}>
                {/* Campaign Header banner with radiant gradient */}
                <rect
                  x={20}
                  y={baseY + 12}
                  width={WIDTH - 40}
                  height={32}
                  rx={8}
                  fill="rgba(20, 27, 50, 0.6)"
                  stroke="rgba(0, 242, 254, 0.2)"
                />
                <text
                  x={36}
                  y={baseY + 33}
                  fill="var(--neon-cyan)"
                  fontWeight={900}
                  fontSize={13}
                  letterSpacing="0.08em"
                >
                  CAMPAIGN: {cid.toUpperCase()}
                </text>
                <text x={260} y={baseY + 33} fill="var(--dim)" fontSize={11} fontWeight={500}>
                  Master Spine (Left) ➔ 40 Localized Territory Variants (Right)
                </text>
              </g>
            );
          })}

          {/* Render Curved Bezier Edges */}
          {visibleNodes.flatMap((n) =>
            n.parents.map((p) => {
              if (!visibleNodeIds.has(p)) return null;
              const a = pos.get(p);
              const b = pos.get(n.node_id);
              if (!a || !b) return null;
              const hot = dirty.has(n.node_id);
              return (
                <path
                  key={`${p}->${n.node_id}`}
                  className={hot ? "edge-dirty" : "edge"}
                  stroke={hot ? "rgba(255, 154, 0, 0.75)" : "rgba(0, 242, 254, 0.18)"}
                  strokeWidth={hot ? 2.5 : 1.2}
                  fill="none"
                  d={`M ${a.x} ${a.y} C ${a.x + (b.x - a.x) * 0.5} ${a.y}, ${a.x + (b.x - a.x) * 0.5} ${b.y}, ${b.x} ${b.y}`}
                />
              );
            }),
          )}

          {/* Render 3D Nodes */}
          {visibleNodes.map((n) => {
            const p = pos.get(n.node_id);
            if (!p) return null;
            const isDirty = dirty.has(n.node_id);
            const isSelected = n.node_id === selectedId;
            const anyDirty = dirty.size > 0;

            const fillUrl = isSelected ? "url(#sphere-selected)" : isDirty ? "url(#sphere-dirty)" : "url(#sphere-clean)";

            return (
              <g
                key={n.node_id}
                className={isDirty ? "node-dirty" : undefined}
                onClick={() => onSelect(n.node_id)}
                style={{ cursor: "pointer" }}
                opacity={anyDirty && !isDirty ? 0.4 : 1}
              >
                {/* Luminous Pulsing Glow for Dirty Nodes */}
                {isDirty && (
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={NODE_R + 8}
                    fill="none"
                    stroke="#ff9a00"
                    strokeWidth={2}
                    opacity={0.7}
                    filter="url(#glow-dirty)"
                  />
                )}

                {/* Selection Halo */}
                {isSelected && (
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={NODE_R + 7}
                    fill="none"
                    stroke="#00f2fe"
                    strokeWidth={2.5}
                    box-shadow="0 0 16px #00f2fe"
                  />
                )}

                {/* 3D Sphere Node */}
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={isSelected ? NODE_R + 3 : NODE_R}
                  fill={fillUrl}
                  stroke={isDirty ? "#ea580c" : isSelected ? "#00f2fe" : "#065f46"}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                  filter={isDirty ? "url(#glow-dirty)" : undefined}
                >
                  <title>
                    {n.node_id} [{n.kind}] - {isDirty ? "DIRTY (Must Rebuild)" : "CLEAN (Reused from Cache for $0.00)"}
                  </title>
                </circle>

                {/* Node Labels */}
                {n.territory === "master" ? (
                  <text className="node-label" x={p.x + 14} y={p.y + 4} fontWeight={800} fill="#ffffff">
                    {n.kind}
                  </text>
                ) : n.kind === "copy" ? (
                  <text className="node-label" x={p.x + 13} y={p.y + 3} fontWeight={600} fill="var(--text-muted)">
                    {n.territory}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
        <div className="legend" style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span className="chip live">🟢 Clean: Reused $0.00</span>
          <span className="chip fallback">🟠 Dirty: In Blast Radius</span>
          <span style={{ fontSize: 12, color: "var(--dim)" }}>👉 Click any node to open Provenance Inspector rail</span>
        </div>
        <span style={{ fontSize: 12, color: "var(--dim)", fontWeight: 600 }}>
          Showing {visibleNodes.length} of {nodes.length} nodes
        </span>
      </div>
    </div>
  );
}

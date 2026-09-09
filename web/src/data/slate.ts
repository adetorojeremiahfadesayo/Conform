// ─────────────────────────────────────────────────────────────
// CONFORM slate model — a campaign rendered as a DAG of assets.
// Deterministic demo data mirroring the backend domain schemas.
// ─────────────────────────────────────────────────────────────

export type NodeKind =
  | "brief"
  | "shotplan"
  | "keyframe"
  | "video"
  | "copy"
  | "audio"
  | "music"
  | "package";

export interface SlateNode {
  id: string;
  label: string;
  kind: NodeKind;
  parents: string[];
  territory?: string;
  costUsd: number; // naive regeneration cost
  model?: string;
}

export interface Scenario {
  id: string;
  emoji: string;
  title: string;
  short: string;
  instruction: string;
  regulation?: string;
  dirtyIds: (nodes: SlateNode[]) => string[];
  spend: string;
  naiveSpend: string;
  savedPct: string;
  reason: string;
  scanFiles: string[];
}

// deterministic pseudo sha-256 fingerprint for demo display
export function fingerprint(seed: string): string {
  let h1 = 0xdeadbeef ^ seed.length;
  let h2 = 0x41c6ce57 ^ seed.length;
  let out = "";
  for (let i = 0; i < 64; i++) {
    const ch = seed.charCodeAt(i % seed.length);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
    const v = (h1 ^ h2) >>> 0;
    out += "0123456789abcdef"[v % 16];
    h1 >>>= 1;
  }
  return out;
}

export function normalizeBackendNodeId(id: string): string {
  let s = id.replace(/^campaign_[a-z]\./, "");
  if (s.startsWith("package.")) return "pkg_" + s.split(".")[1];
  if (s.startsWith("copy.")) return "copy_" + s.split(".")[1];
  if (s === "clip") return "hero_clip";
  if (s === "shot_plan") return "shotplan";
  if (s === "keyframe") return "keyframes";
  if (s === "source") return "brief";
  return s;
}

export const TERRITORIES: { cc: string; name: string; lang: string }[] = [
  { cc: "us", name: "United States", lang: "en-US" },
  { cc: "gb", name: "United Kingdom", lang: "en-GB" },
  { cc: "de", name: "Germany", lang: "de-DE" },
  { cc: "fr", name: "France", lang: "fr-FR" },
  { cc: "it", name: "Italy", lang: "it-IT" },
  { cc: "es", name: "Spain", lang: "es-ES" },
  { cc: "nl", name: "Netherlands", lang: "nl-NL" },
  { cc: "be", name: "Belgium", lang: "nl-BE" },
  { cc: "at", name: "Austria", lang: "de-AT" },
  { cc: "ch", name: "Switzerland", lang: "de-CH" },
  { cc: "se", name: "Sweden", lang: "sv-SE" },
  { cc: "no", name: "Norway", lang: "nb-NO" },
  { cc: "dk", name: "Denmark", lang: "da-DK" },
  { cc: "fi", name: "Finland", lang: "fi-FI" },
  { cc: "pl", name: "Poland", lang: "pl-PL" },
  { cc: "cz", name: "Czechia", lang: "cs-CZ" },
  { cc: "pt", name: "Portugal", lang: "pt-PT" },
  { cc: "ie", name: "Ireland", lang: "en-IE" },
  { cc: "gr", name: "Greece", lang: "el-GR" },
  { cc: "hu", name: "Hungary", lang: "hu-HU" },
  { cc: "jp", name: "Japan", lang: "ja-JP" },
  { cc: "kr", name: "South Korea", lang: "ko-KR" },
  { cc: "cn", name: "China", lang: "zh-CN" },
  { cc: "tw", name: "Taiwan", lang: "zh-TW" },
  { cc: "hk", name: "Hong Kong", lang: "zh-HK" },
  { cc: "sg", name: "Singapore", lang: "en-SG" },
  { cc: "in", name: "India", lang: "hi-IN" },
  { cc: "au", name: "Australia", lang: "en-AU" },
  { cc: "nz", name: "New Zealand", lang: "en-NZ" },
  { cc: "ca", name: "Canada", lang: "en-CA" },
  { cc: "mx", name: "Mexico", lang: "es-MX" },
  { cc: "br", name: "Brazil", lang: "pt-BR" },
  { cc: "ar", name: "Argentina", lang: "es-AR" },
  { cc: "cl", name: "Chile", lang: "es-CL" },
  { cc: "co", name: "Colombia", lang: "es-CO" },
  { cc: "ae", name: "UAE", lang: "ar-AE" },
  { cc: "sa", name: "Saudi Arabia", lang: "ar-SA" },
  { cc: "il", name: "Israel", lang: "he-IL" },
  { cc: "za", name: "South Africa", lang: "en-ZA" },
  { cc: "tr", name: "Türkiye", lang: "tr-TR" },
];

export const CAMPAIGNS = [
  { id: "aurora", title: "Aurora Sneaker Launch", slate: "A-17", assets: 84 },
  { id: "lumen", title: "Lumen Bank Rebrand", slate: "L-04", assets: 84 },
  { id: "terra", title: "Northwind Travel Winter", slate: "T-22", assets: 84 },
];

// ── build the DAG: 8 master nodes + per-territory copy/package pairs ──
export function buildSlate(): SlateNode[] {
  const master: SlateNode[] = [
    { id: "brief", label: "Creative Brief", kind: "brief", parents: [], costUsd: 0 },
    { id: "shotplan", label: "Shot Plan", kind: "shotplan", parents: ["brief"], costUsd: 0.0004, model: "Gemini" },
    { id: "keyframes", label: "Keyframe Stills", kind: "keyframe", parents: ["shotplan"], costUsd: 0.0021, model: "Imagen" },
    { id: "hero_clip", label: "Hero Clip (Veo)", kind: "video", parents: ["keyframes"], costUsd: 0.041, model: "Veo" },
    { id: "master_copy", label: "Master Copy Deck", kind: "copy", parents: ["brief"], costUsd: 0.0004, model: "Gemini" },
    { id: "voiceover", label: "Voiceover", kind: "audio", parents: ["master_copy"], costUsd: 0.0062, model: "Chirp" },
    { id: "music", label: "Music Bed", kind: "music", parents: ["shotplan"], costUsd: 0.0084, model: "Lyria" },
    { id: "mux_master", label: "Master Mux", kind: "package", parents: ["hero_clip", "voiceover", "music"], costUsd: 0.0001 },
  ];
  const nodes: SlateNode[] = [...master];
  for (const t of TERRITORIES) {
    nodes.push({
      id: `copy_${t.cc}`,
      label: `Copy · ${t.lang}`,
      kind: "copy",
      parents: ["master_copy"],
      territory: t.cc,
      costUsd: 0.0002,
      model: "Gemini",
    });
    nodes.push({
      id: `pkg_${t.cc}`,
      label: `Package · ${t.cc.toUpperCase()}`,
      kind: "package",
      parents: [`copy_${t.cc}`, "mux_master"],
      territory: t.cc,
      costUsd: 0.0001,
    });
  }
  return nodes;
}

export const TOTAL_ASSETS = 252;

const EU_LANG_TERRITORIES = ["de", "fr", "it", "es", "nl", "be"];

export const SCENARIOS: Scenario[] = [
  {
    id: "eu-reg",
    emoji: "🇪🇺",
    title: "EU Regulation Change",
    short: "New disclaimer rules for DE / FR markets",
    instruction:
      "New project rule R-DISC-004: require at least 40 characters in the disclaimer for German and French copy across the slate.",
    regulation: "R-DISC-004",
    dirtyIds: () =>
      EU_LANG_TERRITORIES.flatMap((cc) => [`copy_${cc}`, `pkg_${cc}`]),
    spend: "$0.0030",
    naiveSpend: "$0.0630",
    savedPct: "95.2%",
    reason: "RULE_R-DISC-004",
    scanFiles: [
      "slate/A-17/brief.yaml",
      "slate/A-17/regulations/R-DISC-004.json",
      "copy/de-DE/disclaimer_v3.txt",
      "copy/fr-FR/disclaimer_v3.txt",
      "copy/it-IT/disclaimer_v3.txt",
      "copy/es-ES/disclaimer_v3.txt",
      "copy/nl-NL/disclaimer_v3.txt",
      "copy/nl-BE/disclaimer_v3.txt",
      "packages/pkg_DE.manifest",
      "packages/pkg_FR.manifest",
      "packages/pkg_IT.manifest",
      "packages/pkg_ES.manifest",
      "packages/pkg_NL.manifest",
      "packages/pkg_BE.manifest",
    ],
  },
  {
    id: "reshoot",
    emoji: "🎬",
    title: "Master Clip Reshoot",
    short: "Hero prompt edit — new opening shot",
    instruction:
      "Reshoot the hero clip: replace the opening drone shot with a night-city dolly move, keep the rest of the cut untouched.",
    dirtyIds: () => {
      const ids = ["hero_clip", "mux_master"];
      for (const t of TERRITORIES) ids.push(`pkg_${t.cc}`);
      return ids;
    },
    spend: "$0.0481",
    naiveSpend: "$0.0630",
    savedPct: "23.7%",
    reason: "PROMPT_EDIT hero_clip",
    scanFiles: [
      "slate/A-17/prompts/hero_clip.txt",
      "video/hero_clip.veo.mp4",
      "mux/master_mux.mov",
      ...TERRITORIES.slice(0, 10).map((t) => `packages/pkg_${t.cc.toUpperCase()}.manifest`),
      "… + 30 more territory packages",
    ],
  },
  {
    id: "japan",
    emoji: "🇯🇵",
    title: "Japan Winter Retargeting",
    short: "Tokyo text overlay — winter offer",
    instruction:
      "Retarget the Tokyo market: swap the summer tagline for the winter offer in the ja-JP end card.",
    dirtyIds: () => ["copy_jp", "pkg_jp"],
    spend: "$0.0004",
    naiveSpend: "$0.0630",
    savedPct: "99.4%",
    reason: "TEXT_EDIT ja-JP",
    scanFiles: [
      "slate/A-17/brief.yaml",
      "copy/ja-JP/endcard.txt",
      "packages/pkg_JP.manifest",
    ],
  },
];

export interface ScanLine {
  path: string;
  status: "clean" | "dirty";
  detail: string;
}

export function buildScanLines(s: Scenario, slate: SlateNode[]): ScanLine[] {
  const dirty = new Set(s.dirtyIds(slate));
  const lines: ScanLine[] = [];
  s.scanFiles.forEach((p) => {
    const isEllipsis = p.startsWith("…");
    const isRule = p.includes("R-DISC-004");
    const isDirty =
      !isEllipsis &&
      !isRule &&
      (dirty.has(`copy_${p.split("/")[1]?.slice(0, 2)?.toLowerCase()}`) ||
        /pkg_(DE|FR|IT|ES|NL|BE|JP)/.test(p) ||
        p.includes("hero_clip") ||
        p.includes("master_mux") ||
        (s.id === "reshoot" && p.includes("pkg_")));
    lines.push({
      path: p,
      status: isDirty ? "dirty" : "clean",
      detail: isDirty
        ? "hash mismatch → invalidated"
        : isRule
          ? "new rule ingested"
          : isEllipsis
            ? "queued"
            : "hash match · cache hit",
    });
  });
  return lines;
}

export function dirtyAssets(s: Scenario, slate: SlateNode[]): SlateNode[] {
  const dirty = new Set(s.dirtyIds(slate));
  return slate.filter((n) => dirty.has(n.id));
}

export function reusedCount(s: Scenario): number {
  void s;
  return 0;
}

export const KIND_META: Record<NodeKind, { color: string; soft: string; icon: string }> = {
  brief: { color: "#8a7a68", soft: "#efe7df", icon: "B" },
  shotplan: { color: "#8a7a68", soft: "#efe7df", icon: "S" },
  keyframe: { color: "#3f6f8f", soft: "#eaf3f8", icon: "K" },
  video: { color: "#2b5f8f", soft: "#eaf3f8", icon: "V" },
  copy: { color: "#a3722a", soft: "#fdf1de", icon: "C" },
  audio: { color: "#6a5a8f", soft: "#efecf7", icon: "A" },
  music: { color: "#6a5a8f", soft: "#efecf7", icon: "M" },
  package: { color: "#4c8a2f", soft: "#e7fec7", icon: "P" },
};

export interface StepDef {
  n: number;
  label: string;
  icon: string;
}

export const STEPS: StepDef[] = [
  { n: 1, label: "Propose", icon: "✏️" },
  { n: 2, label: "Agent Scan", icon: "🕵️" },
  { n: 3, label: "Blast Radius", icon: "🕸️" },
  { n: 4, label: "Approval", icon: "🛑" },
  { n: 5, label: "Rebuild", icon: "🤖" },
  { n: 6, label: "Release", icon: "🔏" },
];

export default function Stepper({
  current,
  maxUnlocked,
  onJump,
}: {
  current: number;
  maxUnlocked: number;
  onJump: (n: number) => void;
}) {
  return (
    <div className="flex items-center gap-1 flex-wrap justify-center">
      {STEPS.map((s, i) => {
        const done = s.n < current;
        const active = s.n === current;
        const locked = s.n > maxUnlocked;
        return (
          <div key={s.n} className="flex items-center">
            <button
              onClick={() => !locked && onJump(s.n)}
              disabled={locked}
              className="flex items-center gap-2 rounded-full px-3 py-1.5 text-[13px] font-semibold transition-all"
              style={{
                background: active ? "var(--charcoal)" : done ? "var(--mint)" : "transparent",
                color: active ? "#fff" : done ? "var(--ink)" : locked ? "#b9b5ac" : "var(--ink-soft)",
                cursor: locked ? "not-allowed" : "pointer",
                border: active ? "1px solid var(--charcoal)" : "1px solid transparent",
              }}
              title={locked ? "Complete previous stages to unlock" : s.label}
            >
              <span className="text-[12px]">{done ? "✓" : s.icon}</span>
              <span className="hidden md:inline">{s.label}</span>
              <span className="md:hidden">{s.n}</span>
            </button>
            {i < STEPS.length - 1 && (
              <div
                className="w-4 h-[2px] mx-0.5 rounded"
                style={{ background: s.n < current ? "var(--mint-deep)" : "var(--hairline)" }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

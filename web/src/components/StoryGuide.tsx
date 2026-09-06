const GUIDE: Record<number, { title: string; body: string }> = {
  1: {
    title: "Roll camera — what's changing?",
    body: "Pick the campaign and describe the change. In a real studio this is the moment a new regulation, a reshoot note, or a retargeting request lands on the producer's desk.",
  },
  2: {
    title: "The agent reads the slate",
    body: "Instead of regenerating everything, an agent walks the production slate file by file, comparing content hashes to find exactly which assets the change touches — its blast radius.",
  },
  3: {
    title: "See the blast radius",
    body: "The slate is a dependency graph. Dirty assets glow coral — they'll be rebuilt. Everything dimmed stays byte-for-byte from cache at zero cost. Click any node to inspect its provenance.",
  },
  4: {
    title: "Human approval gate",
    body: "No generative model runs before a human signs off. You see the exact rebuild bill versus naive regeneration, then approve or reject. The build stays locked until you do.",
  },
  5: {
    title: "Surgical rebuild",
    body: "The agent rebuilds only the dirty subtree, streaming its progress live. Clean assets are reused from cache at $0.00. Watch each asset flip from dirty to sealed.",
  },
  6: {
    title: "Verify & analyse",
    body: "The release is sealed with a SHA-256 manifest. Re-hash every artifact to prove byte-exact integrity — or corrupt one byte and watch verification catch it instantly.",
  },
};

export default function StoryGuide({ step }: { step: number }) {
  const g = GUIDE[step] ?? GUIDE[1];
  return (
    <div className="surface-warm px-6 py-4 flex items-start gap-4 rise-in" key={step}>
      <div
        className="w-9 h-9 rounded-full flex-none flex items-center justify-center font-display font-bold text-white text-sm mt-0.5"
        style={{ background: "var(--coral)" }}
      >
        {step}
      </div>
      <div>
        <div className="font-display font-bold text-[15px]">{g.title}</div>
        <div className="text-[13.5px] leading-relaxed" style={{ color: "var(--ink-soft)" }}>
          {g.body}
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";

interface Props {
  activeStep: number;
  onNavigateStep: (step: number) => void;
}

interface StoryBeat {
  step: number;
  badge: string;
  headline: string;
  plainEnglish: string;
  actionHint: string;
  nextStepLabel: string;
}

const STORY_BEATS: Record<number, StoryBeat> = {
  1: {
    step: 1,
    badge: "STEP 1 · THE REAL-WORLD PROBLEM",
    headline: "Global Brand Ad: 40 Countries, 252 Video Files",
    plainEnglish:
      "Imagine baking 40 cakes. If one cherry changes in France, dumb AI throws away all 40 cakes and re-renders everything. Click the EU Regulation card below to see how CONFORM prevents this waste!",
    actionHint: "👉 Click '🇪🇺 EU Regulation Change' then hit 'Compute Blast Radius'.",
    nextStepLabel: "See Blast Radius ➔",
  },
  2: {
    step: 2,
    badge: "STEP 2 · SMART DETECTION (THE BLUEPRINT)",
    headline: "Only 12 Files Changed — 240 Recycled for $0.00!",
    plainEnglish:
      "Boom! CONFORM checked the digital DNA of every file. The expensive running-sneaker video clips are untouched. We only need to remake 12 text files. You just saved 95% of the bill!",
    actionHint: "👉 Switch to the 3D Graph to see the 12 orange dirty files, or approve the bill below.",
    nextStepLabel: "Go to Approval Gate ➔",
  },
  3: {
    step: 3,
    badge: "STEP 3 · HUMAN APPROVAL GATE",
    headline: "AI is Locked — Human Must Approve the Spend",
    plainEnglish:
      "CONFORM has a strict safety law: AI is NEVER allowed to spend your money automatically. A real producer must review the $0.0030 quote and click Approve.",
    actionHint: "👉 Click '✓ Approve Spend ($0.0030)' to unlock the build engine.",
    nextStepLabel: "Build Dirty Subtree ➔",
  },
  4: {
    step: 4,
    badge: "STEP 4 · SURGICAL REBUILD & CACHE REUSE",
    headline: "Only Remaking the 12 Dirty Pieces",
    plainEnglish:
      "The build is running! The 12 French & German copy packages are being compiled, while all 240 video clips and audio files are pulled instantly from cache at $0.00 cost.",
    actionHint: "👉 Filter by 'Rebuilt Only' vs 'Cache Hits Reused' to prove zero redundant spend.",
    nextStepLabel: "Verify Tamper-Proof Seal ➔",
  },
  5: {
    step: 5,
    badge: "STEP 5 · CRYPTOGRAPHIC TAMPER SEAL",
    headline: "Mathematically Proving Nobody Messed with the Video",
    plainEnglish:
      "Every video package is sealed with a digital cryptographic hash. Click 'Corrupt 1 Byte' to simulate an accidental file corruption or tampering and watch CONFORM sound the security alarm in RED!",
    actionHint: "👉 Click 'Verify Release' (green), then click 'Corrupt 1 Byte', then re-verify (instant red detection)!",
    nextStepLabel: "See Slate Analytics ➔",
  },
  6: {
    step: 6,
    badge: "STEP 6 · CLICKHOUSE SLATE ANALYTICS",
    headline: "Executive Proof: 95%+ Total Budget Saved",
    plainEnglish:
      "Every penny saved and every model call is streamed into ClickHouse Cloud. You can even ask the Natural Language AI Analyst questions like: 'What is our spend across models?'",
    actionHint: "👉 Click 'Ask the Slate' to chat with the AI Analyst over ClickHouse data!",
    nextStepLabel: "Start New Change ➔",
  },
};

export function DirectorStoryGuide({ activeStep, onNavigateStep }: Props) {
  const [minimized, setMinimized] = useState(false);
  const beat = STORY_BEATS[activeStep] || STORY_BEATS[1];

  return (
    <div className={`story-guide-container ${minimized ? "minimized" : ""}`}>
      <div className="story-guide-glow" />
      <div className="story-guide-content">
        <div className="story-guide-left">
          <div className="story-guide-header">
            <span className="story-guide-badge">{beat.badge}</span>
            <span className="story-guide-title">{beat.headline}</span>
          </div>
          {!minimized && (
            <>
              <p className="story-guide-text">{beat.plainEnglish}</p>
              <div className="story-guide-hint">{beat.actionHint}</div>
            </>
          )}
        </div>

        <div className="story-guide-right">
          <button
            className="story-next-btn"
            onClick={() => {
              const next = activeStep < 6 ? activeStep + 1 : 1;
              onNavigateStep(next);
            }}
          >
            {beat.nextStepLabel}
          </button>
          <button
            className="story-toggle-btn"
            onClick={() => setMinimized(!minimized)}
            title={minimized ? "Expand Explanation" : "Minimize"}
          >
            {minimized ? "📖 Explain" : "▴ Hide"}
          </button>
        </div>
      </div>
    </div>
  );
}

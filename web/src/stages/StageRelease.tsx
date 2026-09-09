import { useState } from "react";
import { api } from "../api";
import type { AskResult, BuildResult, SystemStatus } from "../types";
import type { Scenario } from "../data/slate";

const SUGGESTIONS = [
  "How many nodes were reused vs rebuilt?",
  "What is our spend across models?",
  "What did the disclaimer rule change affect?",
];

export default function StageRelease({ buildResult, onOpenAsk }: {
  scenario: Scenario;
  dirtyCount: number;
  buildResult?: BuildResult | null;
  systemStatus?: SystemStatus | null;
  onOpenAsk?: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [askResult, setAskResult] = useState<AskResult | null>(null);
  const [askError, setAskError] = useState<string | null>(null);

  const release = buildResult?.release ?? null;

  const handleAsk = async (textToQuery?: string) => {
    const q = (textToQuery ?? question).trim();
    if (!q) {
      if (onOpenAsk) onOpenAsk();
      return;
    }
    setIsAsking(true);
    setAskError(null);
    try {
      const res = await api.ask(q);
      setAskResult(res);
    } catch (err) {
      setAskResult(null);
      setAskError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="stage-enter space-y-6">
      {release && (
        <div className="grid sm:grid-cols-3 gap-4">
          {release.artifacts.filter((item) => item.node_id.endsWith(".package.de")).map((item) => (
            <div className="surface p-4" key={item.node_id}>
              <video
                controls
                preload="metadata"
                className="w-full rounded-xl max-h-80"
                src={`/api/releases/${release.release_id}/artifacts/${item.node_id}`}
              />
              <div className="text-xs mt-2" style={{ color: "var(--ink-soft)" }}>{item.node_id}</div>
            </div>
          ))}
        </div>
      )}

      <div className="surface p-6 space-y-4">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg flex items-center justify-center text-lg bg-white shadow-sm">
            💬
          </span>
          <div>
            <h3 className="font-display font-bold text-lg">Ask the Slate</h3>
            <p className="text-[12.5px]" style={{ color: "var(--ink-soft)" }}>
              Query slate analytics, compilation efficiency, spend, or compliance history.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAsk();
              }
            }}
            placeholder="Ask questions about this slate, build spend, cache reuse, or compliance rules..."
            rows={3}
            className="w-full p-4 rounded-xl text-[14px] outline-none transition-all resize-none"
            style={{
              background: "var(--paper-warm)",
              border: "1px solid var(--hairline)",
              color: "var(--ink)",
              fontFamily: "inherit",
            }}
          />

          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    setQuestion(s);
                    handleAsk(s);
                  }}
                  className="pill hover:bg-black/5 transition-all text-[11.5px] cursor-pointer"
                  style={{ background: "var(--paper-warm)", color: "var(--ink-soft)" }}
                >
                  {s}
                </button>
              ))}
            </div>

            <button
              type="button"
              disabled={isAsking}
              onClick={() => handleAsk()}
              className="btn-pill px-6 py-2.5 flex items-center gap-2 ml-auto"
              style={{ background: "var(--charcoal)", color: "#fff" }}
            >
              {isAsking ? "Querying..." : "Ask the Slate →"}
            </button>
          </div>
        </div>

        {askResult && (
          <div className="rise-in rounded-2xl p-5 mt-4 space-y-3" style={{ background: "var(--paper-warm)" }}>
            {askResult.answer && (
              <div className="text-[14px] leading-relaxed font-medium" style={{ color: "var(--ink)" }}>
                {askResult.answer}
              </div>
            )}
            {askResult.rows && askResult.rows.length > 0 && (
              <div className="overflow-x-auto max-h-60 rounded-xl bg-white border border-[var(--hairline)]">
                <table className="w-full text-left text-[12.5px]">
                  <thead className="hairline-b font-mono2 text-[11px] text-[var(--ink-soft)] bg-[var(--paper-warm)]">
                    <tr>
                      {Object.keys(askResult.rows[0]).map((col) => (
                        <th key={col} className="p-2.5 font-semibold">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {askResult.rows.map((row, idx) => (
                      <tr key={idx} className="hairline-b font-mono2">
                        {Object.keys(row).map((col) => (
                          <td key={col} className="p-2.5">{String(row[col] ?? "")}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {askError && (
          <div className="rise-in rounded-xl p-3 text-[13px]" style={{ background: "var(--coral-soft)", color: "var(--coral)" }}>
            ⚠ {askError}
          </div>
        )}
      </div>
    </div>
  );
}

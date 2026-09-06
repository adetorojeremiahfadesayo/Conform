import { useState } from "react";
import { api, ApiError } from "../api";
import type { AskResult } from "../types";

const SUGGESTIONS = [
  "What is our spend across models?",
  "How many nodes were reused vs rebuilt?",
  "Which transient errors were auto-retried?",
  "Which nodes are cache-hostile and burning cost?",
  "What is our cost per finished second of video?",
  "What did the disclaimer rule change affect?",
];

export default function AskModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [query, setQuery] = useState(SUGGESTIONS[0]);
  const [customSql, setCustomSql] = useState("");
  const [showSqlEditor, setShowSqlEditor] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!isOpen) return null;

  async function runQuery(qText?: string, sqlText?: string) {
    setBusy(true);
    setError(null);
    try {
      const activeQuery = qText !== undefined ? qText : query;
      const activeSql = sqlText !== undefined ? sqlText : customSql;
      setResult(await api.ask(activeQuery, activeSql));
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? `${e.code}: ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  }

  const columns = result && result.rows.length > 0 ? Object.keys(result.rows[0]) : [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 overlay-in"
      style={{ background: "rgba(43,41,38,0.55)", backdropFilter: "blur(6px)" }}
    >
      <div
        className="surface pop-in relative max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl"
        style={{ borderRadius: 24, border: "1px solid var(--hairline)" }}
      >
        {/* Header */}
        <div className="hairline-b p-6 flex items-center justify-between" style={{ background: "var(--paper-warm)" }}>
          <div className="flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl flex items-center justify-center text-xl bg-white shadow-sm">
              💬
            </span>
            <div>
              <div className="font-display font-bold text-lg">Ask the Slate</div>
              <div className="text-[12.5px]" style={{ color: "var(--ink-soft)" }}>
                Natural Language Analyst Agent · ClickHouse MCP JSON-RPC 2.0
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm transition-colors hover:bg-black/5"
            style={{ color: "var(--ink-soft)" }}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          <p className="text-[13.5px] leading-relaxed" style={{ color: "var(--ink-soft)" }}>
            Ask natural-language questions over multi-campaign build history. The Analyst Agent generates guarded
            read-only SQL, executes it through the official <b>ClickHouse MCP server</b>, and explains the results grounded in
            table rows.
          </p>

          {/* Suggestion Chips */}
          <div className="flex gap-2 flex-wrap">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                className="pill text-[12px] transition-all hover:border-black/20"
                style={{
                  background: query === s ? "var(--charcoal)" : "var(--paper-warm)",
                  color: query === s ? "#fff" : "var(--ink)",
                  cursor: "pointer",
                }}
                onClick={() => {
                  setQuery(s);
                  setCustomSql("");
                  runQuery(s, "");
                }}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Search bar */}
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runQuery()}
              placeholder="Ask anything about slate spend, cache reuse, retries, or rule impact…"
              className="flex-1 rounded-xl border px-4 py-3 text-[14px] outline-none transition-colors"
              style={{ borderColor: "var(--hairline)", background: "var(--paper)" }}
            />
            <button
              className="btn-pill flex-none"
              onClick={() => runQuery()}
              disabled={busy || (!query.trim() && !customSql.trim())}
            >
              {busy ? "Analyzing…" : "Ask Agent →"}
            </button>
          </div>

          {/* SQL Editor Toggle */}
          <div>
            <button
              className="text-[12px] font-mono2 font-semibold hover:underline"
              style={{ color: "var(--ink-soft)" }}
              onClick={() => setShowSqlEditor(!showSqlEditor)}
            >
              {showSqlEditor ? "Hide SQL editor ▴" : "Direct SQL mode (power users) ▾"}
            </button>
          </div>

          {showSqlEditor && (
            <div className="space-y-2">
              <textarea
                value={customSql}
                onChange={(e) => setCustomSql(e.target.value)}
                placeholder="SELECT model, sum(cost_usd) FROM provider_calls GROUP BY model LIMIT 10"
                className="w-full h-24 font-mono2 text-[12px] p-3 rounded-xl border outline-none"
                style={{ background: "var(--paper)", borderColor: "var(--hairline)" }}
              />
              <button
                className="btn-pill text-[13px] py-1.5"
                onClick={() => runQuery(undefined, customSql)}
                disabled={busy || !customSql.trim()}
              >
                Execute Guarded SQL
              </button>
            </div>
          )}

          {error && (
            <div className="rounded-xl p-3 text-[13px]" style={{ background: "var(--coral-soft)", color: "var(--coral)" }}>
              {error}
            </div>
          )}

          {/* Result Card */}
          {result && (
            <div className="space-y-4 pt-2">
              {result.answer && (
                <div
                  className="rounded-2xl p-5 rise-in"
                  style={{ background: "var(--mint)", border: "1px solid #cbe9a9" }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-display font-bold text-[14px]" style={{ color: "var(--mint-deep)" }}>
                      🤖 Analyst Agent Explanation
                    </span>
                    <span className="pill text-[10.5px]" style={{ background: "#fff", color: "var(--mint-deep)" }}>
                      mode: {result.reader_mode}
                    </span>
                  </div>
                  <p className="text-[14px] leading-relaxed" style={{ color: "var(--ink)" }}>
                    {result.answer}
                  </p>
                </div>
              )}

              {/* Executed SQL preview */}
              <div>
                <div className="font-mono2 text-[10.5px] tracking-widest mb-1" style={{ color: "var(--ink-soft)" }}>
                  EXECUTED READ-ONLY SQL (CLICKHOUSE VIA MCP)
                </div>
                <div
                  className="rounded-xl p-3 font-mono2 text-[11.5px] overflow-x-auto"
                  style={{ background: "var(--charcoal)", color: "#e7fec7" }}
                >
                  {result.sql}
                </div>
              </div>

              {/* Rows table */}
              {columns.length > 0 && (
                <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--hairline)" }}>
                  <table className="w-full text-[12.5px] text-left">
                    <thead style={{ background: "var(--paper-warm)" }}>
                      <tr>
                        {columns.map((c) => (
                          <th key={c} className="px-3 py-2 font-mono2 font-semibold" style={{ color: "var(--ink-soft)" }}>
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: "var(--hairline)" }}>
                      {result.rows.slice(0, 30).map((r, i) => (
                        <tr key={i} className="hover:bg-black/5">
                          {columns.map((c) => (
                            <td key={c} className="px-3 py-2 font-mono2">
                              {String(r[c] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="hairline-t px-6 py-3 text-[11.5px] flex items-center justify-between" style={{ background: "var(--paper-warm)", color: "var(--ink-soft)" }}>
          <span>Security guardrails: read-only SELECT via official mcp-clickhouse server.</span>
          <button className="font-semibold hover:underline" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

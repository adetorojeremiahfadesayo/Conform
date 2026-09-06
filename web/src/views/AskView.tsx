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

export function AskView() {
  const [query, setQuery] = useState(SUGGESTIONS[0]);
  const [customSql, setCustomSql] = useState("");
  const [showSqlEditor, setShowSqlEditor] = useState(false);
  const [result, setResult] = useState<AskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
    <div>
      <div className="panel">
        <h2>💬 Ask the Slate — Natural Language Analyst Agent (ClickHouse MCP)</h2>
        <p style={{ color: "var(--dim)", fontSize: 13, marginBottom: 14 }}>
          Ask natural-language questions over multi-campaign build history. The Analyst Agent generates
          guarded read-only SQL, executes it through the official <strong>ClickHouse MCP server</strong>, and
          explains the results grounded strictly in the database rows.
        </p>

        {/* Suggestion Chips */}
        <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className={`chip ${query === s ? "live" : ""}`}
              style={{ cursor: "pointer", fontSize: 12, padding: "5px 12px" }}
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

        {/* Natural Language Input Bar */}
        <div style={{ display: "flex", gap: 10, alignItems: "stretch" }}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runQuery()}
            placeholder="Ask anything about slate spend, cache reuse, retries, or rule impact..."
            style={{
              flex: 1,
              padding: "12px 16px",
              fontSize: 14,
              borderRadius: 8,
              border: "1px solid var(--border)",
            }}
          />
          <button
            className="primary"
            onClick={() => runQuery()}
            disabled={busy || (!query.trim() && !customSql.trim())}
            style={{ padding: "0 24px", fontSize: 14 }}
          >
            {busy ? "Analyzing Slate..." : "Ask Agent"}
          </button>
        </div>

        {/* Custom SQL Toggle */}
        <div style={{ marginTop: 12 }}>
          <button
            className="chip"
            style={{ cursor: "pointer", fontSize: 11 }}
            onClick={() => setShowSqlEditor(!showSqlEditor)}
          >
            {showSqlEditor ? "Hide SQL editor ▴" : "Direct SQL Mode (Power Users) ▾"}
          </button>
        </div>

        {showSqlEditor && (
          <div style={{ marginTop: 10 }}>
            <textarea
              value={customSql}
              onChange={(e) => setCustomSql(e.target.value)}
              placeholder="SELECT model, sum(cost_usd) FROM provider_calls GROUP BY model LIMIT 10"
              style={{ fontFamily: "var(--font-mono)", width: "100%", height: 80 }}
            />
            <button
              className="secondary"
              style={{ marginTop: 8 }}
              onClick={() => runQuery(undefined, customSql)}
              disabled={busy || !customSql.trim()}
            >
              Execute Guarded SQL
            </button>
          </div>
        )}

        {error && <div className="error" style={{ marginTop: 14 }}>{error}</div>}

        {/* Results Container */}
        {result && (
          <div style={{ marginTop: 20 }}>
            {/* Analyst Explanation Card */}
            {result.answer && (
              <div
                style={{
                  background: "rgba(99, 102, 241, 0.08)",
                  border: "1px solid rgba(99, 102, 241, 0.3)",
                  borderRadius: 10,
                  padding: "16px 20px",
                  marginBottom: 18,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <span style={{ fontWeight: 700, fontSize: 13, color: "#a5b4fc" }}>
                    🤖 Analyst Agent Explanation
                  </span>
                  <span className={`chip ${result.interpretation_mode === "gemini" ? "live" : "fallback"}`} style={{ fontSize: 10 }}>
                    interpreter: {result.interpretation_mode}
                  </span>
                  <span className={`chip ${result.reader_mode === "live_mcp" ? "live" : "fallback"}`} style={{ fontSize: 10 }}>
                    reader: {result.reader_mode}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: "var(--text)" }}>{result.answer}</p>
              </div>
            )}

            {/* Executed SQL */}
            <p style={{ fontSize: 11, color: "var(--dim)", margin: "10px 0 6px 0", fontWeight: 600 }}>
              EXECUTED SQL (Read-only guarded SELECT via ClickHouse {result.reader_mode}):
            </p>
            <pre className="sql" style={{ margin: 0 }}>{result.sql}</pre>

            {/* Result Rows Table */}
            {columns.length > 0 ? (
              <div style={{ marginTop: 14, overflowX: "auto" }}>
                <table className="rows">
                  <thead>
                    <tr>
                      {columns.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.slice(0, 50).map((row, i) => (
                      <tr key={i}>
                        {columns.map((c) => (
                          <td key={c} style={{ fontFamily: typeof row[c] === "number" ? "var(--font-mono)" : undefined }}>
                            {String(row[c] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: "var(--dim)", fontSize: 12, marginTop: 10 }}>
                Query executed successfully through MCP reader but returned 0 rows.
              </p>
            )}
          </div>
        )}

        <p className="disclaimer" style={{ marginTop: 24 }}>
          Security guardrails enforced: single read-only SELECT only with row limits.
          Mutations, DDL, and administrative queries are blocked before reaching ClickHouse.
        </p>
      </div>
    </div>
  );
}

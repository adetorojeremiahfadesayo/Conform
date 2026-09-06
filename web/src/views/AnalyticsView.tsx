import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { AnalyticsSummary } from "../types";

export function AnalyticsView() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setSummary(await api.analyticsSummary());
    } catch (e) {
      setError(e instanceof ApiError ? `${e.code}: ${e.message}` : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading && !summary) {
    return (
      <div className="panel">
        <h2>Slate Analytics & Savings</h2>
        <p style={{ color: "var(--dim)", fontSize: 13 }}>Querying ClickHouse telemetry tables...</p>
      </div>
    );
  }

  const cachePercent = summary ? Math.round(summary.cache_hit_rate * 100) : 0;
  const totalAssets = summary ? summary.nodes_reused + summary.nodes_rebuilt : 0;

  return (
    <div>
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div>
            <h2>6 · Slate Telemetry & Cost Avoidance Analytics</h2>
            <p style={{ color: "var(--dim)", fontSize: 13, margin: 0 }}>
              Live metrics aggregated from ClickHouse event store (<code>node_runs</code>, <code>provider_calls</code>, <code>build_savings_mv</code>).
            </p>
          </div>
          <button className="secondary" onClick={load} disabled={loading}>
            {loading ? "Refreshing..." : "↻ Refresh Telemetry"}
          </button>
        </div>

        {error && <div className="error" style={{ marginBottom: 14 }}>{error}</div>}

        {summary && (
          <>
            {/* KPI Cards */}
            <div className="stats">
              <div className="stat reused">
                <div className="num">${summary.avoided_spend_usd}</div>
                <div className="lbl">avoided spend (saved)</div>
              </div>
              <div className="stat">
                <div className="num">${summary.total_spend_usd}</div>
                <div className="lbl">actual total spend</div>
              </div>
              <div className="stat reused">
                <div className="num">{cachePercent}%</div>
                <div className="lbl">cache hit rate</div>
              </div>
              <div className="stat">
                <div className="num">{summary.nodes_reused} / {totalAssets}</div>
                <div className="lbl">assets reused from cache</div>
              </div>
            </div>

            {/* Visual Compilation Advantage Bar */}
            <div
              style={{
                background: "rgba(18, 24, 38, 0.7)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "16px 20px",
                marginBottom: 24,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontWeight: 700, fontSize: 13, color: "#e2e8f0" }}>
                  Compilation Efficiency Gauge (Reused vs Rebuilt)
                </span>
                <span style={{ fontSize: 12, color: "#10b981", fontWeight: 700 }}>
                  {cachePercent}% Reused Byte-for-Byte
                </span>
              </div>

              {/* Progress Bar */}
              <div
                style={{
                  height: 14,
                  width: "100%",
                  background: "rgba(245, 158, 11, 0.25)",
                  borderRadius: 9999,
                  overflow: "hidden",
                  display: "flex",
                }}
              >
                <div
                  style={{
                    width: `${cachePercent}%`,
                    background: "linear-gradient(90deg, #10b981 0%, #059669 100%)",
                    transition: "width 0.6s ease",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 11, color: "var(--dim)" }}>
                <span>🟩 Clean Cache Hits: {summary.nodes_reused} nodes ($0.00)</span>
                <span>🟧 Dirty Rebuilt Subtree: {summary.nodes_rebuilt} nodes (${summary.total_spend_usd})</span>
              </div>
            </div>

            {/* Tables Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              <div>
                <h3 style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Spend by AI Model & Modality
                </h3>
                <table className="rows">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Modality</th>
                      <th>Calls</th>
                      <th>Incurred Spend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.spend_by_model.map((m, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{String(m.model ?? "")}</td>
                        <td><span className="badge">{String(m.modality ?? "")}</span></td>
                        <td>{String(m.calls ?? "")}</td>
                        <td style={{ fontWeight: 700, color: "#cbd5e1" }}>
                          ${parseFloat(String(m.spend_usd ?? 0)).toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div>
                <h3 style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Runs & Spend by Campaign
                </h3>
                <table className="rows">
                  <thead>
                    <tr>
                      <th>Campaign ID</th>
                      <th>Total Runs</th>
                      <th>Total Spend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.spend_by_campaign.map((c, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{String(c.campaign_id ?? "")}</td>
                        <td>{String(c.total_runs ?? "")}</td>
                        <td style={{ fontWeight: 700, color: "#cbd5e1" }}>
                          ${parseFloat(String(c.spend_usd ?? 0)).toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        <p className="disclaimer" style={{ marginTop: 24 }}>
          Metrics computed deterministically from ClickHouse event logs.
          No model hallucination or approximate cost estimation — pure database arithmetic.
        </p>
      </div>
    </div>
  );
}

# DEVIATIONS — CONFORM

Record of design nuances, operational deviations, and intentional departures from the PRD.

---

## DEV-001: Unified FastAPI SPA Serving for Cloud Run

- **PRD Reference**: PRD §7, §9 Day 10.
- **Departure**: PRD contemplated separate static hosting or reverse proxies for backend and frontend.
- **Implementation**: Adopted a multi-stage Docker build that compiles the React application into `web/dist` and mounts it directly inside FastAPI (`/assets` static mount and SPA root catch-all).
- **Rationale**: Eliminates cross-origin CORS latency, ensures a judge can open the Cloud Run URL cold with zero routing misconfigurations, and fits seamlessly within a single Cloud Run service definition.

---

## DEV-002: Dual-Mode Analyst Agent (Gemini + Deterministic Fallback)

- **PRD Reference**: PRD §5 FR-8.4.
- **Departure**: Enhanced to support both live Gemini structured SQL generation and a deterministic keyword/pattern mapping.
- **Implementation**: If `VERTEX_TEXT_MODEL` or Google credentials are not configured, the Analyst Agent automatically uses deterministic query mapping and structured row explanation templates, labelled as `interpretation_mode="fallback_deterministic"`.
- **Rationale**: Guarantees the system is 100% testable and operable in offline mode without requiring live Vertex API quota during local testing or CI runs.

---

## DEV-003: SQLite View Emulation for ClickHouse Materialized View

- **PRD Reference**: PRD §6 Data Model (`build_savings_mv`).
- **Departure**: SQLite does not support ClickHouse `SummingMergeTree` materialized views.
- **Implementation**: Created a standard SQLite view `build_savings_mv` using conditional aggregations (`SUM(CASE WHEN cache_hit = 1 ...)`), providing cross-dialect query compatibility.
- **Rationale**: Allows identical analyst queries and metrics calculations to execute unchanged across both ClickHouse Cloud and local SQLite development.

---

## DEV-004: Stored Live ADK Preset Interpretations

- **PRD Reference**: PRD human-approval workflow and deterministic boundary.
- **Departure**: Curated demo presets may reuse a validated interpretation captured from an earlier successful
  live Google ADK run instead of invoking the model on every presentation run.
- **Implementation**: The content-addressed store accepts snapshots only when the source execution reports
  `google_adk_live` and the intent reports `gemini`. Replay creates a new change, recomputes the deterministic
  estimate, and still stops at approval.
- **Rationale**: Reduces demo latency and exposure to transient model-service failures without using fabricated
  results or bypassing any spend, approval, build, or verification invariant.

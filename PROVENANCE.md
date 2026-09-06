# Implementation Provenance Record — CONFORM

**Project:** CONFORM — Compiler for Generative Media Pipelines  
**Target:** Agentic Cinema: The Blockbuster Hackathon (Devpost)  
**Track:** ClickHouse Partner Track  
**License:** Apache-2.0 (Open Source)  
**Creation Date:** August 28, 2026  
**Last Updated:** September 6, 2026  

---

## 1. Hackathon Rule Adherence

### Zero Foreign AI Tools (Disqualification Risk Averted)
Per hackathon rules, only Google Cloud AI tools and partner-track AI integrations are permitted:
- **No OpenAI, Anthropic, AWS, Microsoft, fal, Replicate, ElevenLabs, Runway**, or any other third-party AI or agent framework.
- All dependencies verified via `requirements.txt` and `web/package.json`.

### Permitted Google SDKs Called at Runtime
- `google-genai` (v2.22.0): Used for Vertex AI media pipelines and schema-constrained LLM interpretation.
- `google-adk` (v2.8.0): Official Google Agent Development Kit used for autonomous compilation workflow orchestration.

### Partner Track: ClickHouse
- Write path: `clickhouse-connect` (v1.8.0) driver for high-throughput append-only event writes.
- Read path: Official `@clickhouse/mcp-clickhouse` MCP server via HTTP JSON-RPC 2.0 streamable transport.

---

## 2. Source Code Origin & Clean Implementation

- **New Work Only:** All source code in `CONFORM/` was created from scratch during the hackathon competition period (August 28 – September 9, 2026).
- **No Prior Code Reuse:** No source code was copied or imported from any prior project or external repository.
- **Cache Determinism Architecture:** The JCS canonicalisation (RFC 8785) + SHA-256 fingerprinting core was engineered specifically for generative media pipelines to guarantee cryptographic cache determinism.

---

## 3. Third-Party Non-AI Libraries

All non-AI libraries are standard permissive open-source packages:

### Python Backend
| Library | Version | License | Purpose |
|---|---|---|---|
| `fastapi` | 0.141.0 | MIT | Web framework |
| `uvicorn` | 0.40.0 | BSD-3-Clause | ASGI server |
| `pydantic` | 2.13.0 | MIT | Data contracts & schemas |
| `pytest` | 9.0.0 | MIT | Unit testing suite |
| `httpx` | 0.28.1 | BSD-3-Clause | HTTP test client |
| `ruff` | 0.14.0 | MIT / Apache-2.0 | Linter and code formatter |
| `clickhouse-connect`| 1.8.0 | Apache-2.0 | ClickHouse DB driver |
| `google-genai` | 2.22.0 | Apache-2.0 | Google Cloud GenAI SDK |
| `google-adk` | 2.8.0 | Apache-2.0 | Google Agent Development Kit |
| `google-cloud-storage` | 3.13.1 | Apache-2.0 | GCS artifact client |

### Web Frontend
| Library | Version | License | Purpose |
|---|---|---|---|
| `react` / `react-dom` | 19.2.0 | MIT | UI library |
| `typescript` | 5.9.3 | Apache-2.0 | Type safety |
| `vite` | 7.3.0 | MIT | Frontend build tool |
| `tailwindcss` | 3.4.19 | MIT | Utility CSS styling |
| `recharts` | 2.15.4 | MIT | Telemetry & KPI charting |
| `lucide-react` | 0.562.0 | MIT | UI icons |
| `@radix-ui/*` | Various | MIT | Accessible UI primitives |

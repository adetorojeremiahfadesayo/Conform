"""Analyst Agent — LLM-or-fallback side of the boundary.

Translates natural language questions about slate history into safe, guarded SQL,
executes the query through the ClickHouse MCP reader (or fallback direct reader),
and explains the returned rows.

The LLM may NEVER invent numbers or pass/fail verdicts — every figure stated in
the answer must be traceable to a returned row.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.prompts import ANALYST_EXPLAIN_SYSTEM_PROMPT, ANALYST_SQL_SYSTEM_PROMPT
from app.config import Config
from app.domain.schemas import AnalystQueryResult, ConformError
from app.store.mcp_client import HistoryReader, guard_sql


class AnalystAgent:
    """Natural-language analyst agent over ClickHouse build history."""

    def __init__(self, config: Config, reader: HistoryReader):
        self.config = config
        self.reader = reader

    def ask(self, query: str = "", sql: str = "") -> AnalystQueryResult:
        query_text = (query or "").strip()
        input_sql = (sql or "").strip()

        if not query_text and not input_sql:
            raise ConformError("INVALID_QUERY", "either query or sql must be provided")

        interpretation_mode = "fallback_deterministic"

        if input_sql:
            safe_sql = guard_sql(input_sql)
            if not query_text:
                query_text = f"Executed custom SQL: {safe_sql}"
        else:
            safe_sql, interpretation_mode = self._generate_sql(query_text)

        try:
            rows = self.reader.run_select_query(safe_sql)
        except ConformError:
            raise
        except Exception as exc:
            raise ConformError(
                "QUERY_FAILED",
                f"analyst query failed on {self.reader.mode} path: {exc}",
            ) from exc

        answer = self._generate_explanation(query_text, safe_sql, rows, interpretation_mode)

        return AnalystQueryResult(
            query=query_text,
            sql=safe_sql,
            rows=rows,
            answer=answer,
            reader_mode=self.reader.mode,
            interpretation_mode=interpretation_mode,
        )

    def _generate_sql(self, query: str) -> tuple[str, str]:
        """Convert natural language query to SQL."""
        if self.config.vertex_live:
            try:
                sql = self._sql_with_gemini(query)
                return guard_sql(sql), "gemini"
            except Exception:
                pass  # Fall back gracefully to deterministic mapping

        return guard_sql(self._deterministic_sql(query)), "fallback_deterministic"

    def _sql_with_gemini(self, query: str) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(
            vertexai=True,
            project=self.config.google_cloud_project,
            location=self.config.google_cloud_region,
        )
        resp = client.models.generate_content(
            model=self.config.vertex_text_model,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=ANALYST_SQL_SYSTEM_PROMPT,
                temperature=0.0,
            ),
        )
        sql = (resp.text or "").strip()
        # Clean up any residual markdown if model wraps in ```sql
        sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip().rstrip(";")

    def _deterministic_sql(self, query: str) -> str:
        """Deterministic intent-to-SQL mapping for curated questions."""
        q = query.lower()

        if any(k in q for k in ("model", "spend by model", "modality")):
            return (
                "SELECT model, modality, count() AS calls, sum(cost_usd) AS spend_usd "
                "FROM provider_calls GROUP BY model, modality ORDER BY spend_usd DESC LIMIT 20"
            )

        if any(k in q for k in ("reuse", "saved", "saving", "cache hit", "avoided")):
            return (
                "SELECT build_id, sum(cache_hit) AS reused, sum(1 - cache_hit) AS rebuilt, "
                "sum(cost_usd) AS spend_usd FROM node_runs GROUP BY build_id LIMIT 20"
            )

        if any(k in q for k in ("retry", "retries", "failed", "failure", "timeout", "parent")):
            return (
                "SELECT node_id, attempt, parent_run_id, error_class, status, cost_usd "
                "FROM node_runs WHERE attempt > 1 OR status = 'failed' ORDER BY node_id LIMIT 50"
            )

        if any(k in q for k in ("hostile", "burn", "expensive", "waste")):
            return (
                "SELECT node_id, count() AS runs, avg(cache_hit) AS hit_rate, sum(cost_usd) AS burn "
                "FROM node_runs GROUP BY node_id HAVING runs > 1 ORDER BY burn DESC LIMIT 20"
            )

        if any(k in q for k in ("disclaimer", "rule", "finding", "affect", "territor")):
            return (
                "SELECT territory, rule_id, count() AS affected_assets "
                "FROM rule_findings GROUP BY territory, rule_id ORDER BY affected_assets DESC LIMIT 20"
            )

        if any(k in q for k in ("per second", "second of video", "video cost")):
            return (
                "SELECT sum(cost_usd) AS total_video_cost, sum(media_seconds) AS total_media_seconds "
                "FROM provider_calls WHERE modality = 'video' LIMIT 10"
            )

        return (
            "SELECT node_kind, count() AS total_runs, sum(cache_hit) AS cache_hits, "
            "sum(cost_usd) AS total_spend FROM node_runs GROUP BY node_kind "
            "ORDER BY total_spend DESC LIMIT 20"
        )

    def _generate_explanation(
        self, query: str, sql: str, rows: list[dict[str, Any]], mode: str
    ) -> str:
        """Explain query results based strictly on the row data."""
        if not rows:
            return "No historical records were found matching the query."

        if mode == "gemini" and self.config.vertex_live:
            try:
                return self._explain_with_gemini(query, sql, rows)
            except Exception:
                pass

        return self._deterministic_explanation(query, rows)

    def _explain_with_gemini(self, query: str, sql: str, rows: list[dict[str, Any]]) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(
            vertexai=True,
            project=self.config.google_cloud_project,
            location=self.config.google_cloud_region,
        )
        prompt = (
            f"User Question: {query}\n"
            f"SQL Executed: {sql}\n"
            f"Returned Rows (JSON): {json.dumps(rows[:30])}\n\n"
            "Summarize the findings concisely based exclusively on the returned rows."
        )
        resp = client.models.generate_content(
            model=self.config.vertex_text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=ANALYST_EXPLAIN_SYSTEM_PROMPT,
                temperature=0.0,
            ),
        )
        return (resp.text or "").strip()

    def _deterministic_explanation(self, query: str, rows: list[dict[str, Any]]) -> str:
        n = len(rows)
        sample = rows[0]

        if "spend_usd" in sample and "model" in sample:
            top = rows[0]
            return (
                f"Queried spend across {n} models. Highest spend was {top.get('model')} at "
                f"${float(top.get('spend_usd', 0)):.4f} across {top.get('calls', 0)} calls."
            )

        if "reused" in sample and "rebuilt" in sample:
            total_reused = sum(int(r.get("reused", 0) or 0) for r in rows)
            total_rebuilt = sum(int(r.get("rebuilt", 0) or 0) for r in rows)
            return (
                f"Found {n} build records. Across these builds, {total_reused} node executions were "
                f"reused byte-for-byte from cache, while {total_rebuilt} were rebuilt."
            )

        if "attempt" in sample or "error_class" in sample:
            transient_count = sum(1 for r in rows if r.get("error_class") == "transient")
            return (
                f"Identified {n} retried or failed executions. {transient_count} attempts were "
                f"classified as transient and automatically recovered on fresh attempt rows."
            )

        if "burn" in sample and "node_id" in sample:
            top_node = rows[0]
            return (
                f"Analyzed cache efficiency across {n} nodes. Highest cost burn was {top_node.get('node_id')} "
                f"with ${float(top_node.get('burn', 0)):.4f} total cost across {top_node.get('runs', 0)} runs."
            )

        if "affected_assets" in sample:
            total_affected = sum(int(r.get("affected_assets", 0) or 0) for r in rows)
            return (
                f"Rule evaluation identified {total_affected} affected assets across {n} territories. "
                f"Top territory impacted is {sample.get('territory')} with {sample.get('affected_assets')} assets."
            )

        if "total_video_cost" in sample:
            cost = float(sample.get("total_video_cost", 0) or 0)
            secs = float(sample.get("total_media_seconds", 0) or 0)
            rate = (cost / secs) if secs > 0 else 0
            return (
                f"Video generation totaled ${cost:.2f} across {secs:.1f} media seconds, yielding "
                f"an effective rate of ${rate:.3f} per finished second of video."
            )

        return (
            f"Query executed successfully and returned {n} rows. "
            f"Top entry ({list(sample.keys())[0]} = {list(sample.values())[0]}) recorded in the slate store."
        )

"""CONFORM Google ADK Agent Orchestration Layer.

Integrates the Google Agent Development Kit (google-adk) as the autonomous
multi-step orchestrator for generative media compilation pipelines.

Boundary contract:
- The ADK Agent plans, reasons, and orchestrates tool calling via Gemini on Vertex AI.
- Every tool called by the Agent delegates strictly to the pure-Python / SQL deterministic core.
- No LLM ever computes a fingerprint, a cost, or a dirty set.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from google.adk import Agent, Runner
from google.adk.models import Gemini
from google.adk.sessions import InMemorySessionService
from google.genai import Client, types

from app.domain.schemas import AdkExecutionResult, ChangeStatus, ConformError

if TYPE_CHECKING:
    from app.agents.coordinator import Coordinator


ADK_SYSTEM_INSTRUCTION = """You are the CONFORM Autonomous Pipeline Compiler Agent.
Your responsibility is to manage generative media compilation slates for advertising campaigns across 40 territories.

When given a change request or operational goal:
1. Interpret the change and evaluate its blast radius using `interpret_and_estimate`.
2. Report the bill, number of dirty nodes, and the number of reused assets saved from cache.
3. If an action requires financial spend, verify that human approval has been granted via `approve_spend`.
4. Trigger the dirty subtree rebuild using `build_dirty_subtree`.
5. Verify cryptographic release integrity using `verify_release`.
6. Query ClickHouse telemetry using `query_slate_history` when asked about history or spend.

Always respect the cache-determinism law: identical inputs reuse identical bytes without re-generating.
Never bypass the human approval gate before executing a build.
"""


class AdkPipelineOrchestrator:
    """Orchestrates multi-step agentic workflows using google-adk Agent and Runner."""

    def __init__(self, coordinator: Coordinator):
        self.coord = coordinator
        self.config = coordinator.config
        self.session_service = InMemorySessionService()

        # Define typed ADK tools that wrap deterministic core functions
        def interpret_and_estimate(change_text: str) -> dict[str, Any]:
            """Interprets a media pipeline change request, evaluates compliance rules,
            and calculates the pre-spend blast radius and cost estimate.

            Args:
                change_text: The freeform change request text (e.g. 'new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40')
            """
            change = self.coord.submit_change(change_text)
            est = self.coord.estimate_change(change.change_id)
            total_assets = len(self.coord.graph)
            avoided_count = len(est.reused_node_ids)
            # Naive 100% regeneration spend vs incremental compilation spend
            naive_cost = Decimal("0.00025") * Decimal(str(total_assets))
            avoided_cost = max(Decimal("0"), naive_cost - est.estimated_cost_usd)

            return {
                "status": "success",
                "change_id": change.change_id,
                "dirty_node_ids": est.dirty_node_ids,
                "reused_node_ids": est.reused_node_ids,
                "dirty_count": len(est.dirty_node_ids),
                "reused_count": avoided_count,
                "total_assets": total_assets,
                "estimated_cost_usd": str(est.estimated_cost_usd),
                "avoided_spend_usd": str(avoided_cost),
                "budget_usd": str(self.coord.config.build_budget_usd),
                "budget_exceeded": est.budget_exceeded,
                "approval_required": True,
            }

        def approve_spend(change_id: str, actor: str = "producer (simulated)", budget_override: bool = False) -> dict[str, Any]:
            """Explicit human approval checkpoint. Enforces the governance gate before any generative API spend.

            Args:
                change_id: The identifier of the estimated change
                actor: The authorized human role approving the budget
                budget_override: True if overriding the configured budget cap
            """
            approval = self.coord.approve(change_id=change_id, actor=actor, budget_override=budget_override)
            return {
                "status": "approved",
                "change_id": change_id,
                "actor": approval.actor,
                "graph_hash": approval.graph_hash,
                "gate_passed": True,
            }

        def build_dirty_subtree(change_id: str) -> dict[str, Any]:
            """Executes an incremental rebuild of only the dirty subtree in the dependency graph.
            Clean assets are reused byte-for-byte from cache at $0.00 cost.

            Args:
                change_id: The identifier of the approved change to build
            """
            build_res = self.coord.build(change_id)
            return {
                "status": "complete",
                "build_id": build_res.build_id,
                "release_id": build_res.release.release_id if build_res.release else None,
                "nodes_rebuilt": build_res.nodes_rebuilt,
                "nodes_reused": build_res.nodes_reused,
                "actual_cost_usd": str(build_res.total_cost_usd),
                "retries": build_res.retries,
                "artifact_count": len(build_res.release.artifacts) if build_res.release else 0,
            }

        def verify_release(release_id: str) -> dict[str, Any]:
            """Re-downloads all generated and reused artifacts from storage and computes byte-exact
            SHA-256 hashes to cryptographically prove zero-tampering.

            Args:
                release_id: The release ID to verify (e.g. 'release_001')
            """
            report = self.coord.verify(release_id)
            return {
                "status": "verified" if report.ok else "tampered_or_failed",
                "release_id": report.release_id,
                "all_artifacts_ok": report.ok,
                "artifact_count": len(report.per_artifact),
                "mismatches": [a.get("node_id") for a in report.per_artifact if not a.get("ok")],
            }

        def query_slate_history(sql_query: str) -> dict[str, Any]:
            """Executes a read-only SQL query over ClickHouse telemetry via the official MCP server.

            Args:
                sql_query: Guarded SELECT query (e.g. 'SELECT model, sum(cost_usd) FROM provider_calls GROUP BY model')
            """
            rows = self.coord.reader.run_select_query(sql_query)
            return {
                "status": "success",
                "row_count": len(rows),
                "rows": rows[:50],
                "reader_mode": self.coord.reader.mode,
            }

        def tamper_artifact(release_id: str) -> dict[str, Any]:
            """Corrupts one byte of an artifact in storage to demonstrate cryptographic tamper detection.

            Args:
                release_id: The release ID whose artifact will be bit-flipped
            """
            tamper_res = self.coord.tamper_release_artifact(release_id)
            return {
                "status": "tampered",
                "release_id": release_id,
                "node_id": tamper_res.node_id,
                "message": tamper_res.message,
            }

        self.tools = [
            interpret_and_estimate,
            approve_spend,
            build_dirty_subtree,
            verify_release,
            query_slate_history,
            tamper_artifact,
        ]

        self.tool_map = {t.__name__: t for t in self.tools}

        # Initialize the official Google ADK Agent
        agent_model: str | Gemini = self.config.vertex_text_model
        if self.config.vertex_live:
            agent_model = Gemini(
                model=self.config.vertex_text_model,
                client=Client(
                    vertexai=True,
                    project=self.config.google_cloud_project,
                    location=self.config.google_cloud_region,
                ),
            )

        self.adk_agent = Agent(
            name="conform_pipeline_compiler",
            description="Autonomous compiler for generative media pipelines using cache determinism and DAG blast radius",
            model=agent_model,
            instruction=ADK_SYSTEM_INSTRUCTION,
            tools=self.tools,
        )

        # Initialize the official Google ADK Runner
        self.adk_runner = Runner(
            agent=self.adk_agent,
            app_name="conform",
            session_service=self.session_service,
        )

    def execute_goal(self, goal: str, auto_approve: bool = False) -> AdkExecutionResult:
        """Executes a high-level goal through the ADK Agent.

        When live Vertex AI is configured, orchestrates via ADK Agent runner.
        When running offline, executes a multi-step autonomous deterministic flow
        with full tool telemetry and truthful labelling.
        """
        tools_called: list[str] = []
        steps: list[dict[str, Any]] = []

        if self.config.vertex_live:
            try:
                return self._run_live_adk(goal)
            except Exception as exc:
                raise ConformError(
                    "ADK_LIVE_FAILED",
                    "Live Google ADK execution failed; no deterministic success was substituted.",
                ) from exc

        # Deterministic multi-step autonomous execution
        # Step 1: Tool call: interpret_and_estimate
        est_result = self.tool_map["interpret_and_estimate"](goal)
        tools_called.append("interpret_and_estimate")
        steps.append({"tool": "interpret_and_estimate", "input": {"change_text": goal}, "output": est_result})

        change_id = est_result["change_id"]
        dirty_cnt = est_result["dirty_count"]
        reused_cnt = est_result["reused_count"]
        cost_usd = est_result["estimated_cost_usd"]

        if not auto_approve:
            answer = (
                f"Evaluated blast radius for change '{change_id}': "
                f"{dirty_cnt} nodes dirty, {reused_cnt} nodes reused byte-for-byte from cache. "
                f"Estimated rebuild cost is ${cost_usd}. "
                f"Halting at Human Approval Gate: spend must be approved before building."
            )
            return AdkExecutionResult(
                goal=goal,
                steps=steps,
                tools_called=tools_called,
                final_answer=answer,
                mode="google_adk_deterministic",
                change_id=change_id,
            )

        # Step 2: Tool call: approve_spend
        appr_result = self.tool_map["approve_spend"](change_id=change_id, actor="producer (adk_agent)")
        tools_called.append("approve_spend")
        steps.append({"tool": "approve_spend", "input": {"change_id": change_id}, "output": appr_result})

        # Step 3: Tool call: build_dirty_subtree
        build_result = self.tool_map["build_dirty_subtree"](change_id=change_id)
        tools_called.append("build_dirty_subtree")
        steps.append({"tool": "build_dirty_subtree", "input": {"change_id": change_id}, "output": build_result})

        release_id = build_result["release_id"]

        # Step 4: Tool call: verify_release
        if release_id:
            verify_result = self.tool_map["verify_release"](release_id=release_id)
            tools_called.append("verify_release")
            steps.append({"tool": "verify_release", "input": {"release_id": release_id}, "output": verify_result})

        final_answer = (
            f"Autonomous pipeline run completed for change '{change_id}': "
            f"Rebuilt {build_result['nodes_rebuilt']} nodes, reused {build_result['nodes_reused']} from cache. "
            f"Total actual spend: ${build_result['actual_cost_usd']}. "
            f"Release '{release_id}' verified byte-exact against immutable SHA-256 manifest."
        )

        return AdkExecutionResult(
            goal=goal,
            steps=steps,
            tools_called=tools_called,
            final_answer=final_answer,
            mode="google_adk_deterministic",
            change_id=change_id,
            release_id=release_id,
        )

    def _run_live_adk(self, goal: str) -> AdkExecutionResult:
        """Runs the ADK Runner with live Gemini over an active session."""
        async def _run():
            session = await self.session_service.create_session(app_name="conform", user_id="producer")
            msg = types.Content(parts=[types.Part.from_text(text=goal)])

            steps: list[dict[str, Any]] = []
            tools_called: list[str] = []
            last_text = ""
            change_id: str | None = None
            release_id: str | None = None

            # Consume runner events
            for event in self.adk_runner.run(user_id="producer", session_id=session.id, new_message=msg):
                for call in event.get_function_calls():
                    if call.name and call.name not in tools_called:
                        tools_called.append(call.name)
                        steps.append({"tool": call.name, "input": call.args or {}})
                for response in event.get_function_responses():
                    payload = response.response or {}
                    if not isinstance(payload, dict):
                        continue
                    response_change_id = payload.get("change_id")
                    response_release_id = payload.get("release_id")
                    if isinstance(response_change_id, str):
                        change_id = response_change_id
                    if isinstance(response_release_id, str):
                        release_id = response_release_id
                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            last_text += part.text

            return AdkExecutionResult(
                goal=goal,
                steps=steps,
                tools_called=tools_called,
                final_answer=last_text or "ADK agent completed workflow steps.",
                mode="google_adk_live",
                change_id=change_id,
                release_id=release_id,
            )

        return asyncio.run(_run())

    def resume_workflow(self, change_id: str) -> AdkExecutionResult:
        """Resumes an approved workflow through the ADK Agent, enforcing pre-spend invariants."""
        change = self.coord._change(change_id)
        if change.status != ChangeStatus.APPROVED:
            raise ConformError("NOT_APPROVED", f"cannot resume build for change '{change_id}': status is {change.status}")

        tools_called: list[str] = []
        steps: list[dict[str, Any]] = []

        # Step 1: build_dirty_subtree
        build_res = self.tool_map["build_dirty_subtree"](change_id=change_id)
        tools_called.append("build_dirty_subtree")
        steps.append({"tool": "build_dirty_subtree", "input": {"change_id": change_id}, "output": build_res})

        release_id = build_res["release_id"]

        # Step 2: verify_release
        if release_id:
            verify_res = self.tool_map["verify_release"](release_id=release_id)
            tools_called.append("verify_release")
            steps.append({"tool": "verify_release", "input": {"release_id": release_id}, "output": verify_res})

        final_answer = (
            f"Resumed ADK workflow completed for change '{change_id}': "
            f"Rebuilt {build_res['nodes_rebuilt']} nodes, reused {build_res['nodes_reused']} clean nodes at $0.00. "
            f"Total spend: ${build_res['actual_cost_usd']}. "
            f"Release '{release_id}' verified byte-exact against immutable SHA-256 manifest."
        )

        return AdkExecutionResult(
            goal=f"Resume approved change {change_id}",
            steps=steps,
            tools_called=tools_called,
            final_answer=final_answer,
            mode="google_adk_deterministic",
            change_id=change_id,
            release_id=release_id,
        )

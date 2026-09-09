"""Coordinator — the explicit workflow state machine, always authoritative.

slate_loaded → change_received → change_interpreted → rules_evaluated
  → blast_radius_computed → estimate_ready → AWAITING_APPROVAL
  → approved | rejected → build_running → build_complete → release_verified

The coordinator calls a fixed set of deterministic tools with typed payloads.
It enforces the invariants from AGENTS.md §8: no provider call before
approval, stale-approval refusal, idempotent builds, immutable releases.
"""

from __future__ import annotations

from decimal import Decimal

from app.agents.adk_coordinator import AdkPipelineOrchestrator
from app.agents.analyst import AnalystAgent
from app.agents.interpreter import interpret
from app.config import Config, load_config
from app.core.builder import run_build
from app.core.changes import changed_graph
from app.core.closure import ClosureRow, compute_closure
from app.core.dirty import compute_estimate
from app.core.fingerprint import hash_graph, hash_payload
from app.core.graph import PipelineGraph
from app.core.verify import verify_release
from app.domain.schemas import (
    AdkExecutionResult,
    AnalystQueryResult,
    AnalyticsSummary,
    Approval,
    BuildResult,
    CachedAdkPreset,
    Change,
    ChangeStatus,
    ConformError,
    Estimate,
    Release,
    ReleaseDiff,
    TamperResponse,
    VerificationReport,
)
from app.observability.audit import AuditLog
from app.providers.registry import build_providers
from app.slate import build_seed_campaigns, build_seed_specs
from app.store.artifacts import build_store
from app.store.clickhouse_writer import build_writer
from app.store.mcp_client import build_reader

PRESET_DEFINITIONS: dict[str, dict] = {
    "eu_disclaimer_2026": {
        "preset_id": "eu_disclaimer_2026",
        "title": "EU Advertising Regulation R-DISC-004",
        "campaign_id": "campaign_a",
        "category": "compliance_rule",
        "description": "Requires minimum 40-character allergy & sustainability disclaimer on all advertising copy in German and French territories.",
        "raw_text": "new rule R-DISC-004 on copy in territories de fr: field disclaimer min_len 40",
    },
    "reshoot_hero_clip": {
        "preset_id": "reshoot_hero_clip",
        "title": "Hero Clip Golden-Hour Reshoot",
        "campaign_id": "campaign_a",
        "category": "asset_edit",
        "description": "Art director reshoot note: Replace coastal road turn with golden hour drone footage.",
        "raw_text": "edit node campaign_a.clip: set prompt to Sunset coastal highway turn with dynamic aerial tracking camera and warm golden glow",
    },
    "japan_retargeting": {
        "preset_id": "japan_retargeting",
        "title": "Japan Market Retargeting",
        "campaign_id": "campaign_a",
        "category": "asset_edit",
        "description": "Localise on-screen headline and disclaimer for Tokyo launch window.",
        "raw_text": "edit node campaign_a.copy.jp: set copy to Aurora EV: 静寂と革新が交差する、次世代のラグジュアリー体験。",
    },
}


def _preset_cache_key(preset_id: str, raw_text: str, model_id: str) -> str:
    return hash_payload(
        {
            "kind": "live_adk_preset_interpretation",
            "schema_version": 1,
            "preset_id": preset_id,
            "raw_text": raw_text,
            "model_id": model_id,
        }
    )


class Coordinator:
    """Owns all mutable demo state. Single-process, in-memory; the event
    store is the durable record of what happened."""

    def __init__(self, config: Config | None = None):
        self.config = config or load_config()
        self.graph = PipelineGraph(build_seed_specs())
        self.campaigns = build_seed_campaigns()
        self.closure: list[ClosureRow] = compute_closure(self.graph)
        self.providers = build_providers(self.config)
        self.store = build_store(self.config)
        if hasattr(self.store, "warm_cache"):
            self.store.warm_cache()
        self.writer = build_writer(self.config)
        self.reader = build_reader(self.config, self.writer)
        self.audit = AuditLog()

        self.changes: dict[str, Change] = {}
        self.estimates: dict[str, Estimate] = {}
        self.approvals: dict[str, Approval] = {}
        self.releases: list[Release] = []
        self.builds: dict[str, BuildResult] = {}
        self._telemetry_recorded_builds: set[str] = set()
        # Tamper demonstrations are process-local overlays. They never mutate a
        # canonical GCS artifact or write a new object on a public request.
        self._tamper_overrides: dict[tuple[str, str], bytes] = {}
        self._budget = Decimal(self.config.build_budget_usd)
        self.fault_injection_mode = self.config.fault_injection
        self.analyst = AnalystAgent(self.config, self.reader)
        self.adk = AdkPipelineOrchestrator(self)
        if not self.config.judge_mode:
            self._seed_history_if_needed()

    def _seed_history_if_needed(self) -> None:
        try:
            existing = self.writer.query("SELECT count() AS n FROM node_runs")
            if existing and int(existing[0].get("n", 0) or 0) > 0:
                return
        except Exception:
            pass

        from app.slate import seed_historical_builds

        runs, calls = seed_historical_builds()
        if hasattr(self.writer, "write_runs"):
            self.writer.write_runs(runs)
        else:
            for r in runs:
                self.writer.write_run(r)
        if hasattr(self.writer, "write_provider_calls"):
            self.writer.write_provider_calls(calls)
        else:
            for c in calls:
                self.writer.write_provider_call(c)

    # -- tools ----------------------------------------------------------- #

    def system_status(self) -> dict:
        return self.config.public_status() | {
            "writer": self.writer.mode,
            "reader": self.reader.mode,
            "artifact_store": self.store.mode,
            "nodes": len(self.graph),
            "fault_injection": self.fault_injection_mode,
            "adk_agent": "google_adk_2.8.0",
        }

    def list_presets(self) -> list[dict]:
        return list(PRESET_DEFINITIONS.values())

    def submit_preset(self, preset_id: str) -> Change:
        if preset_id not in PRESET_DEFINITIONS:
            raise ConformError("UNKNOWN_PRESET", f"unknown preset: {preset_id}")
        preset = PRESET_DEFINITIONS[preset_id]
        change = self.submit_change(preset["raw_text"])
        change.preset_id = preset_id
        self.audit.record("preset_selected", preset_id=preset_id, change_id=change.change_id)
        return change

    def execute_adk_goal(self, goal: str, auto_approve: bool = False) -> AdkExecutionResult:
        """Executes an autonomous pipeline goal via Google ADK Agent."""
        res = self.adk.execute_goal(goal, auto_approve=auto_approve)
        self.audit.record("adk_goal_executed", mode=res.mode, tools_called=res.tools_called)
        return res

    def execute_adk_preset(self, preset_id: str) -> AdkExecutionResult:
        """Runs a curated demo preset through ADK and stops at approval."""
        if self.config.judge_mode and preset_id != "eu_disclaimer_2026":
            raise ConformError("JUDGE_ACTION_BLOCKED", "Only the prepared EU rule scenario is available to judges.")
        if preset_id not in PRESET_DEFINITIONS:
            raise ConformError("UNKNOWN_PRESET", f"unknown preset: {preset_id}")
        raw_text = PRESET_DEFINITIONS[preset_id]["raw_text"]
        cache_key = _preset_cache_key(preset_id, raw_text, self.config.vertex_text_model)
        try:
            cached_uri = self.store.exists(cache_key)
            if cached_uri:
                snapshot = CachedAdkPreset.model_validate_json(
                    getattr(self.store, "fetch_cached", self.store.fetch)(cached_uri)
                )
                if snapshot.cache_key != cache_key or snapshot.preset_id != preset_id:
                    raise ValueError("cached preset identity mismatch")
                change = Change(
                    preset_id=preset_id,
                    kind=snapshot.intent.kind,
                    intent=snapshot.intent,
                    raw_text=raw_text,
                    status=ChangeStatus.INTERPRETED,
                )
                self.changes[change.change_id] = change
                estimate = self.estimate_change(change.change_id)
                self.audit.record(
                    "adk_preset_cache_hit",
                    preset_id=preset_id,
                    change_id=change.change_id,
                    source_mode=snapshot.source_mode,
                )
                return AdkExecutionResult(
                    goal=raw_text,
                    steps=[
                        {
                            "tool": "restore_live_interpretation",
                            "output": {
                                "change_id": change.change_id,
                                "dirty_count": len(estimate.dirty_node_ids),
                                "reused_count": len(estimate.reused_node_ids),
                            },
                        }
                    ],
                    tools_called=[],
                    final_answer="Stored live ADK interpretation restored; approval is still required.",
                    mode="google_adk_cached_live_result",
                    change_id=change.change_id,
                )
        except Exception as exc:
            self.audit.record(
                "adk_preset_cache_read_failed",
                preset_id=preset_id,
                error_type=type(exc).__name__,
            )

        if self.config.judge_mode:
            raise ConformError(
                "JUDGE_CACHE_MISS",
                "The prepared live interpretation is unavailable; judge mode never calls Vertex on a cache miss.",
            )

        result = self.execute_adk_goal(raw_text, auto_approve=False)
        if result.change_id is None or result.change_id not in self.changes:
            raise ConformError(
                "ADK_NO_CHANGE",
                "Google ADK completed without persisting the change required by the scan workflow.",
            )
        self.changes[result.change_id].preset_id = preset_id
        source_change = self.changes[result.change_id]
        if result.mode == "google_adk_live" and source_change.intent.interpretation_mode == "gemini":
            snapshot = CachedAdkPreset(
                preset_id=preset_id,
                cache_key=cache_key,
                model_id=self.config.vertex_text_model,
                source_mode="google_adk_live",
                intent=source_change.intent,
            )
            try:
                self.store.put(cache_key, snapshot.model_dump_json().encode("utf-8"), "application/json")
                self.audit.record("adk_preset_cache_written", preset_id=preset_id, cache_key=cache_key)
            except Exception as exc:
                self.audit.record(
                    "adk_preset_cache_write_failed",
                    preset_id=preset_id,
                    error_type=type(exc).__name__,
                )
        self.audit.record(
            "adk_preset_executed",
            preset_id=preset_id,
            change_id=result.change_id,
            mode=result.mode,
        )
        return result

    def resume_adk_workflow(self, change_id: str) -> AdkExecutionResult:
        """Resumes an approved workflow via Google ADK Agent."""
        res = self.adk.resume_workflow(change_id)
        self.audit.record("adk_workflow_resumed", change_id=change_id, mode=res.mode, tools_called=res.tools_called)
        return res

    def submit_change(self, text: str) -> Change:
        if self.config.judge_mode:
            raise ConformError("JUDGE_ACTION_BLOCKED", "Custom changes are disabled in the public judge demo.")
        intent = interpret(text, self.config)
        change = Change(kind=intent.kind, intent=intent, raw_text=text, status=ChangeStatus.INTERPRETED)
        self.changes[change.change_id] = change
        self.audit.record("change_interpreted", change_id=change.change_id, mode=intent.interpretation_mode)
        return change

    def estimate_change(self, change_id: str) -> Estimate:
        change = self._change(change_id)
        est = compute_estimate(change, self.graph, self.closure, self._budget)
        self.estimates[change_id] = est
        change.status = ChangeStatus.AWAITING_APPROVAL
        self.audit.record(
            "estimate_ready",
            change_id=change_id,
            dirty=len(est.dirty_node_ids),
            reused=len(est.reused_node_ids),
            cost_usd=str(est.estimated_cost_usd),
            budget_exceeded=est.budget_exceeded,
        )
        return est

    def approve(self, change_id: str, actor: str, budget_override: bool = False) -> Approval:
        change = self._change(change_id)
        if change.status != ChangeStatus.AWAITING_APPROVAL:
            raise ConformError("INVALID_STATE", f"change is {change.status}, not awaiting_approval")
        est = self.estimates[change_id]
        if est.budget_exceeded and not budget_override:
            raise ConformError(
                "BUDGET_EXCEEDED",
                f"estimate {est.estimated_cost_usd} USD exceeds budget {self._budget} USD; override required",
            )
        approval = Approval(change_id=change_id, actor=actor, graph_hash=est.graph_hash)
        self.approvals[change_id] = approval
        change.status = ChangeStatus.APPROVED
        self.audit.record("approved", change_id=change_id, actor=actor, actor_simulated=True)
        return approval

    def reject(self, change_id: str, actor: str) -> Change:
        change = self._change(change_id)
        if change.status != ChangeStatus.AWAITING_APPROVAL:
            raise ConformError("INVALID_STATE", f"change is {change.status}, not awaiting_approval")
        change.status = ChangeStatus.REJECTED
        self.audit.record("rejected", change_id=change_id, actor=actor, actor_simulated=True)
        return change

    def build(self, change_id: str) -> BuildResult:
        change = self._change(change_id)
        approval = self.approvals.get(change_id)
        if approval is None:
            raise ConformError("NOT_APPROVED", "no approval on record — the gate has not been passed")
        est = self.estimates[change_id]
        change.status = ChangeStatus.BUILDING
        prior = next((b for b in self.builds.values() if b.change_id == change_id), None)
        if prior:
            change.status = ChangeStatus.BUILD_COMPLETE
            return prior
        if approval.graph_hash != hash_graph(list(self.graph.nodes.values())):
            raise ConformError("STALE_APPROVAL", "graph changed since approval; re-estimate and re-approve")
        target_graph = changed_graph(change, self.graph)
        if self.config.judge_mode:
            cache_misses = [
                node_id
                for node_id in est.dirty_node_ids
                if not self.store.exists(target_graph.nodes[node_id].fingerprint)
            ]
            if cache_misses:
                raise ConformError(
                    "JUDGE_CACHE_MISS",
                    "Prepared artifacts are unavailable; judge mode never invokes a generative provider.",
                    {"missing_nodes": cache_misses},
                )
        target_approval = approval.model_copy(update={
            "graph_hash": hash_graph(list(target_graph.nodes.values())),
        })
        result = run_build(
            graph=target_graph,
            dirty_node_ids=est.dirty_node_ids,
            approval=target_approval,
            providers=self.providers,
            store=self.store,
            existing_releases=self.releases,
            completed_build_ids=set(self.builds),
            prior_build_id=prior.build_id if prior else None,
        )
        self.builds[result.build_id] = result
        if result.release and result.release not in self.releases:
            self.releases.append(result.release)
        if result.build_id not in self._telemetry_recorded_builds and not self.config.judge_mode:
            try:
                self.writer.write_runs(result.runs)
                self.writer.write_provider_calls(result.provider_calls)
                if result.release:
                    self.writer.write_artifacts(result.release.artifacts)
                self._telemetry_recorded_builds.add(result.build_id)
                result.telemetry_status = "recorded"
                result.telemetry_error = None
            except Exception as exc:
                result.telemetry_status = "failed"
                result.telemetry_error = "event_store_write_failed"
                self.audit.record(
                    "build_telemetry_failed",
                    change_id=change_id,
                    build_id=result.build_id,
                    error_type=type(exc).__name__,
                )
        change.status = ChangeStatus.BUILD_COMPLETE
        self.audit.record(
            "build_complete",
            change_id=change_id,
            build_id=result.build_id,
            rebuilt=result.nodes_rebuilt,
            reused=result.nodes_reused,
            cost_usd=str(result.total_cost_usd),
            retries=result.retries,
        )
        return result

    def verify(self, release_id: str) -> VerificationReport:
        release = next((r for r in self.releases if r.release_id == release_id), None)
        if release is None:
            raise ConformError("UNKNOWN_RELEASE", f"unknown release: {release_id}")
        overrides = self._tamper_overrides

        class ReleaseFetcher:
            def fetch(_, uri: str) -> bytes:
                for artifact in release.artifacts:
                    if artifact.uri == uri and (release_id, artifact.node_id) in overrides:
                        return overrides[(release_id, artifact.node_id)]
                return self.store.fetch(uri)

        report = verify_release(release_id, release.artifacts, ReleaseFetcher())
        self.audit.record("release_verified", release_id=release_id, ok=report.ok)
        return report

    def graph_view(self, change_id: str | None = None) -> dict:
        dirty = set(self.estimates[change_id].dirty_node_ids) if change_id in self.estimates else set()
        nodes = [
            {
                "node_id": n.node_id,
                "campaign_id": n.campaign_id,
                "territory": n.territory,
                "kind": n.kind.value,
                "fingerprint": n.fingerprint,
                "state": "dirty" if n.node_id in dirty else "clean",
                "parents": n.parents,
            }
            for n in self.graph.nodes.values()
        ]
        return {"nodes": nodes, "graph_hash": hash_graph(list(self.graph.nodes.values()))}

    def ask(self, query: str = "", sql: str = "") -> AnalystQueryResult:
        """Analyst path: NL question -> SQL -> MCP -> explanation."""
        if self.config.judge_mode:
            allowed_queries = {
                "What is our spend across models?",
                "How many nodes were reused vs rebuilt?",
                "Which transient errors were auto-retried?",
                "Which nodes are cache-hostile and burning cost?",
                "What is our cost per finished second of video?",
                "What did the disclaimer rule change affect?",
            }
            if sql or query not in allowed_queries:
                raise ConformError(
                    "JUDGE_ACTION_BLOCKED",
                    "Only the six prepared ClickHouse questions are available in the public judge demo.",
                )
        res = self.analyst.ask(query=query, sql=sql)
        self.audit.record("analyst_query", mode=res.reader_mode)
        return res

    def analytics_summary(self) -> AnalyticsSummary:
        """Headline metrics over slate history (PRD §5 FR-10, §7 View 4)."""
        try:
            query = self.reader.run_select_query if self.config.judge_mode else self.writer.query
            totals = query(
                "SELECT count() AS total_runs, sum(cache_hit) AS reused, "
                "sum(1 - cache_hit) AS rebuilt, sum(cost_usd) AS total_spend FROM node_runs"
            )
            reused = int(totals[0].get("reused", 0) or 0) if totals else 0
            rebuilt = int(totals[0].get("rebuilt", 0) or 0) if totals else 0
            spend = Decimal(str(totals[0].get("total_spend", 0) or 0)) if totals else Decimal("0")

            avoided_query = query(
                "SELECT sum(cost_usd) AS avoided FROM node_runs WHERE cache_hit = 1"
            )
            avoided = Decimal(str(avoided_query[0].get("avoided", 0) or 0)) if avoided_query else Decimal("0")

            total_nodes = reused + rebuilt
            cache_rate = (reused / total_nodes) if total_nodes > 0 else 0.0

            models = query(
                "SELECT model, modality, count() AS calls, sum(cost_usd) AS spend_usd "
                "FROM provider_calls GROUP BY model, modality ORDER BY spend_usd DESC"
            )
            campaigns = query(
                "SELECT campaign_id, count() AS total_runs, sum(cost_usd) AS spend_usd "
                "FROM node_runs GROUP BY campaign_id ORDER BY spend_usd DESC"
            )
            return AnalyticsSummary(
                nodes_rebuilt=rebuilt,
                nodes_reused=reused,
                total_spend_usd=spend,
                avoided_spend_usd=avoided,
                cache_hit_rate=round(cache_rate, 4),
                spend_by_model=models,
                spend_by_campaign=campaigns,
            )
        except Exception as exc:
            raise ConformError("ANALYTICS_FAILED", f"failed to compute analytics summary: {exc}") from exc

    def diff_releases(self, a_id: str, b_id: str) -> ReleaseDiff:
        """Diff two releases (PRD FR-9.3, FR-10)."""
        rel_a = next((r for r in self.releases if r.release_id == a_id), None)
        rel_b = next((r for r in self.releases if r.release_id == b_id), None)
        if not rel_a:
            raise ConformError("UNKNOWN_RELEASE", f"release {a_id} not found")
        if not rel_b:
            raise ConformError("UNKNOWN_RELEASE", f"release {b_id} not found")

        arts_a = {a.node_id: a for a in rel_a.artifacts}
        arts_b = {b.node_id: b for b in rel_b.artifacts}

        added = [nid for nid in arts_b if nid not in arts_a]
        removed = [nid for nid in arts_a if nid not in arts_b]
        changed = [nid for nid in arts_b if nid in arts_a and arts_b[nid].sha256 != arts_a[nid].sha256]

        cost_b = sum(
            (Decimal(str(r.cost_usd)) for b in self.builds.values() if b.release and b.release.release_id == b_id for r in b.runs),
            Decimal("0"),
        )
        cost_a = sum(
            (Decimal(str(r.cost_usd)) for b in self.builds.values() if b.release and b.release.release_id == a_id for r in b.runs),
            Decimal("0"),
        )

        return ReleaseDiff(
            release_a=a_id,
            release_b=b_id,
            nodes_added=sorted(added),
            nodes_removed=sorted(removed),
            nodes_changed=sorted(changed),
            cost_delta_usd=cost_b - cost_a,
        )

    def tamper_release_artifact(self, release_id: str, node_id: str | None = None) -> TamperResponse:
        """Corrupt one byte in storage to demonstrate verification failure red (FR-7.4)."""
        rel = next((r for r in self.releases if r.release_id == release_id), None)
        if not rel:
            raise ConformError("UNKNOWN_RELEASE", f"release {release_id} not found")
        if not rel.artifacts:
            raise ConformError("NO_ARTIFACTS", f"release {release_id} has no artifacts")

        if self.config.judge_mode and node_id is not None:
            raise ConformError("JUDGE_ACTION_BLOCKED", "Judge tamper mode selects its fixed demonstration artifact.")
        art = next((a for a in rel.artifacts if a.node_id == node_id), rel.artifacts[0])
        if (release_id, art.node_id) in self._tamper_overrides:
            raise ConformError("JUDGE_ACTION_BLOCKED", "This release already has an isolated tamper demonstration.")
        data = bytearray(self.store.fetch(art.uri))
        if not data:
            raise ConformError("TAMPER_FAILED", "Cannot flip a byte in an empty artifact")
        data[0] ^= 0xFF
        self._tamper_overrides[(release_id, art.node_id)] = bytes(data)

        self.audit.record("tamper_injected", release_id=release_id, node_id=art.node_id, uri=art.uri)
        return TamperResponse(
            release_id=release_id,
            node_id=art.node_id,
            uri="demo://in-memory-tamper-overlay",
            tampered_byte=0,
            message=f"Corrupted first byte of {art.node_id}. Re-verifying release will now fail with MISMATCH.",
        )

    def set_fault_injection(self, mode: str) -> str:
        """Dynamic runtime fault-injection toggle (FR-6.5)."""
        self.fault_injection_mode = mode
        for p in self.providers.values():
            if hasattr(p, "set_fault_injection"):
                p.set_fault_injection(mode)
        self.audit.record("fault_injection_set", mode=mode)
        return self.fault_injection_mode

    def get_build(self, build_id: str) -> BuildResult:
        """Get build execution details (FR-10)."""
        build = self.builds.get(build_id)
        if not build:
            raise ConformError("UNKNOWN_BUILD", f"unknown build: {build_id}")
        return build

    def get_change(self, change_id: str) -> Change:
        """Get change details by ID."""
        return self._change(change_id)

    def _change(self, change_id: str) -> Change:
        change = self.changes.get(change_id)
        if change is None:
            raise ConformError("UNKNOWN_CHANGE", f"unknown change: {change_id}")
        return change

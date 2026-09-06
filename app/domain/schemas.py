"""All pydantic contracts for CONFORM — the single source of truth.

Every cross-module payload is a model defined here. Agents communicate through
these types only; the coordinator calls a fixed set of tools with typed args
and results. Nothing cross-boundary is a bare dict.

Boundary note: LLMs may produce *interpretation* payloads (ChangeIntent) but
every numeric, fingerprint, dirty-set, and verdict field is computed by the
deterministic core — never by a model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class NodeKind(str, Enum):
    SOURCE = "source"
    SHOT_PLAN = "shot_plan"
    KEYFRAME = "keyframe"
    CLIP = "clip"
    COPY = "copy"
    VOICEOVER = "voiceover"
    MUSIC = "music"
    PACKAGE = "package"


class NodeStatus(str, Enum):
    CLEAN = "clean"
    DIRTY = "dirty"
    REUSED = "reused"
    BUILDING = "building"
    BUILT = "built"
    FAILED = "failed"


class ChangeStatus(str, Enum):
    RECEIVED = "received"
    INTERPRETED = "interpreted"
    EVALUATED = "evaluated"
    ESTIMATED = "estimated"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    BUILDING = "building"
    BUILD_COMPLETE = "build_complete"
    VERIFIED = "verified"
    STALE = "stale"


class ChangeKind(str, Enum):
    RULE_CHANGE = "rule_change"   # new / edited / removed demo rule
    ASSET_EDIT = "asset_edit"     # direct edit to a node's inputs


class RuleOp(str, Enum):
    NEW = "new"
    EDIT = "edit"
    REMOVE = "remove"


class ErrorClass(str, Enum):
    NONE = "none"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    POLICY = "policy"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


# --------------------------------------------------------------------------- #
# Graph nodes and campaigns
# --------------------------------------------------------------------------- #


class NodeSpec(BaseModel):
    """Definition of one pipeline node as authored (before fingerprinting).

    `inputs` are the semantic inputs (prompt text, parameters); `recipe` is the
    exact generation recipe (model id, seed, sampler params). Both feed the
    fingerprint. `parents` are node_ids this node consumes.
    """

    node_id: str
    campaign_id: str
    territory: str = "master"
    kind: NodeKind
    inputs: dict[str, Any] = Field(default_factory=dict)
    recipe: dict[str, Any] = Field(default_factory=dict)
    parents: list[str] = Field(default_factory=list)


class Node(NodeSpec):
    """A NodeSpec plus its computed fingerprint and current build state."""

    fingerprint: str = ""
    status: NodeStatus = NodeStatus.CLEAN

    @field_validator("fingerprint")
    @classmethod
    def _fp_shape(cls, v: str) -> str:
        if v and (len(v) != 64 or v != v.lower()):
            raise ValueError("fingerprint must be 64 lowercase hex chars")
        return v


class TerritoryVariant(BaseModel):
    territory: str
    locale: str = "en"
    overrides: dict[str, Any] = Field(default_factory=dict)


class CampaignSpec(BaseModel):
    """Interpretation contract for a campaign brief (LLM-producible, then
    strictly validated before anything downstream touches it)."""

    campaign_id: str
    name: str
    brief: str = ""
    territories: list[TerritoryVariant] = Field(default_factory=list)
    nodes: list[NodeSpec] = Field(default_factory=list)
    interpretation_mode: Literal["gemini", "fallback_deterministic"] = "fallback_deterministic"
    deferred_requirements: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #


class Rule(BaseModel):
    """A deterministic demo rule. `predicate` is a small declarative spec the
    rule engine evaluates — never arbitrary code, never LLM output."""

    rule_id: str
    name: str
    description: str = ""
    node_kinds: list[NodeKind] = Field(default_factory=list)
    territories: list[str] = Field(default_factory=list)  # empty = all territories
    predicate: dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.WARNING


class RuleSet(BaseModel):
    version: str = "1"
    rules: list[Rule] = Field(default_factory=list)


class Finding(BaseModel):
    """A deterministic rule finding with evidence. Advisory — never self-applies."""

    change_id: str
    rule_id: str
    node_id: str
    territory: str
    severity: Severity
    reason: str
    detected_at: datetime = Field(default_factory=_utcnow)


# --------------------------------------------------------------------------- #
# Changes, estimates, approvals
# --------------------------------------------------------------------------- #


class ChangeIntent(BaseModel):
    """Typed interpretation of a free-text change request. This is the ONLY
    payload an LLM may author; it is validated and then handed to the
    deterministic engines, which compute everything else."""

    kind: ChangeKind
    rule_op: RuleOp | None = None
    rule: Rule | None = None                    # for NEW / EDIT
    rule_id: str | None = None                  # for REMOVE
    node_id: str | None = None                  # for ASSET_EDIT
    new_inputs: dict[str, Any] | None = None    # for ASSET_EDIT
    deferred_requirements: list[str] = Field(default_factory=list)
    interpretation_mode: Literal["gemini", "fallback_deterministic"] = "fallback_deterministic"


class Change(BaseModel):
    change_id: str = Field(default_factory=lambda: _new_id("change"))
    preset_id: str | None = None
    kind: ChangeKind
    intent: ChangeIntent
    status: ChangeStatus = ChangeStatus.RECEIVED
    received_at: datetime = Field(default_factory=_utcnow)
    raw_text: str = ""


class ModelBreakdown(BaseModel):
    model: str
    modality: str
    node_count: int
    cost_usd: Decimal


class DirtyReason(str, Enum):
    """Why a node is in the blast radius. A rebuild is never unexplained —
    every dirty node carries a reason code the UI shows verbatim."""

    NODE_SPEC_CHANGED = "NODE_SPEC_CHANGED"
    RULE_SCOPE_HIT = "RULE_SCOPE_HIT"
    UPSTREAM_FINGERPRINT_CHANGED = "UPSTREAM_FINGERPRINT_CHANGED"


class DirtyNode(BaseModel):
    node_id: str
    depth: int
    reason: DirtyReason


class Estimate(BaseModel):
    """Deterministic blast-radius + cost estimate. `graph_hash` pins the exact
    graph state this estimate was computed against; a build refuses to run if
    the graph has since changed."""

    change_id: str
    dirty_node_ids: list[str]
    dirty_nodes: list[DirtyNode] = Field(default_factory=list)
    reused_node_ids: list[str]
    estimated_cost_usd: Decimal
    estimated_seconds: float
    per_model: list[ModelBreakdown] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    graph_hash: str
    budget_exceeded: bool = False
    computed_at: datetime = Field(default_factory=_utcnow)


class Approval(BaseModel):
    approval_id: str = Field(default_factory=lambda: _new_id("approval"))
    change_id: str
    actor: str  # simulated role, labelled as simulated in audit + UI
    actor_is_simulated: bool = True
    graph_hash: str
    approved_at: datetime = Field(default_factory=_utcnow)


# --------------------------------------------------------------------------- #
# Builds, runs, releases
# --------------------------------------------------------------------------- #


class ProviderCallRecord(BaseModel):
    run_id: str
    build_id: str
    model: str
    modality: str
    region: str = ""
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    media_seconds: float = 0.0
    cost_usd: Decimal = Decimal("0")
    http_status: int = 200
    retryable: bool = False
    is_seeded: bool = False
    called_at: datetime = Field(default_factory=_utcnow)


class NodeRunRecord(BaseModel):
    tenant: str = "demo"
    campaign_id: str
    territory: str
    build_id: str
    run_id: str = Field(default_factory=lambda: _new_id("run"))
    parent_run_id: str | None = None
    node_id: str
    node_kind: NodeKind
    fingerprint: str
    inputs_hash: str = ""
    recipe_hash: str = ""
    status: Literal["ok", "failed", "skipped", "running"] = "running"
    cache_hit: bool = False
    attempt: int = 1
    error_class: ErrorClass = ErrorClass.NONE
    is_seeded: bool = False
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: datetime | None = None
    duration_ms: int = 0
    cost_usd: Decimal = Decimal("0")
    bytes_out: int = 0


class ArtifactRecord(BaseModel):
    fingerprint: str
    build_id: str
    node_id: str
    uri: str
    sha256: str
    bytes: int
    content_type: str
    verify_ok: bool | None = None
    verified_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class Release(BaseModel):
    """Immutable. A new build always produces a new release; existing releases
    are never mutated."""

    release_id: str
    build_id: str
    change_id: str
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class BuildResult(BaseModel):
    build_id: str
    change_id: str
    release: Release | None = None
    runs: list[NodeRunRecord] = Field(default_factory=list)
    provider_calls: list[ProviderCallRecord] = Field(default_factory=list)
    nodes_rebuilt: int = 0
    nodes_reused: int = 0
    total_cost_usd: Decimal = Decimal("0")
    retries: int = 0


class VerificationReport(BaseModel):
    release_id: str
    ok: bool
    per_artifact: list[dict[str, Any]] = Field(default_factory=list)
    verified_at: datetime = Field(default_factory=_utcnow)


class AnalystQueryRequest(BaseModel):
    query: str = ""
    sql: str = ""


class AnalystQueryResult(BaseModel):
    query: str
    sql: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    answer: str
    reader_mode: str
    interpretation_mode: str = "fallback_deterministic"


class AnalyticsSummary(BaseModel):
    nodes_rebuilt: int = 0
    nodes_reused: int = 0
    total_spend_usd: Decimal = Decimal("0")
    avoided_spend_usd: Decimal = Decimal("0")
    cache_hit_rate: float = 0.0
    spend_by_model: list[dict[str, Any]] = Field(default_factory=list)
    spend_by_campaign: list[dict[str, Any]] = Field(default_factory=list)


class ReleaseDiff(BaseModel):
    release_a: str
    release_b: str
    nodes_added: list[str] = Field(default_factory=list)
    nodes_removed: list[str] = Field(default_factory=list)
    nodes_changed: list[str] = Field(default_factory=list)
    cost_delta_usd: Decimal = Decimal("0")


class TamperResponse(BaseModel):
    release_id: str
    node_id: str
    uri: str
    tampered_byte: int
    message: str


class FaultInjectionRequest(BaseModel):
    mode: Literal["off", "transient_once"] = "off"


class AdkExecuteRequest(BaseModel):
    goal: str
    auto_approve: bool = False


class AdkResumeRequest(BaseModel):
    change_id: str


class AdkExecutionResult(BaseModel):
    goal: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    tools_called: list[str] = Field(default_factory=list)
    final_answer: str
    mode: str = "google_adk_deterministic"
    change_id: str | None = None
    release_id: str | None = None


# --------------------------------------------------------------------------- #
# API error envelope
# --------------------------------------------------------------------------- #


class ApiError(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


class ConformError(Exception):
    """Typed failure. Every tool failure surfaces as one of these — never an
    invented success, never a bare exception across an API boundary."""

    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None):
        super().__init__(message)
        self.error = ApiError(code=code, message=message, detail=detail or {})

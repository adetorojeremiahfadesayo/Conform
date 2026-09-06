"""CONFORM API — FastAPI surface for the demo workflow.

All endpoints return typed pydantic payloads. Domain failures arrive as
ConformError and map to a consistent ApiError envelope with the right status.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents.coordinator import Coordinator
from app.api.deps import get_coordinator
from app.domain.schemas import AdkExecuteRequest, AdkResumeRequest, ConformError

_STATUS_BY_CODE = {
    "UNKNOWN_CHANGE": 404,
    "UNKNOWN_PRESET": 404,
    "UNKNOWN_RELEASE": 404,
    "UNKNOWN_NODE": 404,
    "UNKNOWN_BUILD": 404,
    "INVALID_STATE": 409,
    "STALE_APPROVAL": 409,
    "BUDGET_EXCEEDED": 422,
    "QUERY_FAILED": 422,
    "NOT_APPROVED": 409,
    "PARSE_FAILED": 422,
    "SQL_NOT_SELECT": 422,
    "SQL_MULTI_STATEMENT": 422,
    "SQL_FORBIDDEN_KEYWORD": 422,
    "ANALYTICS_FAILED": 500,
    "TAMPER_FAILED": 500,
    "NO_ARTIFACTS": 400,
}


class ChangeRequest(BaseModel):
    text: str


class ApproveRequest(BaseModel):
    actor: str = "producer (simulated)"
    budget_override: bool = False


class RejectRequest(BaseModel):
    actor: str = "producer (simulated)"


class AskRequest(BaseModel):
    query: str = ""
    sql: str = ""


class TamperApiRequest(BaseModel):
    release_id: str
    node_id: str | None = None


class FaultInjectionApiRequest(BaseModel):
    mode: str


def create_app() -> FastAPI:
    app = FastAPI(title="CONFORM", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ConformError)
    async def conform_error_handler(_: Request, exc: ConformError) -> JSONResponse:
        status = _STATUS_BY_CODE.get(exc.error.code, 500)
        return JSONResponse(status_code=status, content=exc.error.model_dump())

    @app.get("/api/system/status")
    def system_status(coord: Coordinator = Depends(get_coordinator)):
        return coord.system_status()

    @app.get("/api/system/fault-injection")
    def get_fault_injection(coord: Coordinator = Depends(get_coordinator)):
        return {"mode": coord.fault_injection_mode}

    @app.post("/api/system/fault-injection")
    def set_fault_injection(req: FaultInjectionApiRequest, coord: Coordinator = Depends(get_coordinator)):
        return {"mode": coord.set_fault_injection(req.mode)}

    @app.post("/api/system/tamper")
    def tamper_artifact(req: TamperApiRequest, coord: Coordinator = Depends(get_coordinator)):
        return coord.tamper_release_artifact(req.release_id, req.node_id).model_dump(mode="json")

    @app.get("/api/campaigns")
    def campaigns(coord: Coordinator = Depends(get_coordinator)):
        return [c.model_dump(mode="json") for c in coord.campaigns]

    @app.get("/api/graph")
    def graph(change_id: str | None = None, coord: Coordinator = Depends(get_coordinator)):
        return coord.graph_view(change_id)

    @app.get("/api/presets")
    def list_presets(coord: Coordinator = Depends(get_coordinator)):
        return coord.list_presets()

    @app.post("/api/presets/{preset_id}/changes", status_code=201)
    def submit_preset(preset_id: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.submit_preset(preset_id).model_dump(mode="json")

    @app.post("/api/changes", status_code=201)
    def submit_change(req: ChangeRequest, coord: Coordinator = Depends(get_coordinator)):
        return coord.submit_change(req.text).model_dump(mode="json")

    @app.get("/api/changes/{change_id}")
    def get_change(change_id: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.get_change(change_id).model_dump(mode="json")

    @app.post("/api/changes/{change_id}/estimate")
    def estimate(change_id: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.estimate_change(change_id).model_dump(mode="json")

    @app.post("/api/changes/{change_id}/approve")
    def approve(change_id: str, req: ApproveRequest, coord: Coordinator = Depends(get_coordinator)):
        return coord.approve(change_id, req.actor, req.budget_override).model_dump(mode="json")

    @app.post("/api/changes/{change_id}/reject")
    def reject(change_id: str, req: RejectRequest, coord: Coordinator = Depends(get_coordinator)):
        return coord.reject(change_id, req.actor).model_dump(mode="json")

    @app.post("/api/changes/{change_id}/build", status_code=201)
    def build(change_id: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.build(change_id).model_dump(mode="json")

    @app.get("/api/builds/{build_id}")
    def get_build(build_id: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.get_build(build_id).model_dump(mode="json")

    @app.get("/api/releases")
    def releases(coord: Coordinator = Depends(get_coordinator)):
        return [r.model_dump(mode="json") for r in coord.releases]

    @app.get("/api/releases/{release_id}/verify")
    def verify(release_id: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.verify(release_id).model_dump(mode="json")

    @app.get("/api/releases/{a}/diff/{b}")
    def diff_releases(a: str, b: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.diff_releases(a, b).model_dump(mode="json")

    @app.post("/api/analytics/ask")
    def ask(req: AskRequest, coord: Coordinator = Depends(get_coordinator)):
        return coord.ask(query=req.query, sql=req.sql).model_dump(mode="json")

    @app.get("/api/analytics/summary")
    def analytics_summary(coord: Coordinator = Depends(get_coordinator)):
        return coord.analytics_summary().model_dump(mode="json")

    @app.get("/api/audit")
    def audit(coord: Coordinator = Depends(get_coordinator)):
        return coord.audit.tail()

    @app.post("/api/agents/adk/execute")
    def adk_execute(req: AdkExecuteRequest, coord: Coordinator = Depends(get_coordinator)):
        return coord.execute_adk_goal(req.goal, auto_approve=req.auto_approve).model_dump(mode="json")

    @app.post("/api/agents/adk/resume")
    def adk_resume(req: AdkResumeRequest, coord: Coordinator = Depends(get_coordinator)):
        return coord.resume_adk_workflow(req.change_id).model_dump(mode="json")

    # Serve built React frontend if web/dist exists
    dist_path = Path("web/dist")
    if dist_path.exists():
        assets_dir = dist_path / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            target = dist_path / full_path
            if target.is_file():
                return FileResponse(target)
            return FileResponse(dist_path / "index.html")

    return app


app = create_app()

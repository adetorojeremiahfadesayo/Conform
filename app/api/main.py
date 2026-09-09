"""CONFORM API — FastAPI surface for the demo workflow.

All endpoints return typed pydantic payloads. Domain failures arrive as
ConformError and map to a consistent ApiError envelope with the right status.
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from time import monotonic

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents.coordinator import Coordinator
from app.api.deps import get_coordinator
from app.config import load_config
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
    "ADK_LIVE_FAILED": 502,
    "ADK_NO_CHANGE": 502,
    "JUDGE_ACTION_BLOCKED": 403,
    "JUDGE_CACHE_MISS": 503,
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
    config = load_config()
    requests: dict[str, list[float]] = {}
    request_lock = Lock()
    app.add_middleware(
        CORSMiddleware,
        # The browser bundle and API share one Cloud Run origin. No cross-site
        # caller needs credentials or CORS access in the public judge surface.
        allow_origins=[],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def judge_guard(request: Request, call_next):
        """Constrain the public URL to a cached, no-spend judge journey."""
        try:
            body_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse(status_code=400, content={"code": "INVALID_CONTENT_LENGTH", "message": "Invalid request"})
        if body_length > 8_192:
            return JSONResponse(status_code=413, content={"code": "REQUEST_TOO_LARGE", "message": "Request too large"})
        if config.judge_mode and request.url.path.startswith("/api/"):
            # In-memory per-instance abuse control. Cloud Run is held to one
            # instance and one concurrent request for this prepared demo.
            client = request.client.host if request.client else "unknown"
            now = monotonic()
            with request_lock:
                history = [item for item in requests.get(client, []) if now - item < 60]
                if len(history) >= 60:
                    return JSONResponse(status_code=429, content={"code": "RATE_LIMITED", "message": "Try again shortly."})
                history.append(now)
                requests[client] = history
            allowed = (
                ("GET", "/api/system/status"), ("GET", "/api/campaigns"),
                ("GET", "/api/presets"), ("GET", "/api/graph"),
                ("POST", "/api/agents/adk/presets/eu_disclaimer_2026/execute"),
                ("POST", "/api/analytics/ask"), ("POST", "/api/system/tamper"),
            )
            path = request.url.path
            dynamic = (
                (request.method == "POST" and path.startswith("/api/changes/") and path.endswith(("/estimate", "/approve", "/build")))
                or (request.method == "GET" and path.startswith("/api/releases/") and (path.endswith("/verify") or "/artifacts/" in path))
            )
            if (request.method, path) not in allowed and not dynamic:
                return JSONResponse(status_code=403, content={"code": "JUDGE_ACTION_BLOCKED", "message": "Not available in the public judge demo."})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
        return response

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

    @app.get("/api/releases/{release_id}/artifacts/{node_id}")
    def artifact(release_id: str, node_id: str, coord: Coordinator = Depends(get_coordinator)):
        release = next((r for r in coord.releases if r.release_id == release_id), None)
        if release is None:
            raise ConformError("UNKNOWN_RELEASE", "Release not found")
        item = next((a for a in release.artifacts if a.node_id == node_id), None)
        if item is None:
            raise ConformError("UNKNOWN_NODE", "Artifact not in release")
        return Response(content=coord.store.fetch(item.uri), media_type=item.content_type)

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
        return coord.execute_adk_goal(req.goal, auto_approve=False).model_dump(mode="json")

    @app.post("/api/agents/adk/presets/{preset_id}/execute")
    def adk_execute_preset(preset_id: str, coord: Coordinator = Depends(get_coordinator)):
        return coord.execute_adk_preset(preset_id).model_dump(mode="json")

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

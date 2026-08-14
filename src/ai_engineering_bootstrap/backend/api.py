"""FastAPI compatibility layer backed by the canonical application service."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, TypeVar

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from ai_engineering_bootstrap.backend.service import ApplicationBackend
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.executor.mode import ExecutionMode

API_VERSION = "v1"
GUI_ROOT = Path(__file__).resolve().parents[1] / "gui" / "static"
backend = ApplicationBackend()

app = FastAPI(
    title="AI Engineering Bootstrap API",
    description="FastAPI compatibility layer for the canonical AI Engineering Bootstrap backend.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EnvironmentRequestInput(BaseModel):
    project_path: str | None = None
    natural_language_goal: str = ""
    required_tools: list[str] = Field(default_factory=list)
    optional_tools: list[str] = Field(default_factory=list)
    project_dependencies: list[Any] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


T = TypeVar("T")


def _call(operation: Callable[[], T]) -> T:
    """Translate domain validation failures into HTTP 400 responses."""
    try:
        return operation()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _data(result: Any) -> dict[str, Any]:
    return result.data


def _serve_index() -> HTMLResponse:
    index_path = GUI_ROOT / "index.html"
    html = index_path.read_text(encoding="utf-8")
    if "/app-runtime.js" not in html:
        html = html.replace(
            "</body>",
            '<script src="/app-runtime.js"></script></body>',
        )
    return HTMLResponse(content=html)


@app.get("/", response_class=HTMLResponse)
def serve_gui() -> HTMLResponse:
    return _serve_index()


@app.get("/app-runtime.js")
def serve_runtime_script() -> Response:
    script = (GUI_ROOT / "app-runtime.js").read_text(encoding="utf-8")
    return Response(script, media_type="application/javascript")


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return _data(_call(backend.health))


@app.get("/api/v1/audit")
def audit() -> dict[str, Any]:
    return _data(_call(backend.audit))


@app.get("/api/v1/plan")
def plan() -> dict[str, Any]:
    return _data(_call(backend.plan))


@app.get("/api/v1/engineering")
def engineering() -> dict[str, Any]:
    return _data(_call(backend.engineering))


@app.get("/api/v1/llm/settings")
def get_llm_settings() -> dict[str, Any]:
    return _data(_call(backend.get_llm_settings))


@app.post("/api/v1/llm/settings")
def update_llm_settings(payload: dict[str, Any]) -> dict[str, Any]:
    return _data(_call(lambda: backend.update_llm_settings(payload)))


@app.get("/api/v1/llm/models")
def get_llm_models() -> dict[str, Any]:
    return _data(_call(backend.list_llm_models))


@app.post("/api/v1/llm/models")
def post_llm_models(payload: dict[str, Any]) -> dict[str, Any]:
    return _data(_call(lambda: backend.list_llm_models(payload)))


@app.post("/api/v1/llm/test")
def test_llm(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return _data(_call(lambda: backend.test_llm_connection(payload)))


@app.post("/api/v1/environment/request")
def preview_environment_request(payload: EnvironmentRequestInput) -> dict[str, Any]:
    """Return the normalized desired state without executing it."""
    request = EnvironmentRequest(
        project_path=Path(payload.project_path) if payload.project_path else None,
        natural_language_goal=payload.natural_language_goal,
        required_tools=list(payload.required_tools),
        optional_tools=list(payload.optional_tools),
        project_dependencies=list(payload.project_dependencies),
        constraints=dict(payload.constraints),
    )
    desired = request.to_desired_state()
    return {"request": asdict(desired)}


@app.get("/api/v1/sessions")
def list_sessions() -> dict[str, Any]:
    return _data(_call(backend.list_sessions))


@app.post("/api/v1/sessions")
def create_session(payload: EnvironmentRequestInput) -> dict[str, Any]:
    """Create a session through the canonical LLM-aware runtime service."""
    request = EnvironmentRequest(
        project_path=Path(payload.project_path) if payload.project_path else None,
        natural_language_goal=payload.natural_language_goal,
        required_tools=list(payload.required_tools),
        optional_tools=list(payload.optional_tools),
        project_dependencies=list(payload.project_dependencies),
        constraints=dict(payload.constraints),
    )
    return _data(_call(lambda: backend.create_session(request)))


@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.get_session(session_id)))


@app.get("/api/v1/sessions/{session_id}/state")
def get_session_state(session_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.get_session_state(session_id)))


@app.get("/api/v1/sessions/{session_id}/plan")
def get_session_plan(session_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.get_session_plan(session_id)))


@app.get("/api/v1/sessions/{session_id}/events")
def get_session_events(session_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.get_session_events(session_id)))


@app.get("/api/v1/sessions/{session_id}/agent-decisions")
def get_agent_decisions(session_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.get_agent_decisions(session_id)))


@app.post("/api/v1/sessions/{session_id}/actions/{action_id}/approve")
def approve_action(session_id: str, action_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.approve_action(session_id, action_id)))


@app.post("/api/v1/sessions/{session_id}/actions/{action_id}/reject")
def reject_action(session_id: str, action_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.reject_action(session_id, action_id)))


@app.post("/api/v1/sessions/{session_id}/actions/{action_id}/skip")
def skip_action(session_id: str, action_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.skip_action(session_id, action_id)))


@app.post("/api/v1/sessions/{session_id}/start")
def start_session(session_id: str, mode: str = "safe") -> dict[str, Any]:
    """Execute the approved plan through the canonical runtime service."""
    try:
        execution_mode = ExecutionMode(mode.lower())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=f"Invalid execution mode: {mode}") from error
    return _data(_call(lambda: backend.start_session(session_id, execution_mode)))


@app.post("/api/v1/sessions/{session_id}/cancel")
def cancel_session(session_id: str) -> dict[str, Any]:
    return _data(_call(lambda: backend.cancel_session(session_id)))


__all__ = ["app", "backend"]

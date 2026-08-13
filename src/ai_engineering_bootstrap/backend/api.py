"""
AI Engineering Bootstrap - Backend API Service

Provides REST API v1 endpoints for environment orchestration.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os

from ai_engineering_bootstrap.environment.models import (
    EnvironmentRequest,
    DesiredEnvironmentState,
    ActualEnvironmentState,
    EnvironmentDelta,
)
from ai_engineering_bootstrap.environment.session_store import SessionStore
from ai_engineering_bootstrap.environment.reconciler import EnvironmentReconciler
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog
from ai_engineering_bootstrap.agent.intent_parser import IntentParser
from ai_engineering_bootstrap.agent.strategy_planner import StrategyPlanner
from ai_engineering_bootstrap.audit import default_audit_service


# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GUI_TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'gui', 'templates')


# Pydantic Models for API
class EnvironmentRequestInput(BaseModel):
    project_path: str
    natural_language_goal: str
    required_tools: List[str] = []
    optional_tools: List[str] = []
    project_dependencies: List[str] = []
    constraints: Dict[str, Any] = {}


class ActionApprovalInput(BaseModel):
    action: str  # "approve", "reject", "skip"


class APIResponse(BaseModel):
    api_version: str = "v1"
    request_id: str
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


# FastAPI Application
app = FastAPI(
    title="AI Engineering Bootstrap API",
    description="Backend API for AI-Assisted Engineering Environment Orchestrator",
    version="1.0.0",
)

# CORS middleware for GUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS) if needed
# app.mount("/static", StaticFiles(directory=os.path.join(GUI_TEMPLATE_DIR, "static")), name="static")

# Initialize services
tool_catalog = ToolCatalog()
session_store = SessionStore()
reconciler = EnvironmentReconciler()
intent_parser = IntentParser(tool_catalog=tool_catalog)
strategy_planner = StrategyPlanner(tool_catalog=tool_catalog)
audit_service = default_audit_service()


@app.get("/")
async def serve_gui():
    """Serve the main GUI HTML page."""
    import os
    template_path = os.path.join(GUI_TEMPLATE_DIR, "index.html")
    with open(template_path, 'r') as f:
        return HTMLResponse(content=f.read())


def make_response(request_id: str, status: str, data: Optional[Dict] = None, error: Optional[Dict] = None) -> dict:
    """Create standardized API response."""
    return APIResponse(
        api_version="v1",
        request_id=request_id,
        status=status,
        data=data,
        error=error
    ).dict()


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    request_id = str(uuid.uuid4())
    return make_response(
        request_id=request_id,
        status="ok",
        data={
            "service": "ai-engineering-bootstrap",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "llm_available": intent_parser.is_llm_available(),
        }
    )


@app.get("/api/v1/audit")
async def get_audit():
    """Get current environment audit."""
    request_id = str(uuid.uuid4())
    try:
        audit_result = audit_service.run_audit()
        return make_response(
            request_id=request_id,
            status="ok",
            data={"audit": audit_result}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/environment")
async def get_environment_state():
    """Get current environment state."""
    request_id = str(uuid.uuid4())
    try:
        actual_state = audit_service.get_environment_state()
        return make_response(
            request_id=request_id,
            status="ok",
            data={"actual_state": actual_state}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tools")
async def get_tools_catalog():
    """Get available tools catalog."""
    request_id = str(uuid.uuid4())
    try:
        from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog
        catalog = ToolCatalog()
        tools = catalog.list_tools()
        return make_response(
            request_id=request_id,
            status="ok",
            data={"tools": tools}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/environment/request", response_model=APIResponse)
async def create_environment_request(input_data: EnvironmentRequestInput):
    """Create environment request from natural language or structured input."""
    request_id = str(uuid.uuid4())
    try:
        # Parse natural language if provided
        if input_data.natural_language_goal:
            parsed = intent_parser.parse(input_data.natural_language_goal)
            # Merge parsed intent with explicit inputs
            required_tools = list(set(input_data.required_tools + parsed.required_tools))
            optional_tools = list(set(input_data.optional_tools + parsed.optional_tools))
        else:
            required_tools = input_data.required_tools
            optional_tools = input_data.optional_tools
        
        environment_request = EnvironmentRequest(
            project_path=input_data.project_path,
            natural_language_goal=input_data.natural_language_goal,
            required_tools=required_tools,
            optional_tools=optional_tools,
            project_dependencies=input_data.project_dependencies,
            constraints=input_data.constraints,
        )
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"request": environment_request}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/sessions", response_model=APIResponse)
async def create_session(input_data: EnvironmentRequestInput):
    """Create a new environment session."""
    request_id = str(uuid.uuid4())
    try:
        # Parse intent
        parsed = intent_parser.parse(input_data.natural_language_goal)
        
        # Create environment request
        environment_request = EnvironmentRequest(
            project_path=input_data.project_path,
            natural_language_goal=input_data.natural_language_goal,
            required_tools=parsed.required_tools,
            optional_tools=parsed.optional_tools,
            project_dependencies=input_data.project_dependencies,
            constraints=input_data.constraints,
        )
        
        # Get actual state
        actual_state = audit_service.get_environment_state()
        
        # Create desired state
        desired_state = DesiredEnvironmentState.from_request(environment_request)
        
        # Reconcile
        delta = reconciler.reconcile(actual_state, desired_state)
        
        # Create session
        from ai_engineering_bootstrap.environment.session_models import EnvironmentSession
        session = EnvironmentSession(
            request=environment_request,
            actual_state=actual_state,
            desired_state=desired_state,
            delta=delta,
        )
        session_store.create(session)
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"session_id": session.session_id, "status": session.status.value}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/sessions", response_model=APIResponse)
async def list_sessions():
    """List all sessions."""
    request_id = str(uuid.uuid4())
    try:
        store = SessionStore()
        sessions = store.list_all()
        return make_response(
            request_id=request_id,
            status="ok",
            data={"sessions": [
                {
                    "session_id": s.session_id,
                    "status": s.status.value,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}", response_model=APIResponse)
async def get_session(session_id: str):
    """Get session details."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return make_response(
            request_id=request_id,
            status="ok",
            data={"session": session}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/state", response_model=APIResponse)
async def get_session_state(session_id: str):
    """Get session state (actual, desired, delta)."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return make_response(
            request_id=request_id,
            status="ok",
            data={
                "actual_state": session.actual_state,
                "desired_state": session.desired_state,
                "delta": session.delta,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/plan", response_model=APIResponse)
async def get_session_plan(session_id: str):
    """Get execution plan for session."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate plan if not exists
        if not session.plan:
            plan = strategy_planner.create_plan(session.delta, session.actual_state)
            session.plan = plan
            session_store.update_session(session)
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"plan": session.plan}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/events", response_model=APIResponse)
async def get_session_events(session_id: str):
    """Get session event timeline."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return make_response(
            request_id=request_id,
            status="ok",
            data={"events": session.events}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/agent-decisions", response_model=APIResponse)
async def get_agent_decisions(session_id: str):
    """Get agent decisions for session."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return make_response(
            request_id=request_id,
            status="ok",
            data={"agent_decisions": session.agent_decisions}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/start", response_model=APIResponse)
async def start_session(session_id: str):
    """Start session execution."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.status = "EXECUTING"
        session_store.update_session(session)
        session_store.append_event(session_id, {"type": "session_started", "timestamp": datetime.utcnow().isoformat()})
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"session_id": session_id, "status": "EXECUTING"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/actions/{action_id}/approve", response_model=APIResponse)
async def approve_action(session_id: str, action_id: str, input_data: ActionApprovalInput):
    """Approve an action in the session."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update action approval state
        session.approval_states[action_id] = "approved"
        session_store.update_session(session)
        session_store.append_event(session_id, {
            "type": "action_approved",
            "action_id": action_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"action_id": action_id, "status": "approved"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/actions/{action_id}/reject", response_model=APIResponse)
async def reject_action(session_id: str, action_id: str):
    """Reject an action in the session."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.approval_states[action_id] = "rejected"
        session_store.update_session(session)
        session_store.append_event(session_id, {
            "type": "action_rejected",
            "action_id": action_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"action_id": action_id, "status": "rejected"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/actions/{action_id}/skip", response_model=APIResponse)
async def skip_action(session_id: str, action_id: str):
    """Skip an action in the session."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.approval_states[action_id] = "skipped"
        session_store.update_session(session)
        session_store.append_event(session_id, {
            "type": "action_skipped",
            "action_id": action_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"action_id": action_id, "status": "skipped"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/cancel", response_model=APIResponse)
async def cancel_session(session_id: str):
    """Cancel a session."""
    request_id = str(uuid.uuid4())
    try:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.status = "CANCELLED"
        session_store.update_session(session)
        session_store.append_event(session_id, {"type": "session_cancelled", "timestamp": datetime.utcnow().isoformat()})
        
        return make_response(
            request_id=request_id,
            status="ok",
            data={"session_id": session_id, "status": "CANCELLED"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time session updates."""
    await websocket.accept()
    try:
        while True:
            # Send session state updates
            session = session_store.get_session(session_id)
            if session:
                await websocket.send_json({
                    "type": "session_update",
                    "data": {
                        "session_id": session.session_id,
                        "status": session.status,
                        "current_action": session.current_action,
                        "events": session.events[-5:],  # Last 5 events
                    }
                })
            
            # Wait for client message
            data = await websocket.receive_text()
            # Handle client messages if needed
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        pass

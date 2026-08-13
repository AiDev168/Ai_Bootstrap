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
    ToolStatus,
)
from ai_engineering_bootstrap.environment.session_store import SessionStore
from ai_engineering_bootstrap.environment.reconciler import EnvironmentReconciler
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog
from ai_engineering_bootstrap.agent.intent_parser import IntentParser
from ai_engineering_bootstrap.agent.strategy_planner import StrategyPlanner
from ai_engineering_bootstrap.audit import default_audit_service
from datetime import datetime, timezone


# Helper function for error responses
def make_error(code: str, message: str) -> Dict[str, str]:
    return {"code": code, "message": message}


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


# API Version constant
API_VERSION = "v1"

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
        audit = default_audit_service()
        report = audit.run()
        
        # Build ActualEnvironmentState from audit report
        tools = {}
        python_packages = {}
        system_info = {}
        
        for check in report.checks:
            if check.category.value == 'Tools':
                tool_id = check.name.lower()
                if check.status.value == 'passed':
                    tools[tool_id] = ToolStatus(
                        tool_id=tool_id,
                        status='installed',
                        version=check.details.split()[1] if 'version' in check.details.lower() else None,
                        health='healthy'
                    )
                else:
                    tools[tool_id] = ToolStatus(
                        tool_id=tool_id,
                        status='missing',
                        health='unknown'
                    )
            elif check.category.value == 'Python':
                python_packages['python'] = check.details
            elif check.category.value == 'Platform':
                system_info[check.name] = check.details
        
        actual_state = ActualEnvironmentState(
            tools=tools,
            python_packages=python_packages,
            system_info=system_info,
            probe_timestamp=datetime.now(timezone.utc).isoformat(),
            probe_evidence={check.name: check.facts for check in report.checks}
        )
        
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
        audit = default_audit_service()
        report = audit.run()
        
        # Build ActualEnvironmentState from audit report
        tools = {}
        python_packages = {}
        system_info = {}
        
        for check in report.checks:
            if check.category.value == 'Tools':
                tool_id = check.name.lower()
                if check.status.value == 'passed':
                    tools[tool_id] = ToolStatus(
                        tool_id=tool_id,
                        status='installed',
                        version=check.details.split()[1] if 'version' in check.details.lower() else None,
                        health='healthy'
                    )
                else:
                    tools[tool_id] = ToolStatus(
                        tool_id=tool_id,
                        status='missing',
                        health='unknown'
                    )
            elif check.category.value == 'Python':
                python_packages['python'] = check.details
            elif check.category.value == 'Platform':
                system_info[check.name] = check.details
        
        actual_state = ActualEnvironmentState(
            tools=tools,
            python_packages=python_packages,
            system_info=system_info,
            probe_timestamp=datetime.now(timezone.utc).isoformat(),
            probe_evidence={check.name: check.facts for check in report.checks}
        )
        
        # Create desired state
        desired_state = environment_request.to_desired_state()
        
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

# LLM Settings endpoints
@app.get("/api/v1/llm/settings")
async def get_llm_settings():
    """Get current LLM settings"""
    try:
        # Get settings from intent parser or config
        settings = {
            "provider": "lm_studio",  # Default or from config
            "api_url": "http://localhost:1234/v1",
            "model": "qwen-2.5-coder-32b",
            "api_key": None
        }
        return APIResponse(
            api_version=API_VERSION,
            request_id=str(uuid.uuid4()),
            status="ok",
            data=settings
        )
    except Exception as e:
        return APIResponse(
            api_version=API_VERSION,
            request_id=str(uuid.uuid4()),
            status="error",
            error=make_error("settings_error", str(e))
        )

@app.post("/api/v1/llm/settings")
async def save_llm_settings(settings: dict):
    """Save LLM settings"""
    try:
        # Save settings to config or session store
        # For now, just validate and acknowledge
        provider = settings.get("provider", "lm_studio")
        api_url = settings.get("api_url", "")
        model = settings.get("model", "")
        
        # Update intent parser configuration if available
        if intent_parser:
            # This would update the actual LLM client configuration
            pass
        
        return APIResponse(
            api_version=API_VERSION,
            request_id=str(uuid.uuid4()),
            status="ok",
            data={"message": "Settings saved", "provider": provider, "model": model}
        )
    except Exception as e:
        return APIResponse(
            api_version=API_VERSION,
            request_id=str(uuid.uuid4()),
            status="error",
            error=make_error("settings_error", str(e))
        )

@app.post("/api/v1/llm/test")
async def test_llm_connection():
    """Test LLM connection"""
    try:
        # Test connection to LLM
        if intent_parser and intent_parser.is_llm_available():
            return APIResponse(
                api_version=API_VERSION,
                request_id=str(uuid.uuid4()),
                status="ok",
                data={"connected": True, "model": "test-model"}
            )
        else:
            return APIResponse(
                api_version=API_VERSION,
                request_id=str(uuid.uuid4()),
                status="error",
                error=make_error("connection_failed", "LLM not available")
            )
    except Exception as e:
        return APIResponse(
            api_version=API_VERSION,
            request_id=str(uuid.uuid4()),
            status="error",
            error=make_error("connection_error", str(e))
        )

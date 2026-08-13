"""Stable application service boundary for CLI and GUI consumers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import uuid

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.bootstrap import EnvironmentBootstrapService
from ai_engineering_bootstrap.engineering import EngineeringEnvironmentService
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.pipeline import PipelineEngine, PipelineResult
from ai_engineering_bootstrap.planner import PlannerEngine
from ai_engineering_bootstrap.environment import (
    EnvironmentRequest,
    DesiredEnvironmentState,
    ActualEnvironmentState,
    EnvironmentDelta,
    ToolRequirement,
    ToolRequirementLevel,
    EnvironmentSession,
    SessionStatus,
    AgentDecision,
    ActionApprovalState,
    ExecutionEvidence,
    RecoveryRecord,
    get_session_store,
    set_session_store,
    InMemorySessionStore,
    JSONSessionStore,
    EnvironmentReconciler,
    get_tool_catalog,
)


def _check_dict(check: Any) -> dict[str, Any]:
    return {
        "name": check.name,
        "status": check.status.value,
        "category": check.category.value,
        "details": check.details,
        "facts": check.facts,
        "recommendations": check.recommendations,
    }


def _audit_dict(report: Any) -> dict[str, Any]:
    return {
        "checks": [_check_dict(check) for check in report.checks],
        "readiness": {
            "development_ready": report.readiness.development_ready,
            "production_ready": report.readiness.production_ready,
            "passed": report.readiness.passed_count,
            "failed": report.readiness.failed_count,
            "warnings": report.readiness.warning_count,
            "health_score": report.readiness.health_score,
        },
    }


def _plan_dict(plan: Any) -> dict[str, Any]:
    return {
        "plan_id": plan.plan_id,
        "is_actionable": plan.is_actionable,
        "summary": plan.summary,
        "actions": [
            {
                "action_id": action.action_id,
                "description": action.description,
                "priority": action.priority,
                "context": action.context,
            }
            for action in plan.actions
        ],
    }


def _pipeline_dict(result: PipelineResult) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": result.is_success,
        "audit": _audit_dict(result.audit_report),
        "plan": _plan_dict(result.original_plan),
        "validation": {
            "is_valid": result.validation_result.is_valid,
            "errors": result.validation_result.errors,
            "warnings": result.validation_result.warnings,
        },
        "execution": None,
        "verification": None,
        "recovery": {
            "replan_requested": result.replan_requested,
            "replan_count": result.replan_count,
            "failure_records": [
                {
                    "action_id": record.action_id,
                    "failure_type": record.failure_type.value,
                    "message": record.message,
                    "retryable": record.is_retryable,
                    "requires_replan": record.requires_replan,
                    "details": record.details or {},
                }
                for record in result.failure_records
            ],
        },
        "agent": None,
        "evidence": result.run_evidence.to_dict() if result.run_evidence else None,
    }
    if result.execution_result is not None:
        payload["execution"] = {
            "success": result.execution_result.is_success,
            "summary": result.execution_result.summary,
            "results": [
                {
                    "action_id": item.action_id,
                    "status": item.status.value,
                    "message": item.message,
                    "details": item.details,
                }
                for item in result.execution_result.results
            ],
        }
    if result.verification_result is not None:
        payload["verification"] = [
            {
                "action_id": item.action_id,
                "status": item.status.value,
                "message": item.message,
                "expected": item.expected,
                "observed": item.observed,
                "details": item.details,
            }
            for item in result.verification_result
        ]
    if result.agent_decision is not None:
        payload["agent"] = {
            "decision_id": result.agent_decision.decision_id,
            "reasoning_summary": result.agent_decision.reasoning_summary,
            "selected_capability_ids": result.agent_decision.selected_capability_ids,
            "confidence": result.agent_decision.confidence,
            "metadata": result.agent_decision.metadata,
        }
    return payload


@dataclass(frozen=True)
class BackendResult:
    """Stable result envelope exposed by the application service boundary."""

    data: dict[str, Any]


class ApplicationBackend:
    """Own the stable application API consumed by CLI and GUI."""

    VERSION = "v1"

    def audit(self) -> BackendResult:
        return BackendResult(_audit_dict(default_audit_service().run()))

    def plan(self) -> BackendResult:
        report = default_audit_service().run()
        return BackendResult(_plan_dict(PlannerEngine().generate_plan(report)))

    def engineering(self) -> BackendResult:
        report = EngineeringEnvironmentService().run()
        return BackendResult(
            {
                "project_root": str(report.project_root),
                "ready": report.is_ready,
                "required_tools_ready": report.required_tools_ready,
                "cursor_rules_present": report.cursor_rules_present,
                "cursor_available": report.cursor_available,
                "tools": [
                    {
                        "name": tool.name,
                        "required": tool.required,
                        "available": tool.available,
                        "path": tool.path,
                    }
                    for tool in report.tools
                ],
            }
        )

    def run_safe(self) -> BackendResult:
        result = PipelineEngine().run(mode=ExecutionMode.SAFE, run_id="backend-safe-run")
        return BackendResult(_pipeline_dict(result))

    def run_real_requires_cli(self) -> BackendResult:
        """Document the safe API boundary; REAL execution remains approval-driven CLI work."""
        return BackendResult(
            {
                "allowed": False,
                "message": "REAL execution requires explicit interactive approval through the CLI.",
            }
        )

    def bootstrap_safe(self) -> BackendResult:
        result = EnvironmentBootstrapService().run(
            mode=ExecutionMode.SAFE,
            run_id="backend-bootstrap-safe",
        )
        return BackendResult(_pipeline_dict(result.pipeline_result))

    # Session Management APIs
    
    def create_session(
        self,
        request: EnvironmentRequest,
        storage_backend: str = "memory",
        storage_path: Optional[str] = None,
    ) -> BackendResult:
        """Create a new environment session."""
        from ai_engineering_bootstrap.environment import (
            EnvironmentSession,
            SessionStatus,
        )
        
        # Initialize session store
        if storage_backend == "json" and storage_path:
            store = JSONSessionStore(storage_path)
            set_session_store(store)
        else:
            store = InMemorySessionStore()
            set_session_store(store)
        
        session = EnvironmentSession(
            request=request,
            status=SessionStatus.CREATED,
        )
        session.add_event("session_created", "Environment session created")
        
        store.create(session)
        
        return BackendResult({
            "session_id": session.session_id,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
        })
    
    def get_session(self, session_id: str) -> BackendResult:
        """Get a session by ID."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        return BackendResult(session.to_dict())
    
    def list_sessions(self, status_filter: Optional[str] = None) -> BackendResult:
        """List all sessions, optionally filtered by status."""
        store = get_session_store()
        
        status_enum = None
        if status_filter:
            try:
                status_enum = SessionStatus(status_filter)
            except ValueError:
                return BackendResult({
                    "error": f"Invalid status filter: {status_filter}",
                    "valid_statuses": [s.value for s in SessionStatus],
                })
        
        sessions = store.list_sessions(status_enum)
        return BackendResult({
            "sessions": [
                {
                    "session_id": s.session_id,
                    "status": s.status.value,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ],
            "count": len(sessions),
        })
    
    def get_session_state(self, session_id: str) -> BackendResult:
        """Get current/desired state and delta for a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        return BackendResult({
            "session_id": session.session_id,
            "status": session.status.value,
            "actual_state": session.actual_state.to_dict() if session.actual_state else None,
            "desired_state": session.desired_state.to_dict() if session.desired_state else None,
            "delta": session.delta.to_dict() if session.delta else None,
        })
    
    def get_session_plan(self, session_id: str) -> BackendResult:
        """Get the execution plan for a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        return BackendResult({
            "session_id": session.session_id,
            "plan": session.plan.to_dict() if session.plan else None,
            "status": session.status.value,
        })
    
    def get_session_events(self, session_id: str) -> BackendResult:
        """Get the event timeline for a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        return BackendResult({
            "session_id": session.session_id,
            "events": [e.to_dict() for e in session.events],
            "count": len(session.events),
        })
    
    def get_session_agent_decisions(self, session_id: str) -> BackendResult:
        """Get agent decisions for a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        return BackendResult({
            "session_id": session.session_id,
            "agent_decisions": [d.to_dict() for d in session.agent_decisions],
            "count": len(session.agent_decisions),
        })
    
    def approve_action(self, session_id: str, action_id: str) -> BackendResult:
        """Approve an action in a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        session.set_approval_state(action_id, "approved")
        session.add_event("action_approved", f"Action {action_id} approved")
        store.update(session)
        
        return BackendResult({
            "session_id": session_id,
            "action_id": action_id,
            "status": "approved",
        })
    
    def reject_action(self, session_id: str, action_id: str, reason: Optional[str] = None) -> BackendResult:
        """Reject an action in a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        session.set_approval_state(action_id, "rejected", rejection_reason=reason)
        session.add_event("action_rejected", f"Action {action_id} rejected", {"reason": reason})
        store.update(session)
        
        return BackendResult({
            "session_id": session_id,
            "action_id": action_id,
            "status": "rejected",
            "reason": reason,
        })
    
    def skip_action(self, session_id: str, action_id: str) -> BackendResult:
        """Skip an action in a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        session.set_approval_state(action_id, "skipped")
        session.add_event("action_skipped", f"Action {action_id} skipped")
        store.update(session)
        
        return BackendResult({
            "session_id": session_id,
            "action_id": action_id,
            "status": "skipped",
        })
    
    def start_session(self, session_id: str) -> BackendResult:
        """Start executing a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        session.status = SessionStatus.EXECUTING
        session.add_event("session_started", "Session execution started")
        store.update(session)
        
        return BackendResult({
            "session_id": session_id,
            "status": session.status.value,
        })
    
    def cancel_session(self, session_id: str) -> BackendResult:
        """Cancel a session."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        session.status = SessionStatus.CANCELLED
        session.completed_at = session.updated_at
        session.add_event("session_cancelled", "Session cancelled")
        store.update(session)
        
        return BackendResult({
            "session_id": session_id,
            "status": session.status.value,
        })
    
    def complete_session(self, session_id: str) -> BackendResult:
        """Mark a session as completed."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        session.status = SessionStatus.COMPLETED
        session.completed_at = session.updated_at
        session.add_event("session_completed", "Session completed successfully")
        store.update(session)
        
        return BackendResult({
            "session_id": session_id,
            "status": session.status.value,
        })
    
    def fail_session(self, session_id: str, reason: str) -> BackendResult:
        """Mark a session as failed."""
        store = get_session_store()
        session = store.get(session_id)
        
        if not session:
            return BackendResult({
                "error": "Session not found",
                "session_id": session_id,
            })
        
        session.status = SessionStatus.FAILED
        session.completed_at = session.updated_at
        session.add_event("session_failed", "Session failed", {"reason": reason})
        store.update(session)
        
        return BackendResult({
            "session_id": session_id,
            "status": session.status.value,
            "reason": reason,
        })

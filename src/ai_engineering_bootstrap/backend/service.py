"""Stable application service boundary for CLI and GUI consumers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.bootstrap import EnvironmentBootstrapService
from ai_engineering_bootstrap.engineering import EngineeringEnvironmentService
from ai_engineering_bootstrap.environment import (
    EnvironmentRequest,
    EnvironmentReconciler,
    SessionStore,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.pipeline import PipelineEngine, PipelineResult
from ai_engineering_bootstrap.planner import PlannerEngine


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

    def create_session(self, request: EnvironmentRequest) -> BackendResult:
        store = SessionStore()
        session = store.create(request)
        return BackendResult({"session_id": session.session_id, "status": session.status.value})

    def list_sessions(self) -> BackendResult:
        store = SessionStore()
        sessions = store.list_all()
        return BackendResult({
            "sessions": [
                {
                    "session_id": s.session_id,
                    "status": s.status.value,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ]
        })

    def get_session(self, session_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return BackendResult({
            "session_id": session.session_id,
            "status": session.status.value,
            "request": session.request.__dict__,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        })

    def get_session_state(self, session_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        reconciler = EnvironmentReconciler()
        actual = reconciler.get_actual_state(session.request.project_path)
        desired = reconciler.get_desired_state(session.request)
        delta = reconciler.reconcile(actual, desired)
        
        return BackendResult({
            "actual": {
                "tools": [
                    {"tool_id": t.tool_id, "status": t.status.value, "version": t.version}
                    for t in actual.tools
                ]
            },
            "desired": {
                "tools": [
                    {"tool_id": t.tool_id, "requirement": t.requirement.value}
                    for t in desired.tools
                ]
            },
            "delta": {
                "tool_deltas": [
                    {
                        "tool_id": d.tool_id,
                        "action": d.action.value,
                        "current_status": d.current_status.value if d.current_status else None,
                        "desired_requirement": d.desired_requirement.value,
                    }
                    for d in delta.tool_deltas
                ]
            }
        })

    def get_session_plan(self, session_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Generate plan from delta
        reconciler = EnvironmentReconciler()
        actual = reconciler.get_actual_state(session.request.project_path)
        desired = reconciler.get_desired_state(session.request)
        delta = reconciler.reconcile(actual, desired)
        
        actions = []
        for tool_delta in delta.tool_deltas:
            if tool_delta.action.value in ["INSTALL", "UPGRADE"]:
                actions.append({
                    "action_id": f"install_{tool_delta.tool_id}",
                    "tool_id": tool_delta.tool_id,
                    "operation": "install",
                    "strategy": "auto",
                    "risk": "medium",
                    "privilege": "user",
                    "description": f"Install {tool_delta.tool_id}",
                })
        
        return BackendResult({
            "session_id": session_id,
            "actions": actions,
            "total_actions": len(actions),
        })

    def approve_action(self, session_id: str, action_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session status to executing
        store.update(session_id, {"status": "EXECUTING", "current_action": action_id})
        
        # TODO: Execute the actual action here
        # For now, just mark as approved
        return BackendResult({
            "status": "approved",
            "message": f"Action {action_id} approved for execution",
        })

    def reject_action(self, session_id: str, action_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return BackendResult({
            "status": "rejected",
            "message": f"Action {action_id} rejected",
        })

    def skip_action(self, session_id: str, action_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return BackendResult({
            "status": "skipped",
            "message": f"Action {action_id} skipped",
        })

    def get_session_events(self, session_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return BackendResult({
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "event_type": e.event_type,
                    "message": e.message,
                }
                for e in session.events
            ]
        })

    def get_agent_decisions(self, session_id: str) -> BackendResult:
        store = SessionStore()
        session = store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return BackendResult({
            "decisions": [
                {
                    "decision_id": d.decision_id,
                    "decision_type": d.decision_type,
                    "reasoning_summary": d.reasoning_summary,
                    "confidence": d.confidence,
                    "created_at": d.created_at.isoformat(),
                }
                for d in session.agent_decisions
            ]
        })

"""Stable application service boundary for CLI and GUI consumers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.backend.llm_settings import LLMSettingsService
from ai_engineering_bootstrap.backend.session_service import EnvironmentSessionService
from ai_engineering_bootstrap.backend.strategy_planner_runtime import RuntimeStrategyPlanner
from ai_engineering_bootstrap.bootstrap import EnvironmentBootstrapService
from ai_engineering_bootstrap.engineering import EngineeringEnvironmentService
from ai_engineering_bootstrap.environment import EnvironmentRequest
from ai_engineering_bootstrap.environment.session_repository import InMemorySessionRepository
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

    def __init__(self, session_service: EnvironmentSessionService | None = None) -> None:
        self._llm_settings = LLMSettingsService()
        self._session_service = session_service or EnvironmentSessionService(
            repository=InMemorySessionRepository(),
            strategy_planner=RuntimeStrategyPlanner(settings_service=self._llm_settings),
        )

    def health(self) -> BackendResult:
        """Return backend health and safe LLM status."""
        settings = self._llm_settings.get()
        return BackendResult(
            {
                "status": "ok",
                "version": self.VERSION,
                "llm_available": settings.enabled,
                "llm": {
                    "provider": settings.provider,
                    "model": settings.model,
                    "base_url": settings.base_url,
                    "api_key_configured": settings.api_key_configured,
                },
            }
        )

    def get_llm_settings(self) -> BackendResult:
        """Return safe LLM configuration metadata."""
        settings = self._llm_settings.get()
        return BackendResult(
            {
                "provider": settings.provider,
                "model": settings.model,
                "base_url": settings.base_url,
                "api_key_configured": settings.api_key_configured,
                "enabled": settings.enabled,
            }
        )

    def update_llm_settings(self, payload: dict[str, Any]) -> BackendResult:
        """Update process-local LLM configuration."""
        settings = self._llm_settings.update(payload)
        return BackendResult(
            {
                "provider": settings.provider,
                "model": settings.model,
                "base_url": settings.base_url,
                "api_key_configured": settings.api_key_configured,
                "enabled": settings.enabled,
            }
        )

    def test_llm_connection(self) -> BackendResult:
        """Probe the configured LLM endpoint."""
        return BackendResult(self._llm_settings.test_connection())

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
        return BackendResult(self._session_service.create(request).data)

    def list_sessions(self) -> BackendResult:
        return BackendResult(self._session_service.list().data)

    def get_session(self, session_id: str) -> BackendResult:
        session = self._session_service.get(session_id)
        return BackendResult(
            {
                "session_id": session.session_id,
                "status": session.status.value,
                "current_action": session.current_action,
                "request": self._session_service._request_dict(session.request),
                "approval_states": {key: value.to_dict() for key, value in session.approval_states.items()},
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
        )

    def get_session_state(self, session_id: str) -> BackendResult:
        return BackendResult(self._session_service.state(session_id).data)

    def get_session_plan(self, session_id: str) -> BackendResult:
        return BackendResult(self._session_service.plan(session_id).data)

    def approve_action(self, session_id: str, action_id: str) -> BackendResult:
        return BackendResult(self._session_service.approve(session_id, action_id).data)

    def reject_action(self, session_id: str, action_id: str) -> BackendResult:
        return BackendResult(self._session_service.reject(session_id, action_id).data)

    def skip_action(self, session_id: str, action_id: str) -> BackendResult:
        return BackendResult(self._session_service.skip(session_id, action_id).data)

    def start_session(self, session_id: str, mode: ExecutionMode = ExecutionMode.SAFE) -> BackendResult:
        return BackendResult(self._session_service.start(session_id, mode).data)

    def cancel_session(self, session_id: str) -> BackendResult:
        return BackendResult(self._session_service.cancel(session_id).data)

    def get_session_events(self, session_id: str) -> BackendResult:
        return BackendResult(self._session_service.events(session_id).data)

    def get_agent_decisions(self, session_id: str) -> BackendResult:
        return BackendResult(self._session_service.agent_decisions(session_id).data)


__all__ = ["ApplicationBackend", "BackendResult"]

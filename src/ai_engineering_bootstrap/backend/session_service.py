"""Application service for environment session orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from ai_engineering_bootstrap.agent.strategy_planner import StrategyPlanner
from ai_engineering_bootstrap.approval.provider import InMemoryApprovalProvider
from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.backend.execution_plan_builder import ExecutionPlanBuilder
from ai_engineering_bootstrap.bootstrap.service import EnvironmentBootstrapService
from ai_engineering_bootstrap.environment.models import (
    ActualEnvironmentState,
    DesiredEnvironmentState,
    EnvironmentDelta,
    EnvironmentRequest,
    ToolStatus,
)
from ai_engineering_bootstrap.environment.reconciler import EnvironmentReconciler
from ai_engineering_bootstrap.environment.session_models import (
    AgentDecision,
    EnvironmentSession,
    ExecutionEvidence,
    SessionStatus,
)
from ai_engineering_bootstrap.environment.session_repository import (
    InMemorySessionRepository,
    SessionRepository,
)
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog
from ai_engineering_bootstrap.executor.mode import ExecutionMode


@dataclass(frozen=True)
class SessionServiceResult:
    """Stable result envelope for session operations."""

    data: dict


class EnvironmentSessionService:
    """Own session lifecycle and keep HTTP concerns outside the application layer."""

    def __init__(
        self,
        repository: SessionRepository | None = None,
        audit_factory: Callable[[], object] = default_audit_service,
        reconciler: EnvironmentReconciler | None = None,
        strategy_planner: StrategyPlanner | None = None,
        plan_builder: ExecutionPlanBuilder | None = None,
        bootstrap_factory: Callable[[], EnvironmentBootstrapService] = EnvironmentBootstrapService,
    ) -> None:
        self.repository = repository or InMemorySessionRepository()
        self._audit_factory = audit_factory
        self._reconciler = reconciler or EnvironmentReconciler()
        self._strategy_planner = strategy_planner or StrategyPlanner(ToolCatalog())
        self._plan_builder = plan_builder or ExecutionPlanBuilder()
        self._bootstrap_factory = bootstrap_factory

    def create(self, request: EnvironmentRequest) -> SessionServiceResult:
        """Create a session from a desired environment request."""
        report = self._audit_factory().run()
        actual = self._actual_state(report)
        desired = request.to_desired_state()
        delta = self._reconciler.reconcile(actual, desired)
        session = EnvironmentSession(
            request=request,
            actual_state=actual,
            desired_state=desired,
            delta=delta,
        )
        session.add_event("session_created", "Environment session created.")
        self.repository.create(session)
        return SessionServiceResult(self._summary(session))

    def list(self) -> SessionServiceResult:
        """List sessions newest first."""
        return SessionServiceResult({"sessions": [self._summary(session) for session in self.repository.list()]})

    def get(self, session_id: str) -> EnvironmentSession:
        """Return a session or raise a stable ValueError."""
        session = self.repository.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        return session

    def state(self, session_id: str) -> SessionServiceResult:
        """Return cached actual, desired, and reconciled state."""
        session = self.get(session_id)
        return SessionServiceResult(
            {
                "session_id": session_id,
                "actual": self._actual_dict(session.actual_state),
                "desired": self._desired_dict(session.desired_state),
                "delta": self._delta_dict(session.delta),
            }
        )

    def plan(self, session_id: str) -> SessionServiceResult:
        """Build and persist a validated execution plan exactly once per session."""
        session = self.get(session_id)
        if session.plan is None:
            if session.delta is None:
                raise ValueError(f"Session {session_id} has no reconciliation delta")
            try:
                strategy_plan = self._strategy_planner.plan_strategies(session.delta)
                session.plan = self._plan_builder.build(session.delta, strategy_plan)
            except ValueError as error:
                session.add_event("plan_failed", str(error), {"error_type": type(error).__name__})
                self.repository.update(session)
                return SessionServiceResult(
                    {
                        "session_id": session_id,
                        "status": "blocked",
                        "error": str(error),
                        "plan": None,
                    }
                )
            self._record_strategy_decisions(session, strategy_plan)
            session.add_event(
                "plan_created",
                "Validated execution plan created.",
                {"plan_id": session.plan.plan_id, "action_count": len(session.plan.actions)},
            )
            self.repository.update(session)
        return SessionServiceResult(
            {
                "session_id": session_id,
                "status": "ready",
                "plan": {
                    "plan_id": session.plan.plan_id,
                    "is_actionable": session.plan.is_actionable,
                    "summary": session.plan.summary,
                    "actions": [
                        {
                            "action_id": action.action_id,
                            "description": action.description,
                            "priority": action.priority,
                            "context": action.context,
                        }
                        for action in session.plan.actions
                    ],
                },
            }
        )

    def approve(self, session_id: str, action_id: str) -> SessionServiceResult:
        """Approve an action that exists in the persisted execution plan."""
        session = self.get(session_id)
        self._ensure_action(session, action_id)
        session.set_approval_state(action_id, "approved")
        session.add_event("action_approved", f"Action '{action_id}' approved.", {"action_id": action_id})
        self.repository.update(session)
        return SessionServiceResult({"action_id": action_id, "status": "approved"})

    def reject(self, session_id: str, action_id: str) -> SessionServiceResult:
        """Reject an action without executing it."""
        session = self.get(session_id)
        self._ensure_action(session, action_id)
        session.set_approval_state(action_id, "rejected")
        session.add_event("action_rejected", f"Action '{action_id}' rejected.", {"action_id": action_id})
        self.repository.update(session)
        return SessionServiceResult({"action_id": action_id, "status": "rejected"})

    def skip(self, session_id: str, action_id: str) -> SessionServiceResult:
        """Skip an action without executing it."""
        session = self.get(session_id)
        self._ensure_action(session, action_id)
        session.set_approval_state(action_id, "skipped")
        session.add_event("action_skipped", f"Action '{action_id}' skipped.", {"action_id": action_id})
        self.repository.update(session)
        return SessionServiceResult({"action_id": action_id, "status": "skipped"})

    def start(self, session_id: str, mode: ExecutionMode) -> SessionServiceResult:
        """Execute a persisted plan through the canonical bootstrap pipeline."""
        session = self.get(session_id)
        if session.plan is None:
            planning = self.plan(session_id)
            if planning.data.get("status") == "blocked":
                return planning
            session = self.get(session_id)
        if session.plan is None or not session.plan.actions:
            session.status = SessionStatus.COMPLETED
            session.completed_at = utcnow()
            self.repository.update(session)
            return SessionServiceResult({"session_id": session_id, "status": session.status.value})

        required_approval = {
            action.action_id
            for action in session.plan.actions
            if self._requires_approval(action.action_id)
        }
        approved = {
            action_id
            for action_id, state in session.approval_states.items()
            if state.status == "approved"
        }
        if mode == ExecutionMode.REAL and not required_approval.issubset(approved):
            pending = sorted(required_approval - approved)
            session.status = SessionStatus.AWAITING_APPROVAL
            self.repository.update(session)
            raise ValueError(f"Approval required for actions: {', '.join(pending)}")

        session.status = SessionStatus.EXECUTING
        session.add_event("session_started", f"Session execution started in {mode.value} mode.")
        self.repository.update(session)

        provider = InMemoryApprovalProvider() if mode == ExecutionMode.REAL else None
        approved_ids = approved
        result = self._bootstrap_factory().run(
            mode=mode,
            approval_provider=provider,
            approval_callback=lambda request: request.action_id in approved_ids,
            run_id=session.session_id,
            plan_override=session.plan,
        )

        for execution in result.action_results:
            for action_result in execution.results:
                session.add_execution_evidence(
                    ExecutionEvidence(
                        action_id=action_result.action_id,
                        success=action_result.status.value == "success",
                        output=action_result.message,
                        error=None if action_result.status.value == "success" else action_result.message,
                    )
                )
        session.status = SessionStatus.COMPLETED if result.is_success else SessionStatus.FAILED
        session.completed_at = utcnow()
        session.add_event(
            "session_completed" if result.is_success else "session_failed",
            "Session execution completed." if result.is_success else "Session execution failed.",
            {"environment_ready": result.environment_ready},
        )
        self.repository.update(session)
        return SessionServiceResult(
            {
                "session_id": session_id,
                "status": session.status.value,
                "environment_ready": result.environment_ready,
                "rejected_actions": list(result.rejected_actions),
            }
        )

    def cancel(self, session_id: str) -> SessionServiceResult:
        """Cancel a session before terminal completion."""
        session = self.get(session_id)
        if session.status in {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED}:
            raise ValueError(f"Session {session_id} is already terminal: {session.status.value}")
        session.status = SessionStatus.CANCELLED
        session.completed_at = utcnow()
        session.add_event("session_cancelled", "Session cancelled.")
        self.repository.update(session)
        return SessionServiceResult({"session_id": session_id, "status": session.status.value})

    def events(self, session_id: str) -> SessionServiceResult:
        """Return timeline events."""
        session = self.get(session_id)
        return SessionServiceResult({"events": [event.to_dict() for event in session.events]})

    def agent_decisions(self, session_id: str) -> SessionServiceResult:
        """Return recorded agent decisions."""
        session = self.get(session_id)
        return SessionServiceResult({"decisions": [decision.to_dict() for decision in session.agent_decisions]})

    def _record_strategy_decisions(self, session: EnvironmentSession, strategy_plan: object) -> None:
        for decision in strategy_plan.decisions:
            provider = "llm" if str(strategy_plan.reasoning_summary).startswith("LLM") else "deterministic"
            session.add_agent_decision(
                AgentDecision(
                    session_id=session.session_id,
                    provider=provider,
                    decision_type="strategy_selection",
                    reasoning_summary=decision.reasoning,
                    confidence=decision.confidence,
                    selected_strategy={
                        "tool_id": decision.tool_id,
                        "strategy": decision.strategy_name,
                        "args": dict(decision.strategy_args),
                        "source": decision.source,
                    },
                )
            )

    @staticmethod
    def _actual_state(report: object) -> ActualEnvironmentState:
        tools: dict[str, ToolStatus] = {}
        for check in report.checks:
            tool_id = check.name.lower().replace(" ", "_")
            status = "installed" if check.status.value == "passed" else "missing"
            tools[tool_id] = ToolStatus(
                tool_id=tool_id,
                status=status,
                version=check.facts.get("version") or check.facts.get("current"),
                health="healthy" if status == "installed" else "unknown",
                probe_evidence=dict(check.facts),
            )
        return ActualEnvironmentState(
            tools=tools,
            python_packages={},
            system_info={},
            probe_timestamp=utcnow().isoformat(),
            probe_evidence={check.name: dict(check.facts) for check in report.checks},
        )

    @staticmethod
    def _summary(session: EnvironmentSession) -> dict:
        return {
            "session_id": session.session_id,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    @staticmethod
    def _request_dict(request: EnvironmentRequest | None) -> dict | None:
        if request is None:
            return None
        return {
            "request_id": request.request_id,
            "project_id": request.project_id,
            "project_path": str(request.project_path) if request.project_path else None,
            "natural_language_goal": request.natural_language_goal,
            "required_tools": list(request.required_tools),
            "optional_tools": list(request.optional_tools),
            "languages": list(request.languages),
            "frameworks": list(request.frameworks),
            "project_dependencies": [
                {"name": item.name, "version_constraint": item.version_constraint, "extras": list(item.extras)}
                for item in request.project_dependencies
            ],
            "configurations": dict(request.configurations),
            "constraints": dict(request.constraints),
            "platform_preferences": dict(request.platform_preferences),
            "user_preferences": dict(request.user_preferences),
        }

    @staticmethod
    def _actual_dict(actual: ActualEnvironmentState | None) -> dict | None:
        if actual is None:
            return None
        return {
            "tools": {
                tool_id: {
                    "tool_id": status.tool_id,
                    "status": status.status,
                    "version": status.version,
                    "location": status.location,
                    "health": status.health,
                    "probe_evidence": dict(status.probe_evidence),
                }
                for tool_id, status in actual.tools.items()
            },
            "python_packages": dict(actual.python_packages),
            "system_info": dict(actual.system_info),
            "probe_timestamp": actual.probe_timestamp,
            "probe_evidence": dict(actual.probe_evidence),
        }

    @staticmethod
    def _desired_dict(desired: DesiredEnvironmentState | None) -> dict | None:
        if desired is None:
            return None
        return {
            "tools": {
                tool_id: {
                    "tool_id": req.tool_id,
                    "level": req.level.value,
                    "version_constraint": req.version_constraint,
                    "configuration": dict(req.configuration),
                }
                for tool_id, req in desired.tools.items()
            },
            "python_packages": [
                {"name": item.name, "version_constraint": item.version_constraint, "extras": list(item.extras)}
                for item in desired.python_packages
            ],
            "configurations": dict(desired.configurations),
            "project_requirements": [
                {"name": item.name, "version_constraint": item.version_constraint, "extras": list(item.extras)}
                for item in desired.project_requirements
            ],
            "constraints": dict(desired.constraints),
        }

    @staticmethod
    def _delta_dict(delta: EnvironmentDelta | None) -> dict | None:
        if delta is None:
            return None
        return {
            "tool_deltas": [
                {
                    "tool_id": item.tool_id,
                    "action": item.action.value,
                    "desired_requirement": {
                        "tool_id": item.desired_requirement.tool_id,
                        "level": item.desired_requirement.level.value,
                        "version_constraint": item.desired_requirement.version_constraint,
                    }
                    if item.desired_requirement else None,
                    "actual_status": {
                        "tool_id": item.actual_status.tool_id,
                        "status": item.actual_status.status,
                        "version": item.actual_status.version,
                        "health": item.actual_status.health,
                    }
                    if item.actual_status else None,
                    "reason": item.reason,
                }
                for item in delta.tool_deltas
            ],
            "package_deltas": [
                {
                    "package_name": item.package_name,
                    "action": item.action.value,
                    "desired_version": item.desired_version,
                    "actual_version": item.actual_version,
                    "reason": item.reason,
                }
                for item in delta.package_deltas
            ],
            "configuration_deltas": dict(delta.configuration_deltas),
        }

    @staticmethod
    def _ensure_action(session: EnvironmentSession, action_id: str) -> None:
        if session.plan is None:
            raise ValueError(f"Session {session.session_id} has no execution plan")
        if not any(action.action_id == action_id for action in session.plan.actions):
            raise ValueError(f"Action {action_id} does not exist in session {session.session_id}")

    @staticmethod
    def _requires_approval(action_id: str) -> bool:
        return action_id in {"install_cursor", "install_git", "install_docker", "install_python_package", "install_project_dependencies"}


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


__all__ = ["EnvironmentSessionService", "SessionServiceResult", "utcnow"]

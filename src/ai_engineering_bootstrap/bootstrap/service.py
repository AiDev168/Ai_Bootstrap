"""End-to-end environment bootstrap orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ai_engineering_bootstrap.agent.planning import AgentPlanningService
from ai_engineering_bootstrap.approval.models import ApprovalRequest
from ai_engineering_bootstrap.approval.provider import (
    ApprovalProvider,
    InMemoryApprovalProvider,
)
from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport
from ai_engineering_bootstrap.executor import ExecutionMode, ExecutionResult
from ai_engineering_bootstrap.executor.policy import SafetyGate
from ai_engineering_bootstrap.pipeline import PipelineEngine, PipelineResult
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction

ApprovalCallback = Callable[[ApprovalRequest], bool]


@dataclass(frozen=True)
class EnvironmentBootstrapResult:
    """Observable result of one complete bootstrap attempt."""

    pipeline_result: PipelineResult | None
    final_audit_report: AuditReport
    action_results: tuple[ExecutionResult, ...] = field(default_factory=tuple)
    rejected_actions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def environment_ready(self) -> bool:
        return self.final_audit_report.readiness.development_ready

    @property
    def is_success(self) -> bool:
        if not self.environment_ready:
            return False
        if self.pipeline_result is not None and self.pipeline_result.execution_result is not None:
            if not self.pipeline_result.execution_result.is_success:
                return False
        return all(result.is_success for result in self.action_results)


class EnvironmentBootstrapService:
    """Run the canonical bootstrap workflow without owning remediation logic."""

    def __init__(self, pipeline: PipelineEngine | None = None) -> None:
        self._pipeline = pipeline or PipelineEngine()

    def run(
        self,
        mode: ExecutionMode = ExecutionMode.SAFE,
        approval_provider: ApprovalProvider | None = None,
        approval_callback: ApprovalCallback | None = None,
        run_id: str = "bootstrap-run",
        max_retry_attempts: int = 1,
        max_replans: int = 1,
        agent_planning_service: AgentPlanningService | None = None,
        plan_override: ExecutionPlan | None = None,
    ) -> EnvironmentBootstrapResult:
        """Bootstrap each planned action in deterministic order."""
        discovery = None
        if plan_override is None:
            discovery = self._pipeline.run(mode=ExecutionMode.SAFE, run_id=f"{run_id}-plan")
            plan = discovery.original_plan
        else:
            plan = plan_override

        if not plan.is_actionable:
            final_report = default_audit_service().run()
            return EnvironmentBootstrapResult(discovery, final_report)

        provider = approval_provider
        action_results: list[ExecutionResult] = []
        rejected: list[str] = []
        last_result: PipelineResult | None = discovery
        safety_gate = SafetyGate()

        for index, action in enumerate(plan.actions):
            single_plan = ExecutionPlan(
                True,
                [
                    ExecutionPlanAction(
                        action_id=action.action_id,
                        description=action.description,
                        priority=action.priority,
                        context=dict(action.context),
                    )
                ],
                summary=f"Bootstrap action {index + 1}: {action.description}",
            )
            action_run_id = f"{run_id}-action-{index + 1}"
            requires_approval = safety_gate.requires_human_approval(action.action_id)

            if mode == ExecutionMode.REAL and requires_approval:
                if provider is None:
                    provider = InMemoryApprovalProvider()
                pending = self._pipeline.run(
                    mode=mode,
                    approval_provider=provider,
                    run_id=action_run_id,
                    plan_override=single_plan,
                    max_retry_attempts=max_retry_attempts,
                    max_replans=max_replans,
                    agent_planning_service=agent_planning_service,
                )
                last_result = pending
                if not pending.is_pending_approval or not pending.approval_requests:
                    action_results.append(
                        pending.execution_result
                        or ExecutionResult(False, [], "Approval workflow failed.")
                    )
                    continue

                request = pending.approval_requests[0]
                if approval_callback is None:
                    return EnvironmentBootstrapResult(
                        pending,
                        default_audit_service().run(),
                        tuple(action_results),
                        tuple(rejected),
                    )
                if not approval_callback(request):
                    provider.reject(request.approval_id)
                    rejected.append(action.action_id)
                    continue
                provider.approve(request.approval_id)
                result = self._pipeline.run(
                    mode=mode,
                    approval_provider=provider,
                    pending_approvals={action.action_id: request.approval_id},
                    run_id=action_run_id,
                    plan_override=single_plan,
                    max_retry_attempts=max_retry_attempts,
                    max_replans=max_replans,
                    agent_planning_service=agent_planning_service,
                )
            else:
                result = self._pipeline.run(
                    mode=mode,
                    run_id=action_run_id,
                    plan_override=single_plan,
                    max_retry_attempts=max_retry_attempts,
                    max_replans=max_replans,
                    agent_planning_service=agent_planning_service,
                )

            last_result = result
            if result.execution_result is not None:
                action_results.append(result.execution_result)
            if not result.is_success:
                break

        final_report = default_audit_service().run()
        return EnvironmentBootstrapResult(
            last_result,
            final_report,
            tuple(action_results),
            tuple(rejected),
        )


__all__ = ["EnvironmentBootstrapResult", "EnvironmentBootstrapService"]

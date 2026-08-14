from unittest.mock import MagicMock, patch

from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.agent.planning import AgentPlanningResult
from ai_engineering_bootstrap.executor.models import (
    ActionResult,
    ExecutionResult,
    ExecutionStatus,
)
from ai_engineering_bootstrap.pipeline import PipelineEngine
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def _plan(action_id: str) -> ExecutionPlan:
    return ExecutionPlan(
        True,
        [ExecutionPlanAction(action_id, action_id, 1)],
        "recovery plan",
    )


def _report() -> MagicMock:
    report = MagicMock()
    report.readiness.health_score = 80
    return report


def test_pipeline_uses_agent_for_recovery_after_diagnosable_failure() -> None:
    first = _plan("install_cursor")
    second = _plan("install_cursor")
    failed = ExecutionResult(
        False,
        [
            ActionResult(
                "install_cursor",
                ExecutionStatus.FAILED,
                "Cursor metadata is invalid.",
                {"replan_recommended": True, "available_formats": ["downloadUrl"]},
            )
        ],
        "failed",
    )
    succeeded = ExecutionResult(
        True,
        [ActionResult("install_cursor", ExecutionStatus.SUCCESS, "installed")],
        "ok",
    )

    decision = AgentDecision(
        reasoning_summary="Retry the existing Cursor capability after diagnosis.",
        selected_capability_ids=["install_cursor"],
        confidence=0.92,
    )
    service = MagicMock()
    service.decide_and_plan.return_value = AgentPlanningResult(decision, second)

    with (
        patch(
            "ai_engineering_bootstrap.pipeline.engine.default_audit_service"
        ) as audit_factory,
        patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine") as planner_cls,
        patch(
            "ai_engineering_bootstrap.pipeline.engine.ExecutorEngine"
        ) as executor_cls,
        patch(
            "ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator"
        ) as validator_cls,
    ):
        audit_factory.return_value.run.side_effect = [_report(), _report()]
        planner_cls.return_value.generate_plan.return_value = first
        validator_cls.return_value.validate.return_value = MagicMock(is_valid=True)
        executor = MagicMock()
        executor.execute.side_effect = [failed, succeeded]
        executor.verify.side_effect = [[], []]
        executor_cls.return_value = executor

        result = PipelineEngine().run(
            agent_planning_service=service,
            max_replans=1,
            run_id="agent-recovery-1",
        )

    assert result.is_success is True
    assert result.replan_count == 1
    assert result.replanned_plan == second
    service.decide_and_plan.assert_called_once()
    context = service.decide_and_plan.call_args.args[0]
    assert "install_cursor" in context
    assert "replan_recommended" in context

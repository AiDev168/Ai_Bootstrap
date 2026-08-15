"""Tests for the end-to-end environment bootstrap service."""

from unittest.mock import MagicMock, patch

from ai_engineering_bootstrap.approval.provider import InMemoryApprovalProvider
from ai_engineering_bootstrap.audit.models import (
    AuditCheck,
    AuditReport,
    CheckCategory,
    CheckStatus,
    EnvironmentReadiness,
)
from ai_engineering_bootstrap.bootstrap import EnvironmentBootstrapService
from ai_engineering_bootstrap.executor import ExecutionMode
from ai_engineering_bootstrap.executor.models import (
    ActionResult,
    ExecutionResult,
    ExecutionStatus,
)
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def _report(ready: bool) -> AuditReport:
    status = CheckStatus.PASSED if ready else CheckStatus.FAILED
    check = AuditCheck("Python Version", status, CheckCategory.PYTHON)
    return AuditReport([check], EnvironmentReadiness.calculate([check]))


def test_bootstrap_service_runs_safe_plan_and_final_audit() -> None:
    action = ExecutionPlanAction("check_python_version_real", "Check Python", 1)
    plan = ExecutionPlan(True, [action])
    execution = ExecutionResult(
        True,
        [ActionResult("check_python_version_real", ExecutionStatus.SUCCESS, "ok")],
        "ok",
    )

    with (
        patch(
            "ai_engineering_bootstrap.bootstrap.service.default_audit_service"
        ) as audit_factory,
        patch(
            "ai_engineering_bootstrap.bootstrap.service.PipelineEngine"
        ) as pipeline_cls,
    ):
        audit_factory.return_value.run.return_value = _report(True)
        pipeline = MagicMock()
        pipeline.run.side_effect = [
            MagicMock(original_plan=plan),
            MagicMock(original_plan=plan, execution_result=execution, is_success=True),
        ]
        pipeline_cls.return_value = pipeline

        result = EnvironmentBootstrapService().run()

    assert result.is_success is True
    assert result.environment_ready is True
    assert len(result.action_results) == 1
    assert pipeline.run.call_count == 2


def test_bootstrap_service_prompts_each_real_approval_independently() -> None:
    actions = [
        ExecutionPlanAction(
            "install_python_package",
            "Install colorama",
            1,
            {"package": "colorama", "requirement": "colorama"},
        ),
        ExecutionPlanAction(
            "install_python_package",
            "Install requests",
            2,
            {"package": "requests", "requirement": "requests"},
        ),
    ]
    plan = ExecutionPlan(True, actions)
    provider = InMemoryApprovalProvider()
    prompts: list[str] = []

    def callback(request: object) -> bool:
        prompts.append(str(request.reason))
        return len(prompts) == 1

    pipeline = MagicMock()

    def run_side_effect(*args: object, **kwargs: object) -> MagicMock:
        override = kwargs.get("plan_override")
        if override is None:
            return MagicMock(original_plan=plan)
        action = override.actions[0]
        pending = kwargs.get("pending_approvals")
        if pending:
            approval_id = pending[action.action_id]
            if provider.get_status(approval_id) is not None:
                execution = ExecutionResult(
                    True,
                    [
                        ActionResult(
                            action.action_id, ExecutionStatus.SUCCESS, "installed"
                        )
                    ],
                    "ok",
                )
                return MagicMock(
                    original_plan=override,
                    execution_result=execution,
                    is_pending_approval=False,
                    is_success=True,
                )
        request = provider.request_approval(
            action.action_id,
            override.plan_id,
            str(kwargs["run_id"]),
            f"Install Python package: {action.context['package']}",
            "medium",
        )
        return MagicMock(
            original_plan=override,
            execution_result=None,
            is_pending_approval=True,
            approval_requests=[request],
        )

    pipeline.run.side_effect = run_side_effect

    with patch(
        "ai_engineering_bootstrap.bootstrap.service.default_audit_service"
    ) as audit_factory:
        audit_factory.return_value.run.return_value = _report(True)
        service = EnvironmentBootstrapService(pipeline)
        result = service.run(
            mode=ExecutionMode.REAL,
            approval_provider=provider,
            approval_callback=callback,
        )

    assert prompts == [
        "Install Python package: colorama",
        "Install Python package: requests",
    ]
    assert result.rejected_actions == ("install_python_package",)
    assert len(result.action_results) == 1
    assert result.action_results[0].results[0].message == "installed"

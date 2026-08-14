"""End-to-end tests for the dependency remediation workflow."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_engineering_bootstrap.approval.provider import InMemoryApprovalProvider
from ai_engineering_bootstrap.audit.dependencies import (
    DependencyRequirement,
    ProjectDependencyProbe,
)
from ai_engineering_bootstrap.audit.models import (
    CheckStatus,
)
from ai_engineering_bootstrap.audit.service import AuditService
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.pipeline.engine import PipelineEngine
from ai_engineering_bootstrap.planner.engine import PlannerEngine


def test_missing_dependency_becomes_install_action(tmp_path: Path) -> None:
    requirement = DependencyRequirement("missing-demo", "missing-demo>=1", "project")
    report = AuditService([ProjectDependencyProbe(requirement)]).run()
    plan = PlannerEngine().generate_plan(report)
    assert report.checks[0].status == CheckStatus.FAILED
    assert plan.actions[0].action_id == "install_python_package"
    assert plan.actions[0].context["package"] == "missing-demo"


def test_dependency_installation_requires_human_approval() -> None:
    action = __import__(
        "ai_engineering_bootstrap.planner.models", fromlist=["ExecutionPlanAction"]
    ).ExecutionPlanAction(
        "install_python_package",
        "Install package",
        1,
        {"package": "demo_pkg", "requirement": "demo_pkg"},
    )
    plan = __import__(
        "ai_engineering_bootstrap.planner.models", fromlist=["ExecutionPlan"]
    ).ExecutionPlan(True, [action])
    provider = InMemoryApprovalProvider()
    engine = PipelineEngine()
    with (
        patch(
            "ai_engineering_bootstrap.pipeline.engine.default_audit_service"
        ) as audit,
        patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine") as planner,
    ):
        audit.return_value.run.return_value = MagicMock()
        planner.return_value.generate_plan.return_value = plan
        result = engine.run(
            mode=ExecutionMode.REAL,
            approval_provider=provider,
        )
    assert result.is_pending_approval is True
    assert result.approval_requests[0].action_id == "install_python_package"

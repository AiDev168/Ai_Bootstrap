"""Step 31 backend service boundary tests."""

from unittest.mock import MagicMock

import pytest

from ai_engineering_bootstrap.agent.strategy_planner import (
    StrategyDecision,
    StrategyPlan,
)
from ai_engineering_bootstrap.backend.execution_plan_builder import ExecutionPlanBuilder
from ai_engineering_bootstrap.backend.service import ApplicationBackend
from ai_engineering_bootstrap.environment.models import (
    DeltaAction,
    EnvironmentDelta,
    PackageDelta,
    ToolDelta,
    ToolRequirement,
    ToolRequirementLevel,
    ToolStatus,
)


def _delta() -> EnvironmentDelta:
    return EnvironmentDelta(
        tool_deltas=[
            ToolDelta(
                tool_id="cursor",
                action=DeltaAction.INSTALL,
                desired_requirement=ToolRequirement(
                    "cursor", ToolRequirementLevel.REQUIRED
                ),
                actual_status=ToolStatus("cursor", "missing"),
            ),
            ToolDelta(
                tool_id="ruff",
                action=DeltaAction.INSTALL,
                desired_requirement=ToolRequirement(
                    "ruff", ToolRequirementLevel.REQUIRED
                ),
                actual_status=ToolStatus("ruff", "missing"),
            ),
        ],
        package_deltas=[
            PackageDelta(
                package_name="pytest",
                action=DeltaAction.INSTALL,
                desired_version=None,
            )
        ],
    )


def test_execution_plan_builder_maps_known_actions() -> None:
    builder = ExecutionPlanBuilder()
    strategy_plan = StrategyPlan(
        decisions=[
            StrategyDecision(
                tool_id="cursor",
                strategy_name="deb_install",
                strategy_args={"artifact_url": "https://downloads.cursor.com/x.deb"},
                confidence=0.9,
                source="official",
                risk_level="medium",
            ),
            StrategyDecision(
                tool_id="ruff",
                strategy_name="pip_install",
                strategy_args={"package_name": "ruff"},
                confidence=0.9,
                source="catalog",
                risk_level="low",
            ),
        ],
        overall_confidence=0.9,
        reasoning_summary="Deterministic strategy selection from catalog metadata.",
    )

    plan = builder.build(_delta(), strategy_plan)

    assert plan.is_actionable
    assert [action.action_id for action in plan.actions] == [
        "install_cursor:cursor",
        "install_python_package:ruff",
        "install_python_package:pytest",
    ]
    assert len({action.action_id for action in plan.actions}) == len(plan.actions)


def test_execution_plan_builder_fails_closed_for_unknown_strategy() -> None:
    builder = ExecutionPlanBuilder()
    strategy_plan = StrategyPlan(
        decisions=[
            StrategyDecision(
                tool_id="ruff",
                strategy_name="unknown_strategy",
                risk_level="low",
            )
        ]
    )

    with pytest.raises(ValueError, match="No executor action"):
        builder.build(_delta(), strategy_plan)


def test_backend_delegates_session_operations_to_service() -> None:
    session_service = MagicMock()
    session_service.list.return_value.data = {"sessions": []}
    backend = ApplicationBackend(session_service=session_service)

    result = backend.list_sessions()

    assert result.data == {"sessions": []}
    session_service.list.assert_called_once_with()

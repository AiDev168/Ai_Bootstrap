from ai_engineering_bootstrap.agent.strategy_planner import StrategyDecision, StrategyPlan
from ai_engineering_bootstrap.backend.execution_plan_builder import ExecutionPlanBuilder
from ai_engineering_bootstrap.environment.models import (
    DeltaAction,
    EnvironmentDelta,
    PackageDelta,
    EnvironmentRequest,
    PythonPackageRequirement,
)


def test_desired_state_deduplicates_python_packages_case_insensitively() -> None:
    request = EnvironmentRequest(
        project_dependencies=[
            PythonPackageRequirement(name="colorama"),
            PythonPackageRequirement(name="Colorama"),
            PythonPackageRequirement(name="requests"),
        ]
    )

    state = request.to_desired_state()

    assert [item.name for item in state.python_packages] == ["colorama", "requests"]


def test_execution_plan_does_not_duplicate_strategy_and_package_action() -> None:
    delta = EnvironmentDelta(
        package_deltas=[
            PackageDelta(
                package_name="colorama",
                action=DeltaAction.INSTALL,
                reason="Package is required.",
            )
        ]
    )
    strategy_plan = StrategyPlan(
        decisions=[
            StrategyDecision(
                tool_id="colorama",
                strategy_name="pip_install",
                strategy_args={"package_name": "colorama"},
                confidence=0.9,
                source="llm",
                risk_level="low",
            )
        ],
        overall_confidence=0.9,
        reasoning_summary="LLM-selected strategies passed catalog and source validation.",
    )

    plan = ExecutionPlanBuilder().build(delta, strategy_plan)

    assert [action.action_id for action in plan.actions] == [
        "install_python_package:colorama"
    ]

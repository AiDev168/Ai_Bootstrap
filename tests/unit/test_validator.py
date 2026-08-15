"""Unit tests for the ExecutionPlan Validator."""

from ai_engineering_bootstrap.executor.validator import ExecutionPlanValidator
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def _make_plan(actions: list[ExecutionPlanAction]) -> ExecutionPlan:
    return ExecutionPlan(
        is_actionable=len(actions) > 0, actions=actions, summary="Test"
    )


def test_validate_empty_plan() -> None:
    plan = _make_plan([])
    result = ExecutionPlanValidator().validate(plan)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_valid_action() -> None:
    action = ExecutionPlanAction(
        action_id="install_git", description="Install Git", priority=1
    )
    result = ExecutionPlanValidator().validate(_make_plan([action]))
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_validate_python_package_instance_action() -> None:
    actions = [
        ExecutionPlanAction(
            action_id="install_python_package:ruff",
            description="Install Ruff",
            priority=1,
            context={"package": "ruff", "requirement": "ruff"},
        ),
        ExecutionPlanAction(
            action_id="install_python_package:pytest",
            description="Install Pytest",
            priority=1,
            context={"package": "pytest", "requirement": "pytest"},
        ),
    ]
    result = ExecutionPlanValidator().validate(_make_plan(actions))
    assert result.is_valid is True
    assert result.errors == []


def test_validate_empty_action_id_fails() -> None:
    action = ExecutionPlanAction(action_id="", description="Bad Action", priority=1)
    result = ExecutionPlanValidator().validate(_make_plan([action]))
    assert result.is_valid is False
    assert any("empty" in err.lower() for err in result.errors)


def test_validate_duplicate_actions_fails() -> None:
    actions = [
        ExecutionPlanAction(action_id="install_git", description="Git 1", priority=1),
        ExecutionPlanAction(action_id="install_git", description="Git 2", priority=2),
    ]
    result = ExecutionPlanValidator().validate(_make_plan(actions))
    assert result.is_valid is False
    assert any("duplicate" in err.lower() for err in result.errors)


def test_validate_same_action_id_with_different_packages_is_valid() -> None:
    actions = [
        ExecutionPlanAction(
            action_id="install_python_package",
            description="Install colorama",
            priority=1,
            context={"package": "colorama"},
        ),
        ExecutionPlanAction(
            action_id="install_python_package",
            description="Install requests",
            priority=1,
            context={"package": "requests"},
        ),
    ]
    result = ExecutionPlanValidator().validate(_make_plan(actions))
    assert result.is_valid is True
    assert result.errors == []


def test_validate_same_action_and_package_fails() -> None:
    actions = [
        ExecutionPlanAction(
            action_id="install_python_package",
            description="Install requests",
            priority=1,
            context={"package": "requests"},
        ),
        ExecutionPlanAction(
            action_id="install_python_package",
            description="Install requests again",
            priority=2,
            context={"package": "requests"},
        ),
    ]
    result = ExecutionPlanValidator().validate(_make_plan(actions))
    assert result.is_valid is False
    assert any("duplicate" in err.lower() for err in result.errors)


def test_validate_missing_description_warning() -> None:
    action = ExecutionPlanAction(action_id="install_git", description="", priority=1)
    result = ExecutionPlanValidator().validate(_make_plan([action]))
    assert result.is_valid is True
    assert len(result.warnings) > 0
    assert any("description" in warning.lower() for warning in result.warnings)


def test_validate_deterministic_order() -> None:
    actions = [
        ExecutionPlanAction(
            action_id=f"action_{i}", description=f"Desc {i}", priority=i
        )
        for i in range(3)
    ]
    validator = ExecutionPlanValidator()
    first = validator.validate(_make_plan(actions))
    second = validator.validate(_make_plan(actions))
    assert first.errors == second.errors
    assert first.warnings == second.warnings
    assert first.is_valid == second.is_valid

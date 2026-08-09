"""Tests for Real Action Handler Architecture."""

from ai_engineering_bootstrap.executor.engine import ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def test_safe_mode_selects_safe_handler() -> None:
    """SAFE mode must use Safe/Mock handler."""
    action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")

    engine = ExecutorEngine(mode=ExecutionMode.SAFE)
    result = engine.execute(plan)

    assert len(result.results) == 1
    assert result.results[0].status == ExecutionStatus.SKIPPED


def test_real_mode_selects_real_handler() -> None:
    """REAL mode must use Real handler if available."""
    action = ExecutionPlanAction(
        action_id="check_python_version_real", description="Py", priority=1
    )
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")

    engine = ExecutorEngine(mode=ExecutionMode.REAL)
    result = engine.execute(plan)

    assert len(result.results) == 1
    res = result.results[0]
    assert res.status == ExecutionStatus.SUCCESS
    assert "sys.version_info" in str(res.details)


def test_real_mode_fails_without_real_handler() -> None:
    """REAL mode must fail safely if no real handler exists."""
    action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")

    engine = ExecutorEngine(mode=ExecutionMode.REAL)
    result = engine.execute(plan)

    assert len(result.results) == 1
    assert result.results[0].status == ExecutionStatus.FAILED
    # پیام دقیق Safety Gate را چک می‌کنیم
    assert "not allowed in real mode" in result.results[0].message


def test_unknown_action_fails_safely() -> None:
    """Unknown action must fail safely."""
    action = ExecutionPlanAction(action_id="unknown_xyz", description="Bad", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")

    engine = ExecutorEngine(mode=ExecutionMode.SAFE)
    result = engine.execute(plan)

    assert len(result.results) == 1
    assert result.results[0].status == ExecutionStatus.FAILED
    # پیام دقیق Safety Gate را چک می‌کنیم (Default Deny)
    assert "no explicit policy" in result.results[0].message


def test_executor_independent_of_concrete_handlers() -> None:
    """ExecutorEngine should not contain action-specific logic."""
    engine = ExecutorEngine()
    assert hasattr(engine, "_registry")

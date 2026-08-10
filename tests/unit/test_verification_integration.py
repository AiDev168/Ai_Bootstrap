"""Tests for post-execution verification integration."""

from ai_engineering_bootstrap.executor.engine import ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import (
    ActionResult,
    ExecutionResult,
    ExecutionStatus,
)
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def test_executor_verify_returns_read_only_result() -> None:
    action = ExecutionPlanAction("check_python_version_real", "Check Python", 1)
    plan = ExecutionPlan(True, [action])
    execution = ExecutionResult(
        True,
        [ActionResult("check_python_version_real", ExecutionStatus.SUCCESS, "ok")],
        "ok",
    )
    results = ExecutorEngine(ExecutionMode.REAL).verify(plan, execution)
    assert len(results) == 1
    assert results[0].status.value == "verified"

"""Tests for controlled real execution capabilities."""

from types import SimpleNamespace

from ai_engineering_bootstrap.executor.engine import ExecutorEngine
from ai_engineering_bootstrap.executor.handlers.dependency_handlers import (
    InstallPythonPackageHandler,
)
from ai_engineering_bootstrap.executor.handlers.real_handlers import REAL_HANDLERS
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.executor.registry import ActionRegistry
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def test_safe_mode_default_behavior() -> None:
    action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    result = ExecutorEngine(mode=ExecutionMode.SAFE).execute(plan)
    assert len(result.results) == 1
    assert result.results[0].status != ExecutionStatus.FAILED


def test_real_mode_approved_action() -> None:
    action = ExecutionPlanAction(
        action_id="check_python_version_real", description="Check Py", priority=1
    )
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    result = ExecutorEngine(mode=ExecutionMode.REAL).execute(plan)
    assert len(result.results) == 1
    res = result.results[0]
    assert res.status == ExecutionStatus.SUCCESS
    assert "sys.version_info" in str(res.details)


def test_real_mode_executes_python_package_instance(monkeypatch) -> None:
    def fake_runner(_command, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="installed ruff", stderr="")

    monkeypatch.setitem(
        REAL_HANDLERS,
        "install_python_package",
        InstallPythonPackageHandler(runner=fake_runner),
    )
    action = ExecutionPlanAction(
        action_id="install_python_package:ruff",
        description="Install Ruff",
        priority=3,
        context={
            "executor_action_id": "install_python_package",
            "package": "ruff",
            "requirement": "ruff",
        },
    )
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    result = ExecutorEngine(mode=ExecutionMode.REAL, is_approved=True).execute(plan)
    assert len(result.results) == 1
    assert result.results[0].status == ExecutionStatus.SUCCESS
    assert result.results[0].action_id == "install_python_package:ruff"


def test_registry_supports_real_python_package_instances() -> None:
    registry = ActionRegistry()
    assert registry.is_supported("install_python_package:ruff", ExecutionMode.REAL) is True


def test_real_mode_rejects_unapproved_action() -> None:
    action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    result = ExecutorEngine(mode=ExecutionMode.REAL).execute(plan)
    assert len(result.results) == 1
    res = result.results[0]
    assert res.status == ExecutionStatus.FAILED
    assert "not allowed in real mode" in res.message


def test_real_mode_rejects_unknown_action() -> None:
    action = ExecutionPlanAction(
        action_id="sudo_rm_rf_root", description="Bad", priority=1
    )
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    result = ExecutorEngine(mode=ExecutionMode.REAL).execute(plan)
    assert len(result.results) == 1
    assert result.results[0].status == ExecutionStatus.FAILED
    assert "Safety Gate Denied" in result.results[0].message
    assert "Default Deny" in result.results[0].message


def test_registry_separation() -> None:
    registry = ActionRegistry()
    assert registry.is_supported("install_git", ExecutionMode.SAFE) is True
    assert registry.is_supported("install_git", ExecutionMode.REAL) is False
    assert registry.is_supported("check_python_version_real", ExecutionMode.REAL) is True

"""Tests for controlled real dependency handlers."""

from pathlib import Path
from unittest.mock import MagicMock

from ai_engineering_bootstrap.executor.handlers.base import ExecutionContext
from ai_engineering_bootstrap.executor.handlers.dependency_handlers import (
    CreateVirtualEnvHandler,
    InstallProjectDependenciesHandler,
    InstallPythonPackageHandler,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


def _real_context() -> ExecutionContext:
    return ExecutionContext(ExecutionMode.REAL, dry_run=False, is_approved=True)


def test_create_virtualenv_real_creates_marker(tmp_path: Path) -> None:
    action = ExecutionPlanAction(
        "create_virtualenv", "Create venv", 1, {"venv_path": str(tmp_path / ".venv")}
    )
    result = CreateVirtualEnvHandler().execute(action, _real_context())
    assert result.status == ExecutionStatus.SUCCESS
    assert (tmp_path / ".venv" / "pyvenv.cfg").is_file()


def test_package_handler_uses_no_shell() -> None:
    runner = MagicMock()
    runner.return_value.returncode = 0
    runner.return_value.stdout = "installed"
    action = ExecutionPlanAction(
        "install_python_package",
        "Install package",
        1,
        {
            "package": "demo_pkg",
            "requirement": "demo_pkg>=1",
            "python_executable": "/venv/bin/python",
        },
    )
    result = InstallPythonPackageHandler(runner).execute(action, _real_context())
    assert result.status == ExecutionStatus.SUCCESS
    kwargs = runner.call_args.kwargs
    assert kwargs["shell"] is False
    assert runner.call_args.args[0][:4] == ("/venv/bin/python", "-m", "pip", "install")


def test_package_handler_rejects_shell_like_package_name() -> None:
    runner = MagicMock()
    action = ExecutionPlanAction(
        "install_python_package",
        "Install package",
        1,
        {"package": "demo;rm -rf /", "requirement": "demo;rm -rf /"},
    )
    result = InstallPythonPackageHandler(runner).execute(action, _real_context())
    assert result.status == ExecutionStatus.FAILED
    runner.assert_not_called()


def test_project_dependency_handler_requires_pyproject(tmp_path: Path) -> None:
    action = ExecutionPlanAction(
        "install_project_dependencies",
        "Install dependencies",
        1,
        {"project_root": str(tmp_path)},
    )
    result = InstallProjectDependenciesHandler().execute(action, _real_context())
    assert result.status == ExecutionStatus.FAILED
    assert "pyproject.toml" in result.message

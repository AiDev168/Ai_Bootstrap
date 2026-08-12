"""Security hardening tests for milestone 30."""

from pathlib import Path

from ai_engineering_bootstrap.executor.engine import ExecutorEngine
from ai_engineering_bootstrap.executor.handlers.dependency_handlers import (
    InstallPythonPackageHandler,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.executor.validator import ExecutionPlanValidator
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def test_tampered_plan_is_rejected_by_validator() -> None:
    action = ExecutionPlanAction(
        "install_python_package",
        "Install requests",
        1,
        {"package": "requests", "requirement": "requests"},
    )
    plan = ExecutionPlan(True, [action])
    action.context["package"] = "colorama"

    result = ExecutionPlanValidator().validate(plan)

    assert result.is_valid is False
    assert any("integrity" in error.lower() for error in result.errors)


def test_tampered_plan_is_rejected_before_execution() -> None:
    action = ExecutionPlanAction(
        "install_python_package",
        "Install requests",
        1,
        {"package": "requests", "requirement": "requests"},
    )
    plan = ExecutionPlan(True, [action])
    action.context["package"] = "colorama"

    result = ExecutorEngine(mode=ExecutionMode.SAFE).execute(plan)

    assert result.is_success is False
    assert result.results == []
    assert "integrity" in result.summary.lower()


def test_validator_rejects_direct_url_package_requirement() -> None:
    action = ExecutionPlanAction(
        "install_python_package",
        "Install requests",
        1,
        {
            "package": "requests",
            "requirement": "requests @ https://example.invalid/requests.whl",
        },
    )

    result = ExecutionPlanValidator().validate(ExecutionPlan(True, [action]))

    assert result.is_valid is False
    assert any("direct url" in error.lower() for error in result.errors)


def test_validator_rejects_pip_option_in_package_requirement() -> None:
    action = ExecutionPlanAction(
        "install_python_package",
        "Install requests",
        1,
        {
            "package": "requests",
            "requirement": "--index-url https://example.invalid requests",
        },
    )

    result = ExecutionPlanValidator().validate(ExecutionPlan(True, [action]))

    assert result.is_valid is False
    assert any(
        "option" in error.lower() or "requirement" in error.lower()
        for error in result.errors
    )


def test_handler_rejects_requirement_mismatch_without_running_pip() -> None:
    class Runner:
        def __init__(self) -> None:
            self.called = False

        def __call__(self, *args: object, **kwargs: object) -> object:
            self.called = True
            raise AssertionError("pip runner must not be invoked")

    runner = Runner()
    action = ExecutionPlanAction(
        "install_python_package",
        "Install requests",
        1,
        {
            "package": "requests",
            "requirement": "requests; malicious_marker",
        },
    )

    result = InstallPythonPackageHandler(runner).execute(
        action,
        context=type("Context", (), {"dry_run": False})(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert runner.called is False


def test_validator_rejects_virtualenv_outside_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    action = ExecutionPlanAction(
        "create_virtualenv",
        "Create virtual environment",
        1,
        {
            "project_root": str(project_root),
            "venv_path": str(tmp_path / "outside"),
        },
    )

    result = ExecutionPlanValidator().validate(ExecutionPlan(True, [action]))

    assert result.is_valid is False
    assert any("inside the project root" in error.lower() for error in result.errors)


def test_validator_accepts_normal_package_version_constraint() -> None:
    action = ExecutionPlanAction(
        "install_python_package",
        "Install requests",
        1,
        {"package": "requests", "requirement": "requests>=2.0"},
    )

    result = ExecutionPlanValidator().validate(ExecutionPlan(True, [action]))

    assert result.is_valid is True

"""Controlled handlers for Python environment remediation."""

from __future__ import annotations

import re
import subprocess
import sys
import venv
from collections.abc import Callable, Sequence
from pathlib import Path

from ai_engineering_bootstrap.executor.handlers.base import (
    ActionHandler,
    ExecutionContext,
)
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _result(action: ExecutionPlanAction, status: ExecutionStatus, message: str, **details: object) -> ActionResult:
    return ActionResult(
        action_id=action.action_id,
        status=status,
        message=message,
        details=dict(details),
    )


class CreateVirtualEnvHandler(ActionHandler):
    """Create an isolated Python virtual environment."""

    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        if context.dry_run:
            return _result(
                action,
                ExecutionStatus.SKIPPED,
                "Virtual environment creation simulated in Safe Mode.",
                simulated=True,
            )

        target = Path(str(action.context.get("venv_path", ".venv"))).expanduser()
        if target.exists() and not target.is_dir():
            return _result(action, ExecutionStatus.FAILED, "Virtual environment target is not a directory.")
        if target.exists() and (target / "pyvenv.cfg").is_file():
            return _result(
                action,
                ExecutionStatus.SUCCESS,
                "Virtual environment already exists.",
                venv_path=str(target),
            )

        try:
            venv.EnvBuilder(with_pip=True, clear=False, symlinks=True).create(target)
        except (OSError, subprocess.SubprocessError) as error:
            return _result(action, ExecutionStatus.FAILED, f"Virtual environment creation failed: {error}")

        return _result(
            action,
            ExecutionStatus.SUCCESS,
            "Virtual environment created.",
            venv_path=str(target),
        )


class InstallPythonPackageHandler(ActionHandler):
    """Install one explicitly named Python package without a shell."""

    def __init__(self, runner: CommandRunner = subprocess.run) -> None:
        self._runner = runner

    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        package = str(action.context.get("package", "")).strip()
        requirement = str(action.context.get("requirement", package)).strip()
        if not package or not _PACKAGE_NAME.fullmatch(package):
            return _result(action, ExecutionStatus.FAILED, "Invalid package name.")
        if requirement != package and not requirement.startswith(package):
            return _result(action, ExecutionStatus.FAILED, "Package requirement does not match package name.")

        if context.dry_run:
            return _result(
                action,
                ExecutionStatus.SKIPPED,
                f"Package installation simulated for '{requirement}'.",
                simulated=True,
                package=package,
            )

        python_executable = str(action.context.get("python_executable", sys.executable))
        command: Sequence[str] = (python_executable, "-m", "pip", "install", requirement)
        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                timeout=float(action.context.get("timeout_seconds", 300)),
                check=False,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return _result(action, ExecutionStatus.FAILED, f"Package installation failed: {error}")

        output = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode != 0:
            return _result(
                action,
                ExecutionStatus.FAILED,
                f"Package installation failed for '{requirement}'.",
                returncode=completed.returncode,
                output=output[-2000:],
            )

        return _result(
            action,
            ExecutionStatus.SUCCESS,
            f"Package '{requirement}' installed successfully.",
            package=package,
            python_executable=python_executable,
            output=output[-2000:],
        )


class InstallProjectDependenciesHandler(ActionHandler):
    """Install the project's declared dependencies in the selected interpreter."""

    def __init__(self, runner: CommandRunner = subprocess.run) -> None:
        self._runner = runner

    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        if context.dry_run:
            return _result(
                action,
                ExecutionStatus.SKIPPED,
                "Project dependency installation simulated in Safe Mode.",
                simulated=True,
            )

        project_root = Path(str(action.context.get("project_root", Path.cwd()))).resolve()
        pyproject = project_root / "pyproject.toml"
        if not pyproject.is_file():
            return _result(action, ExecutionStatus.FAILED, f"No pyproject.toml found at {project_root}.")

        python_executable = str(action.context.get("python_executable", sys.executable))
        extras = str(action.context.get("extras", "dev")).strip()
        target = f"{project_root}[{extras}]" if extras else str(project_root)
        command: Sequence[str] = (
            python_executable,
            "-m",
            "pip",
            "install",
            "-e",
            target,
        )
        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                timeout=float(action.context.get("timeout_seconds", 600)),
                check=False,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return _result(action, ExecutionStatus.FAILED, f"Project dependency installation failed: {error}")

        output = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode != 0:
            return _result(
                action,
                ExecutionStatus.FAILED,
                "Project dependency installation failed.",
                returncode=completed.returncode,
                output=output[-3000:],
            )

        return _result(
            action,
            ExecutionStatus.SUCCESS,
            "Project dependencies installed successfully.",
            project_root=str(project_root),
            python_executable=python_executable,
            output=output[-3000:],
        )

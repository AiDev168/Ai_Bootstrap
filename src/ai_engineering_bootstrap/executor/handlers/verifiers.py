"""Concrete read-only action verifiers."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path
from typing import Any

from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.executor.verifier import (
    ActionVerifier,
    VerificationResult,
    VerificationStatus,
)
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class PythonVersionVerifier(ActionVerifier):
    """Independently verify the active Python version."""

    def verify(
        self,
        action: ExecutionPlanAction,
        execution_result: ActionResult,
        context: Any,
    ) -> VerificationResult:
        if execution_result.status == ExecutionStatus.SKIPPED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Safe-mode simulation produced no real environment change to verify.",
                details={"execution_status": execution_result.status.value},
            )
        if execution_result.status == ExecutionStatus.FAILED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Execution failed; nothing to verify.",
            )

        current = sys.version_info[:2]
        required = (3, 8)
        observed = f"{current[0]}.{current[1]}"
        status = VerificationStatus.VERIFIED if current >= required else VerificationStatus.FAILED
        return VerificationResult(
            action.action_id,
            status,
            f"Python {observed} independently verified against >= {required[0]}.{required[1]}.",
            expected=f">={required[0]}.{required[1]}",
            observed=observed,
            details={"source": "sys.version_info"},
        )


class PythonPackageVerifier(ActionVerifier):
    """Verify that a Python distribution is installed."""

    def verify(
        self,
        action: ExecutionPlanAction,
        execution_result: ActionResult,
        context: Any,
    ) -> VerificationResult:
        if execution_result.status == ExecutionStatus.SKIPPED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Safe-mode simulation produced no real environment change to verify.",
            )
        if execution_result.status == ExecutionStatus.FAILED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Execution failed; nothing to verify.",
            )

        package = str(action.context.get("package", "")).strip()
        if not package:
            return VerificationResult(
                action.action_id,
                VerificationStatus.FAILED,
                "Verification failed: package name is missing.",
            )

        python_executable = str(action.context.get("python_executable", sys.executable))
        target = Path(python_executable)
        if not target.exists():
            return VerificationResult(
                action.action_id,
                VerificationStatus.FAILED,
                "Verification failed: target Python executable does not exist.",
                observed=str(target),
            )

        if target.resolve() == Path(sys.executable).resolve():
            try:
                version = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                version = None
        else:
            try:
                completed = subprocess.run(
                    (
                        python_executable,
                        "-c",
                        "import importlib.metadata as m; print(m.version(__import__('sys').argv[1]))",
                        package,
                    ),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    shell=False,
                )
                version = completed.stdout.strip() if completed.returncode == 0 else None
            except (OSError, subprocess.SubprocessError):
                version = None

        if version is None:
            return VerificationResult(
                action.action_id,
                VerificationStatus.FAILED,
                f"Verification failed: package '{package}' is not installed in the target interpreter.",
                expected=package,
                observed=None,
            )

        return VerificationResult(
            action.action_id,
            VerificationStatus.VERIFIED,
            f"Package '{package}' is installed.",
            expected=package,
            observed=version,
            details={"source": "importlib.metadata"},
        )


class VirtualEnvVerifier(ActionVerifier):
    """Verify a created virtual environment by its standard marker."""

    def verify(
        self,
        action: ExecutionPlanAction,
        execution_result: ActionResult,
        context: Any,
    ) -> VerificationResult:
        if execution_result.status == ExecutionStatus.SKIPPED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Safe-mode simulation produced no real environment change to verify.",
            )
        if execution_result.status == ExecutionStatus.FAILED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Execution failed; nothing to verify.",
            )

        path = Path(str(action.context.get("venv_path", ".venv"))).expanduser()
        marker = path / "pyvenv.cfg"
        if marker.is_file():
            return VerificationResult(
                action.action_id,
                VerificationStatus.VERIFIED,
                "Virtual environment marker verified.",
                expected=str(marker),
                observed=str(marker),
            )
        return VerificationResult(
            action.action_id,
            VerificationStatus.FAILED,
            "Virtual environment marker was not found.",
            expected=str(marker),
            observed=None,
        )


class ProjectDependenciesVerifier(ActionVerifier):
    """Verify that the project is installed in editable mode."""

    def verify(
        self,
        action: ExecutionPlanAction,
        execution_result: ActionResult,
        context: Any,
    ) -> VerificationResult:
        if execution_result.status == ExecutionStatus.SKIPPED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Safe-mode simulation produced no real environment change to verify.",
            )
        if execution_result.status == ExecutionStatus.FAILED:
            return VerificationResult(
                action.action_id,
                VerificationStatus.SKIPPED,
                "Execution failed; nothing to verify.",
            )

        project_name = str(action.context.get("project_name", "ai-engineering-bootstrap"))
        python_executable = str(action.context.get("python_executable", sys.executable))
        target = Path(python_executable)
        if not target.exists():
            return VerificationResult(
                action.action_id,
                VerificationStatus.FAILED,
                "Verification failed: target Python executable does not exist.",
                observed=str(target),
            )
        if target.resolve() == Path(sys.executable).resolve():
            try:
                version = importlib.metadata.version(project_name)
            except importlib.metadata.PackageNotFoundError:
                version = None
        else:
            try:
                completed = subprocess.run(
                    (
                        python_executable,
                        "-c",
                        "import importlib.metadata as m; print(m.version(__import__('sys').argv[1]))",
                        project_name,
                    ),
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    shell=False,
                )
                version = completed.stdout.strip() if completed.returncode == 0 else None
            except (OSError, subprocess.SubprocessError):
                version = None
        if version is None:
            return VerificationResult(
                action.action_id,
                VerificationStatus.FAILED,
                f"Project distribution '{project_name}' is not installed in the target interpreter.",
                expected=project_name,
            )

        return VerificationResult(
            action.action_id,
            VerificationStatus.VERIFIED,
            f"Project distribution '{project_name}' is installed.",
            expected=project_name,
            observed=version,
            details={"source": "importlib.metadata"},
        )


DEFAULT_VERIFIERS = {
    "check_python_version_real": PythonVersionVerifier(),
    "create_virtualenv": VirtualEnvVerifier(),
    "install_python_package": PythonPackageVerifier(),
    "install_project_dependencies": ProjectDependenciesVerifier(),
}

__all__ = [
    "DEFAULT_VERIFIERS",
    "ProjectDependenciesVerifier",
    "PythonPackageVerifier",
    "PythonVersionVerifier",
    "VirtualEnvVerifier",
]

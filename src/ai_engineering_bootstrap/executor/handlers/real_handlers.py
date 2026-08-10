"""Real action handlers approved by the execution policy."""

from __future__ import annotations

import sys

from ai_engineering_bootstrap.executor.handlers.base import (
    ActionHandler,
    ExecutionContext,
)
from ai_engineering_bootstrap.executor.handlers.dependency_handlers import (
    CreateVirtualEnvHandler,
    InstallProjectDependenciesHandler,
    InstallPythonPackageHandler,
)
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class CheckPythonVersionRealHandler(ActionHandler):
    """Read the active Python version without modifying the system."""

    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        try:
            current = sys.version_info[:3]
            version = f"{current[0]}.{current[1]}.{current[2]}"
            valid = current[:2] >= (3, 8)
            return ActionResult(
                action_id=action.action_id,
                status=ExecutionStatus.SUCCESS if valid else ExecutionStatus.FAILED,
                message=f"Real check: Python {version} detected.",
                details={
                    "current": version,
                    "source": "sys.version_info",
                    "classification": "read-only/non-destructive",
                },
            )
        except Exception as error:  # noqa: BLE001
            return ActionResult(
                action_id=action.action_id,
                status=ExecutionStatus.FAILED,
                message=f"Real check failed: {error!s}",
                details={"error": str(error)},
            )


REAL_HANDLERS = {
    "check_python_version_real": CheckPythonVersionRealHandler(),
    "create_virtualenv": CreateVirtualEnvHandler(),
    "install_python_package": InstallPythonPackageHandler(),
    "install_project_dependencies": InstallProjectDependenciesHandler(),
}

__all__ = [
    "REAL_HANDLERS",
    "CheckPythonVersionRealHandler",
    "CreateVirtualEnvHandler",
    "InstallProjectDependenciesHandler",
    "InstallPythonPackageHandler",
]

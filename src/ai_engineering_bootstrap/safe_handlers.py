"""Safe/Mock implementations of action handlers."""

from __future__ import annotations

from ai_engineering_bootstrap.executor.handlers.base import (
    ActionHandler,
    ExecutionContext,
)
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class _SafeHandlerBase:
    """Base class providing safe, non-mutating simulation."""

    def _simulate_success(self, action: ExecutionPlanAction) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            status=ExecutionStatus.SKIPPED,
            message=f"Action '{action.action_id}' simulated successfully (Safe Mode).",
            details={"simulated": True, "description": action.description},
        )


class CheckPythonVersionSafeHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


class InstallGitHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


class InstallDockerHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


class FixVenvHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


class FixEditableHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


class UpgradePythonHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


class CreateVirtualEnvSafeHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


class InstallPythonPackageSafeHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        package = str(action.context.get("package", "")).strip()
        requirement = str(action.context.get("requirement", package)).strip()
        result = self._simulate_success(action)
        return ActionResult(
            action_id=result.action_id,
            status=result.status,
            message=(
                f"Package '{requirement}' installation simulated in Safe Mode."
                if requirement
                else result.message
            ),
            details={
                **result.details,
                "package": package,
                "requirement": requirement,
            },
        )


class InstallProjectDependenciesSafeHandler(_SafeHandlerBase, ActionHandler):
    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        return self._simulate_success(action)


DEFAULT_SAFE_HANDLERS = {
    "check_python_version_real": CheckPythonVersionSafeHandler(),
    "install_git": InstallGitHandler(),
    "install_docker": InstallDockerHandler(),
    "fix_venv": FixVenvHandler(),
    "fix_editable": FixEditableHandler(),
    "upgrade_python": UpgradePythonHandler(),
    "create_virtualenv": CreateVirtualEnvSafeHandler(),
    "install_python_package": InstallPythonPackageSafeHandler(),
    "install_project_dependencies": InstallProjectDependenciesSafeHandler(),
}

__all__ = [
    "DEFAULT_SAFE_HANDLERS",
    "CheckPythonVersionSafeHandler",
    "CreateVirtualEnvSafeHandler",
    "FixEditableHandler",
    "FixVenvHandler",
    "InstallDockerHandler",
    "InstallGitHandler",
    "InstallProjectDependenciesSafeHandler",
    "InstallPythonPackageSafeHandler",
    "UpgradePythonHandler",
]

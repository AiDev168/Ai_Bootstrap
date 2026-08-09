"""Safe/Mock implementations of action handlers."""

from __future__ import annotations

from ai_engineering_bootstrap.executor.handlers.base import (
    ActionHandler,
    ExecutionContext,
)
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class _SafeHandlerBase:
    """Base class providing safe behavior for all mock handlers."""

    def _simulate_success(self, action: ExecutionPlanAction) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            status=ExecutionStatus.SKIPPED,
            message=f"Action '{action.action_id}' simulated successfully (Safe Mode).",
            details={"simulated": True, "description": action.description}
        )


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


# نگاشت پیش‌فرض هندلرهای ایمن
DEFAULT_SAFE_HANDLERS = {
    "install_git": InstallGitHandler(),
    "install_docker": InstallDockerHandler(),
    "fix_venv": FixVenvHandler(),
    "fix_editable": FixEditableHandler(),
    "upgrade_python": UpgradePythonHandler(),
}

__all__ = ["DEFAULT_SAFE_HANDLERS", "FixVenvHandler", "InstallDockerHandler", "InstallGitHandler"]

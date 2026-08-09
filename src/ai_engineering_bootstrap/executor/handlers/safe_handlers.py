"""Safe/Mock implementations of action handlers."""

from __future__ import annotations

from ai_engineering_bootstrap.executor.handlers import ActionHandler, BaseContext
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class _SafeHandlerBase:
    """Base class providing safe behavior for all mock handlers."""

    def _simulate_success(self, action: ExecutionPlanAction) -> ActionResult:
        return ActionResult(
            action_id=action.action_id,
            status=ExecutionStatus.SKIPPED, # یا SUCCESS بسته به تعریف پروژه
            message=f"Action '{action.action_id}' simulated successfully (Safe Mode).",
            details={"simulated": True, "description": action.description}
        )


class InstallGitHandler(_SafeHandlerBase, ActionHandler):
    def handle(self, action: ExecutionPlanAction, context: BaseContext) -> ActionResult:
        return self._simulate_success(action)


class InstallDockerHandler(_SafeHandlerBase, ActionHandler):
    def handle(self, action: ExecutionPlanAction, context: BaseContext) -> ActionResult:
        return self._simulate_success(action)


class FixVenvHandler(_SafeHandlerBase, ActionHandler):
    def handle(self, action: ExecutionPlanAction, context: BaseContext) -> ActionResult:
        return self._simulate_success(action)


class FixEditableHandler(_SafeHandlerBase, ActionHandler):
    def handle(self, action: ExecutionPlanAction, context: BaseContext) -> ActionResult:
        return self._simulate_success(action)


class UpgradePythonHandler(_SafeHandlerBase, ActionHandler):
    def handle(self, action: ExecutionPlanAction, context: BaseContext) -> ActionResult:
        return self._simulate_success(action)


# نگاشت پیش‌فرض برای ثبت سریع در رجیستری
DEFAULT_HANDLERS = {
    "install_git": InstallGitHandler(),
    "install_docker": InstallDockerHandler(),
    "fix_venv": FixVenvHandler(),
    "fix_editable": FixEditableHandler(),
    "upgrade_python": UpgradePythonHandler(),
}

__all__ = ["DEFAULT_HANDLERS", "FixVenvHandler", "InstallDockerHandler", "InstallGitHandler"]

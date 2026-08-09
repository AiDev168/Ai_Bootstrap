"""Real (but safe/read-only) action handlers."""

from __future__ import annotations

import sys

from ai_engineering_bootstrap.executor.handlers import ActionHandler, BaseContext
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class CheckPythonVersionRealHandler(ActionHandler):
    """
    Real handler for checking Python version.
    
    SAFETY CLASSIFICATION: Non-destructive / Read-only.
    This handler only reads sys.version_info and performs a comparison.
    It does not modify files, install packages, or execute shell commands.
    """

    def handle(self, action: ExecutionPlanAction, context: BaseContext) -> ActionResult:
        try:
            current = sys.version_info[:3]
            version_str = f"{current[0]}.{current[1]}.{current[2]}"
            
            # منطق ساده: بررسی اینکه آیا نسخه فعلی >= 3.8 است (به عنوان نمونه)
            is_valid = current[:2] >= (3, 8)
            
            return ActionResult(
                action_id=action.action_id,
                status=ExecutionStatus.SUCCESS if is_valid else ExecutionStatus.FAILED,
                message=f"Real check: Python {version_str} detected.",
                details={
                    "current": version_str,
                    "source": "sys.version_info",
                    "classification": "read-only/non-destructive"
                }
            )
        except Exception as e: # noqa: BLE001
            return ActionResult(
                action_id=action.action_id,
                status=ExecutionStatus.FAILED,
                message=f"Real check failed: {e!s}",
                details={"error": str(e)}
            )


# نگاشت اکشن‌های مجاز برای اجرای واقعی
# فقط اکشن‌هایی که اینجا ثبت شوند در مود REAL اجرا می‌شوند.
REAL_HANDLERS = {
    "check_python_version_real": CheckPythonVersionRealHandler(),
}

__all__ = ["REAL_HANDLERS", "CheckPythonVersionRealHandler"]

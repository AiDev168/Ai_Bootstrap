"""Real (but safe/read-only) action handlers."""

from __future__ import annotations

import sys

from ai_engineering_bootstrap.executor.handlers.base import (
    ActionHandler,
    ExecutionContext,
)
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class CheckPythonVersionRealHandler(ActionHandler):
    """
    Real handler for checking Python version.
    
    SAFETY CLASSIFICATION: Non-destructive / Read-only.
    """

    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        try:
            current = sys.version_info[:3]
            version_str = f"{current[0]}.{current[1]}.{current[2]}"
            
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


# نگاشت هندلرهای واقعی مورد تایید
REAL_HANDLERS = {
    "check_python_version_real": CheckPythonVersionRealHandler(),
}

__all__ = ["REAL_HANDLERS", "CheckPythonVersionRealHandler"]

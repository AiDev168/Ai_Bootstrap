"""Executor Engine - Dispatches actions via the Registry with Mode control."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_engineering_bootstrap.executor.handlers import BaseContext
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import (
    ActionResult,
    ExecutionResult,
    ExecutionStatus,
)
from ai_engineering_bootstrap.executor.registry import ActionRegistry

if TYPE_CHECKING:
    from ai_engineering_bootstrap.planner.models import ExecutionPlan


class ExecutorEngine:
    """
    Executes actions from a validated ExecutionPlan using the Action Registry.
    Supports both SAFE (mock) and REAL (controlled) execution modes.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.SAFE) -> None:
        self._mode = mode
        self._registry = ActionRegistry()

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Process all actions in the plan deterministically."""
        results: list[ActionResult] = []
        # متادیتای زمینه اجرا
        context = BaseContext(
            dry_run=(self._mode == ExecutionMode.SAFE),
            platform="unknown", # می‌تواند از سیستم خوانده شود
            metadata={"mode": self._mode.value}
        )

        for action in plan.actions:
            try:
                handler = self._registry.get_handler(action.action_id, self._mode)
                result = handler.handle(action, context)
                results.append(result)
            except KeyError as ke:
                # اکشن ناشناخته یا عدم مجوز برای مود واقعی
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=str(ke),
                    details={"error": "Unsupported or Unauthorized"}
                ))
            except Exception as e: # noqa: BLE001
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=f"Handler execution error: {e!s}",
                    details={}
                ))

        return ExecutionResult.create_from_actions(results)


__all__ = ["ExecutorEngine"]

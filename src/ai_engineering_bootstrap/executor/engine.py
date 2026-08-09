"""Executor Engine - Dispatches actions via the Registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_engineering_bootstrap.executor.handlers import BaseContext
from ai_engineering_bootstrap.executor.models import (
    ActionResult,
    ExecutionResult,
    ExecutionStatus,
)
from ai_engineering_bootstrap.executor.registry import ActionRegistry

if TYPE_CHECKING:
    from ai_engineering_bootstrap.planner.models import (
        ExecutionPlan,
    )


class ExecutorEngine:
    """
    Executes actions from a validated ExecutionPlan using the Action Registry.
    SAFE MODE: All handlers are mocks; no system changes occur.
    """

    def __init__(self) -> None:
        self._registry = ActionRegistry()

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Process all actions in the plan deterministically."""
        results: list[ActionResult] = []
        context = BaseContext(dry_run=True)

        for action in plan.actions:
            try:
                handler = self._registry.get_handler(action.action_id)
                result = handler.handle(action, context)
                results.append(result)
            except KeyError:
                #action not found in registery
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=f"Action '{action.action_id}' is not supported.",
                    details={"error": "No registered handler"}
                ))
            except Exception as e:  # noqa: BLE001
                # Handler internal error
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=f"Handler failed: {e!s}",
                    details={}
                ))

        return ExecutionResult.create_from_actions(results)


__all__ = ["ExecutorEngine"]

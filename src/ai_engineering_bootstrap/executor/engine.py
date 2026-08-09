#!/usr/bin/env python3
"""Executor Engine - Dispatches via Registry and Abstraction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_engineering_bootstrap.executor.handlers.base import ExecutionContext
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import (
    ActionResult,
    ExecutionResult,
    ExecutionStatus,
)
from ai_engineering_bootstrap.executor.policy import SafetyGate
from ai_engineering_bootstrap.executor.registry import ActionRegistry

if TYPE_CHECKING:
    from ai_engineering_bootstrap.planner.models import ExecutionPlan


class ExecutorEngine:
    """
    Executes actions using handler abstraction.
    Does not depend on concrete handler implementations.
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.SAFE, is_approved: bool = False) -> None:
        self._mode = mode
        self._is_approved = is_approved
        self._registry = ActionRegistry()
        self._safety_gate = SafetyGate()

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Process all actions deterministically."""
        results: list[ActionResult] = []
        context = ExecutionContext(
            mode=self._mode,
            dry_run=(self._mode == ExecutionMode.SAFE),
            is_approved=self._is_approved
        )

        for action in plan.actions:
            # 1. Safety Gate Check
            allowed, reason = self._safety_gate.evaluate(
                action.action_id,
                self._mode,
                is_approved=self._is_approved
            )
            if not allowed:
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=f"Safety Gate Denied: {reason}",
                    details={"reason": "policy_violation"}
                ))
                continue

            # 2. Handler Lookup & Execution
            try:
                handler = self._registry.get_handler(action.action_id, self._mode)
                result = handler.execute(action, context)
                results.append(result)
            except KeyError as ke:
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=str(ke),
                    details={"error": "Unsupported or Unauthorized"}
                ))
            except Exception as e:  # noqa: BLE001
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=f"Handler execution error: {e!s}",
                    details={}
                ))

        return ExecutionResult.create_from_actions(results)


__all__ = ["ExecutorEngine"]

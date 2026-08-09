#!/usr/bin/env python3
"""Executor Engine - Dispatches via Registry with Retry support."""

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
from ai_engineering_bootstrap.executor.recovery import RetryPolicy
from ai_engineering_bootstrap.executor.registry import ActionRegistry

if TYPE_CHECKING:
    from ai_engineering_bootstrap.planner.models import ExecutionPlan


class ExecutorEngine:
    """Executes actions using handler abstraction with bounded retry."""

    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.SAFE,
        is_approved: bool = False,
    ) -> None:
        self._mode = mode
        self._is_approved = is_approved
        self._registry = ActionRegistry()
        self._safety_gate = SafetyGate()

    def execute(
        self,
        plan: ExecutionPlan,
        max_attempts: int = 1,
    ) -> ExecutionResult:
        """Process all actions deterministically with optional retry."""
        results: list[ActionResult] = []
        context = ExecutionContext(
            mode=self._mode,
            dry_run=(self._mode == ExecutionMode.SAFE),
            is_approved=self._is_approved,
        )
        policy = RetryPolicy(max_attempts=max_attempts)

        for action in plan.actions:
            attempt = 0
            final_result: ActionResult | None = None

            while attempt < max_attempts:
                attempt += 1

                # 1. Safety Gate Check
                allowed, reason = self._safety_gate.evaluate(
                    action.action_id,
                    self._mode,
                    is_approved=self._is_approved,
                )

                if not allowed:
                    final_result = ActionResult(
                        action_id=action.action_id,
                        status=ExecutionStatus.FAILED,
                        message=f"Safety Gate Denied: {reason}",
                        details={"reason": "policy_violation"},
                    )
                    break

                # 2. Handler Lookup & Execution
                try:
                    handler = self._registry.get_handler(
                        action.action_id,
                        self._mode,
                    )
                    result = handler.execute(action, context)

                    if result.status != ExecutionStatus.FAILED:
                        final_result = result
                        break

                    failure_record = policy.classify_failure(result)
                    if not failure_record.is_retryable:
                        final_result = result
                        break

                    final_result = result

                except KeyError as err:
                    final_result = ActionResult(
                        action_id=action.action_id,
                        status=ExecutionStatus.FAILED,
                        message=str(err),
                        details={"error": "Unsupported or Unauthorized"},
                    )
                    break
                except Exception as err:  # noqa: BLE001
                    final_result = ActionResult(
                        action_id=action.action_id,
                        status=ExecutionStatus.FAILED,
                        message=f"Handler execution error: {err!s}",
                        details={},
                    )
                    rec = policy.classify_failure(final_result)
                    if not rec.is_retryable:
                        break

            if final_result:
                results.append(final_result)

        return ExecutionResult.create_from_actions(results)


__all__ = ["ExecutorEngine"]

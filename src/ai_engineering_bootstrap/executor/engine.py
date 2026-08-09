"""Executor Engine - Dispatches actions and verifies results."""

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
from ai_engineering_bootstrap.executor.verifier import (
    VerificationResult,
    VerifierRegistry,
)

if TYPE_CHECKING:
    from ai_engineering_bootstrap.planner.models import ExecutionPlan


class ExecutorEngine:
    """Executes actions and optionally verifies them."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SAFE) -> None:
        self._mode = mode
        self._registry = ActionRegistry()
        self._verifier_registry = VerifierRegistry()

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        results: list[ActionResult] = []
        context = BaseContext(
            dry_run=(self._mode == ExecutionMode.SAFE),
            platform="unknown",
            metadata={"mode": self._mode.value}
        )

        for action in plan.actions:
            try:
                handler = self._registry.get_handler(action.action_id, self._mode)
                result = handler.handle(action, context)
                results.append(result)
            except KeyError as ke:
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

    def verify(self, exec_result: ExecutionResult) -> list[VerificationResult]:
        """Verify the results of executed actions."""
        verification_results: list[VerificationResult] = []
        context = {} # می‌تواند متادیتای بیشتری بگیرد

        for action_result in exec_result.results:
            verifier = self._verifier_registry.get_verifier(action_result.action_id)
            if verifier:
                # نیاز به ساخت موقت ExecutionPlanAction از روی ActionResult داریم
                # چون پروتکل وریفایر اکشن اصلی را می‌خواهد، اما ما فقط نتیجه را داریم.
                # برای سادگی، یک آبجکت دیکشنری مانند یا ماک می‌سازیم.
                # در اینجا فرض می‌کنیم اکشن اصلی را می‌توان بازسازی کرد یا وریفایر فقط نتیجه را نیاز دارد.
                # اصلاح پروتکل برای سادگی:
                try:
                    # ساخت یک شیء شبه-اکشن برای پاس دادن به وریفایر
                    pseudo_action = type('PseudoAction', (), {
                        'action_id': action_result.action_id,
                        'description': action_result.details.get('description', '')
                    })()
                    v_res = verifier.verify(pseudo_action, action_result, context)
                    verification_results.append(v_res)
                except Exception as e: # noqa: BLE001
                    verification_results.append(VerificationResult(
                        action_id=action_result.action_id,
                        status="failed", # نوع استرینگ برای جلوگیری از ایمپورت اضافی در خطایابی
                        message=f"Verifier error: {e!s}",
                        details={"error": str(e)}
                    ))
            else:
                # وریفایری ثبت نشده است
                verification_results.append(VerificationResult(
                    action_id=action_result.action_id,
                    status="skipped",
                    message="No verifier registered for this action.",
                    details={"reason": "unregistered"}
                ))
        return verification_results

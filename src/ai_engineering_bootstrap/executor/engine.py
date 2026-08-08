"""Executor Engine - Safe execution of planned actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ai_engineering_bootstrap.executor.models import (
    ActionResult,
    ExecutionResult,
    ExecutionStatus,
)

if TYPE_CHECKING:
    from ai_engineering_bootstrap.planner.models import (
        ExecutionPlan,
        ExecutionPlanAction,
    )


# نوع هندلر: تابعی که یک اکشن را می‌گیرد و نتیجه را برمی‌گرداند
HandlerFunc = Callable[["ExecutionPlanAction"], ActionResult]


class ExecutorEngine:
    """
    Executes actions from an ExecutionPlan.
    
    SAFETY NOTE: This is a FOUNDATION implementation.
    No real system changes (pip install, sudo, etc.) are performed.
    All actions are simulated or skipped safely.
    """

    def __init__(self) -> None:
        # ثبت‌کننده اکشن‌ها (Action Registry)
        self._handlers: dict[str, HandlerFunc] = {}
        self._register_safe_handlers()

    def _register_safe_handlers(self) -> None:
        """ثبت هندلرهای ایمن و آزمایشی."""
        # لیست اکشن‌های شناخته شده از Planner
        known_actions = [
            "fix_venv",
            "fix_editable",
            "install_git",
            "install_docker",
            "upgrade_python",
        ]
        
        # ثبت یک هندلر پیش‌فرض ایمن برای همه اکشن‌های شناخته شده
        for action_id in known_actions:
            self.register_handler(action_id, self._safe_mock_handler)

    def _safe_mock_handler(self, action: ExecutionPlanAction) -> ActionResult:
        """
        هندلر ایمن که هیچ کاری انجام نمی‌دهد و فقط گزارش می‌دهد.
        این رفتار برای جلوگیری از تغییرات ناخواسته سیستم است.
        """
        return ActionResult(
            action_id=action.action_id,
            status=ExecutionStatus.SKIPPED,
            message=f"Action '{action.action_id}' is registered but not implemented (Safe Mode).",
            details={"description": action.description, "priority": action.priority}
        )

    def register_handler(self, action_id: str, handler: HandlerFunc) -> None:
        """ثبت یک هندلر جدید برای یک اکشن خاص."""
        self._handlers[action_id] = handler

    def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """
        اجرای تمام اکشن‌های موجود در طرح.
        
        - اگر اکشنی ناشناخته باشد، با وضعیت FAILED برگردانده می‌شود (بدون کرش).
        - اگر اکشنی شناخته شده باشد، هندلر مربوطه اجرا می‌شود.
        - ترتیب اجرا قطعی است.
        """
        results: list[ActionResult] = []

        for action in plan.actions:
            handler = self._handlers.get(action.action_id)
            
            if handler:
                try:
                    result = handler(action)
                    results.append(result)
                except Exception as exc:  # noqa: BLE001
                    # اگر هندلر خطا داد، آن را به عنوان FAILED ثبت کن
                    # این بلوک عمداً همه استثناها را می‌گیرد تا از کرش کردن جلوگیری کند
                    results.append(ActionResult(
                        action_id=action.action_id,
                        status=ExecutionStatus.FAILED,
                        message=f"Execution error: {exc!s}",
                        details={}
                    ))
            else:
                # اکشن ناشناخته: بدون کرش، فقط گزارش خطا
                results.append(ActionResult(
                    action_id=action.action_id,
                    status=ExecutionStatus.FAILED,
                    message=f"Action '{action.action_id}' is not implemented.",
                    details={}
                ))

        return ExecutionResult.create_from_actions(results)

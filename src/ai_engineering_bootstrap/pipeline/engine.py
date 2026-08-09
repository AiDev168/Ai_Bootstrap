#!/usr/bin/env python3
"""Pipeline Engine - Orchestrates flow with bounded recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport
from ai_engineering_bootstrap.executor import ExecutionResult, ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.recovery import (
    FailureType,
    RetryPolicy,
)
from ai_engineering_bootstrap.executor.validator import (
    ExecutionPlanValidator,
    ValidationResult,
)
from ai_engineering_bootstrap.planner import PlannerEngine
from ai_engineering_bootstrap.planner.models import ExecutionPlan


@dataclass(frozen=True)
class PipelineResult:
    """Complete result of the full execution pipeline."""
    audit_report: AuditReport
    original_plan: ExecutionPlan
    validation_result: ValidationResult
    execution_result: ExecutionResult | None
    verification_result: Any | None  # فعلاً ساده‌سازی شده
    replan_requested: bool = False
    replanned_plan: ExecutionPlan | None = None
    failure_records: list[Any] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        if self.execution_result is None:
            return False
        if not self.validation_result.is_valid:
            return False
        return self.execution_result.is_success


class PipelineEngine:
    """
    Orchestrates the full flow: Audit → Plan → Validate → Execute → Verify → Recover.
    Implements bounded retry/replan logic.
    """

    def run(
        self,
        mode: ExecutionMode = ExecutionMode.SAFE,
        max_retry_attempts: int = 1
    ) -> PipelineResult:
        """
        Executes the pipeline with optional bounded recovery.
        Args:
            mode: ExecutionMode.SAFE or REAL.
            max_retry_attempts: Maximum attempts per action (default 1 for safety).
        """
        # Stage 1: Audit
        audit_service = default_audit_service()
        report = audit_service.run()

        # Stage 2: Planning (Original Plan)
        planner = PlannerEngine()
        original_plan = planner.generate_plan(report)

        # Stage 3: Validation
        validator = ExecutionPlanValidator()
        validation_result = validator.validate(original_plan)

        if not validation_result.is_valid:
            return PipelineResult(
                audit_report=report,
                original_plan=original_plan,
                validation_result=validation_result,
                execution_result=None,
                verification_result=None,
                replan_requested=False
            )

        # Stage 4: Execution with Bounded Recovery
        # برای سادگی در این فیچر، Retry را در سطح اکشن‌های منفرد مدیریت می‌کنیم
        # اما اینجا ساختار کلی را حفظ می‌کنیم.
        # توجه: ExecutorEngine خودش مسئول Retry تک‌تک اکشن‌ها بر اساس Policy است.
        executor = ExecutorEngine(mode=mode)
        # اعمال سیاست Retry به Executor (از طریق آرگومان یا تنظیم داخلی)
        # در این پیاده‌سازی، Executor مستقیماً از RetryPolicy استفاده می‌کند.
        # ما اینجا فقط یک بار اجرا می‌کنیم و نتیجه را می‌گیریم.
        # اگر بخواهیم حلقه کلی داشته باشیم، باید اینجا لوپ بگذاریم، اما برای ایمنی
        # و جلوگیری از پیچیدگی، منطق Retry را به Executor محول می‌کنیم تا روی هر اکشن اعمال کند.
        exec_result = executor.execute(original_plan, max_attempts=max_retry_attempts)

        # Stage 5: Verification (ساده‌سازی شده برای این فیچر)
        # فعلاً فرض می‌کنیم اگر اجرا موفق بود، وریفای هم موفق است مگر خلافش ثابت شود.
        # در فیچرهای بعدی لایه Verifier مستقل فراخوانی می‌شود.
        verification_result = None
        # بررسی نیاز به Re-plan بر اساس نتایج شکست
        replan_requested = False
        failure_records = []
        # استخراج رکوردهای شکست از نتایج اجرا
        policy = RetryPolicy(max_attempts=max_retry_attempts)
        for res in exec_result.results:
            record = policy.classify_failure(res)
            if record.failure_type != FailureType.NONE:
                failure_records.append(record)
                if record.requires_replan:
                    replan_requested = True

        # اگر Re-plan درخواست شده، فعلاً فقط پرچم را بالا می‌بریم (Foundation)
        # اجرای واقعی Re-plan نیازمند تایید صریح یا لایه Agent است.
        replanned_plan = None
        if replan_requested:
            # در این مرحله Foundation، ما فقط سیگنال می‌دهیم.
            # اجرای مجدد Planner نیازمند ورودی جدید یا تایید است.
            pass

        return PipelineResult(
            audit_report=report,
            original_plan=original_plan,
            validation_result=validation_result,
            execution_result=exec_result,
            verification_result=verification_result,
            replan_requested=replan_requested,
            replanned_plan=replanned_plan,
            failure_records=failure_records
        )

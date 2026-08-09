#!/usr/bin/env python3
"""Pipeline Engine - Orchestrates Audit, Plan, Execute, Verify."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport
from ai_engineering_bootstrap.executor import ExecutionResult, ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.validator import (
    ExecutionPlanValidator,
    ValidationResult,
)
from ai_engineering_bootstrap.executor.verifier import VerificationResult
from ai_engineering_bootstrap.planner import PlannerEngine
from ai_engineering_bootstrap.planner.models import ExecutionPlan


@dataclass(frozen=True)
class PipelineResult:
    audit_report: AuditReport
    plan: ExecutionPlan
    validation_result: ValidationResult
    execution_result: ExecutionResult | None
    verification_results: list[VerificationResult] | None
    
    @property
    def is_success(self) -> bool:
        if not self.validation_result.is_valid or self.execution_result is None:
            return False
        if not self.execution_result.is_success:
            return False
        # اگر وریفیکیشن انجام شده، باید همه VERIFIED باشند (یا SKIPPED مجاز است؟)
        # برای سخت‌گیری: اگر وریفیکیشنی هست، نباید FAILED باشد.
        if self.verification_results:
            for vr in self.verification_results:
                if vr.status.value == "failed":
                    return False
        return True


class PipelineEngine:
    def run(self, mode: ExecutionMode = ExecutionMode.SAFE) -> PipelineResult:
        # 1. Audit
        audit_service = default_audit_service()
        report = audit_service.run()
        # 2. Plan
        planner = PlannerEngine()
        plan = planner.generate_plan(report)
        
        # 3. Validate
        validator = ExecutionPlanValidator()
        validation_result = validator.validate(plan)
        if not validation_result.is_valid:
            return PipelineResult(
                audit_report=report,
                plan=plan,
                validation_result=validation_result,
                execution_result=None,
                verification_results=None
            )
        # 4. Execute
        executor = ExecutorEngine(mode=mode)
        exec_result = executor.execute(plan)
        # 5. Verify (فقط اگر اجرا موفق بوده باشد)
        verification_results = None
        if exec_result.is_success and len(exec_result.results) > 0:
            verification_results = executor.verify(exec_result)
        elif len(exec_result.results) > 0:
            # اگر اجرا شده ولی خطا داشته، وریفیکیشن را اسکیپ کن اما گزارش بده
            verification_results = []
            for res in exec_result.results:
                 verification_results.append(VerificationResult(
                     action_id=res.action_id,
                     status="skipped",
                     message="Execution failed, verification skipped.",
                     details={"execution_status": res.status.value}
                 ))

        return PipelineResult(
            audit_report=report,
            plan=plan,
            validation_result=validation_result,
            execution_result=exec_result,
            verification_results=verification_results
        )

#!/usr/bin/env python3
"""Pipeline Engine - Orchestrates the Doctor → Planner → Executor flow."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport
from ai_engineering_bootstrap.executor import (
    ExecutionResult,
    ExecutorEngine,
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
    plan: ExecutionPlan
    validation_result: ValidationResult  # جدید: نتیجه اعتبارسنجی
    execution_result: ExecutionResult
    
    @property
    def is_success(self) -> bool:
        """Returns True if validation passed AND execution completed without failures."""
        if not self.validation_result.is_valid:
            return False
        return self.execution_result.is_success


class PipelineEngine:
    """
    Orchestrates the full flow: Audit → Plan → Validate → Execute.
    
    This class is purely an orchestration layer. It does not contain
    business logic for probing, planning decisions, or action execution.
    """

    def run(self) -> PipelineResult:
        """
        Executes the full pipeline:
        1. Runs AuditService to get AuditReport.
        2. Uses PlannerEngine to generate ExecutionPlan.
        3. Uses ExecutionPlanValidator to validate the plan (Safety Gate).
        4. If valid, uses ExecutorEngine to execute the plan.
           If invalid, stops and returns a failure result without executing.
        
        Returns a PipelineResult containing all intermediate results.
        """
        # Stage 1: Audit (Observation)
        audit_service = default_audit_service()
        report = audit_service.run()
        
        # Stage 2: Planning (Decision)
        planner = PlannerEngine()
        plan = planner.generate_plan(report)
        
        # Stage 3: Validation (Safety Gate)
        validator = ExecutionPlanValidator()
        validation_result = validator.validate(plan)
        # Stage 4: Execution (Action - Safe/Mock)
        # ONLY if validation passes
        if not validation_result.is_valid:
            # ساخت نتیجه اجرای خالی با وضعیت شکست به دلیل عدم اعتبارسنجی
            exec_result = ExecutionResult(
                is_success=False,
                results=[],
                summary=f"Execution blocked by Safety Gate: {', '.join(validation_result.errors)}"
            )
            return PipelineResult(
                audit_report=report,
                plan=plan,
                validation_result=validation_result,
                execution_result=exec_result
            )
        executor = ExecutorEngine()
        exec_result = executor.execute(plan)
        return PipelineResult(
            audit_report=report,
            plan=plan,
            validation_result=validation_result,
            execution_result=exec_result
        )

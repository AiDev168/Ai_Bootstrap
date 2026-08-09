#!/usr/bin/env python3
"""Pipeline Engine - Orchestrates the full flow with Execution Mode support."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport
from ai_engineering_bootstrap.executor import ExecutionResult, ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
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
    validation_result: ValidationResult
    execution_result: ExecutionResult | None
    safety_decisions: dict[str, str] = field(default_factory=dict) # action_id -> reason
    
    @property
    def is_success(self) -> bool:
        if self.execution_result is None:
            return False
        return self.execution_result.is_success and self.validation_result.is_valid


class PipelineEngine:
    """Orchestrates the full flow: Audit → Plan → Validate → Execute."""

    def run(self, mode: ExecutionMode = ExecutionMode.SAFE) -> PipelineResult:
        """Executes the full pipeline."""
        # Stage 1: Audit
        audit_service = default_audit_service()
        report = audit_service.run()
        # Stage 2: Planning
        planner = PlannerEngine()
        plan = planner.generate_plan(report)
        
        # Stage 3: Validation (Safety Gate Structure)
        validator = ExecutionPlanValidator()
        validation_result = validator.validate(plan)
        if not validation_result.is_valid:
            return PipelineResult(
                audit_report=report,
                plan=plan,
                validation_result=validation_result,
                execution_result=None
            )
        # Stage 4: Execution (Controlled by Mode & Policy)
        executor = ExecutorEngine(mode=mode)
        exec_result = executor.execute(plan)
        # استخراج تصمیمات Safety Gate از نتایج اجرا
        safety_decisions = {}
        if exec_result:
            for res in exec_result.results:
                if "Safety Gate Denied" in res.message:
                    safety_decisions[res.action_id] = res.message
        return PipelineResult(
            audit_report=report,
            plan=plan,
            validation_result=validation_result,
            execution_result=exec_result,
            safety_decisions=safety_decisions
        )

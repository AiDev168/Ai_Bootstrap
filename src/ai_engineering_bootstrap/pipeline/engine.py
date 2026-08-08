"""Pipeline Engine - Orchestrates the Doctor → Planner → Executor flow."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport
from ai_engineering_bootstrap.executor import ExecutionResult, ExecutorEngine
from ai_engineering_bootstrap.planner import PlannerEngine
from ai_engineering_bootstrap.planner.models import ExecutionPlan


@dataclass(frozen=True)
class PipelineResult:
    """Complete result of the full execution pipeline."""
    audit_report: AuditReport
    plan: ExecutionPlan
    execution_result: ExecutionResult
    
    @property
    def is_success(self) -> bool:
        """Returns True if the entire pipeline completed without execution failures."""
        return self.execution_result.is_success


class PipelineEngine:
    """
    Orchestrates the full flow: Audit → Plan → Execute.
    
    This class is purely an orchestration layer. It does not contain
    business logic for probing, planning decisions, or action execution.
    """

    def run(self) -> PipelineResult:
        """
        Executes the full pipeline:
        1. Runs AuditService to get AuditReport.
        2. Uses PlannerEngine to generate ExecutionPlan.
        3. Uses ExecutorEngine to execute the plan (Safe/Mock mode).
        
        Returns a PipelineResult containing all intermediate results.
        """
        # Stage 1: Audit (Observation)
        audit_service = default_audit_service()
        report = audit_service.run()
        
        # Stage 2: Planning (Decision)
        planner = PlannerEngine()
        plan = planner.generate_plan(report)
        
        # Stage 3: Execution (Action - Safe/Mock)
        executor = ExecutorEngine()
        exec_result = executor.execute(plan)
        
        return PipelineResult(
            audit_report=report,
            plan=plan,
            execution_result=exec_result
        )

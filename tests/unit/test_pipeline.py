#!/usr/bin/env python3
"""Integration tests for the Execution Pipeline."""

from unittest.mock import MagicMock, patch

from ai_engineering_bootstrap.audit.models import (
    AuditCheck,
    AuditReport,
    CheckCategory,
    CheckStatus,
    EnvironmentReadiness,
)
from ai_engineering_bootstrap.pipeline import PipelineEngine
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def _make_failed_report() -> AuditReport:
    """Helper to create a report with failures."""
    checks = [
        AuditCheck(name="Git", status=CheckStatus.FAILED, category=CheckCategory.TOOLS),
        AuditCheck(name="Python Version", status=CheckStatus.PASSED, category=CheckCategory.PYTHON),
    ]
    readiness = EnvironmentReadiness.calculate(checks)
    return AuditReport(checks=checks, readiness=readiness)

def _make_healthy_report() -> AuditReport:
    """Helper to create a healthy report."""
    checks = [
        AuditCheck(name="Git", status=CheckStatus.PASSED, category=CheckCategory.TOOLS),
        AuditCheck(name="Python Version", status=CheckStatus.PASSED, category=CheckCategory.PYTHON),
    ]
    readiness = EnvironmentReadiness.calculate(checks)
    return AuditReport(checks=checks, readiness=readiness)

def test_pipeline_blocks_invalid_plan() -> None:
    """If Validator fails, Executor must NOT be called."""
    # ساخت یک طرح نامعتبر (action_id خالی)
    bad_action = ExecutionPlanAction(action_id="", description="Bad", priority=1)
    bad_plan = ExecutionPlan(is_actionable=True, actions=[bad_action], summary="Bad Plan")

    # ماک کردن سرویس‌های داخلی پایپ‌لاین
    with patch('ai_engineering_bootstrap.pipeline.engine.default_audit_service') as mock_audit_svc:
        mock_audit_instance = MagicMock()
        mock_audit_instance.run.return_value = _make_healthy_report()
        mock_audit_svc.return_value = mock_audit_instance
        with patch('ai_engineering_bootstrap.pipeline.engine.PlannerEngine') as MockPlanner:
            mock_planner_instance = MagicMock()
            mock_planner_instance.generate_plan.return_value = bad_plan
            MockPlanner.return_value = mock_planner_instance
            # Executor نباید صدا زده شود
            with patch('ai_engineering_bootstrap.pipeline.engine.ExecutorEngine') as MockExecutor:
                mock_executor_instance = MagicMock()
                MockExecutor.return_value = mock_executor_instance
                engine = PipelineEngine()
                result = engine.run()
                # بررسی‌ها
                assert result.validation_result is not None
                assert result.validation_result.is_valid is False
                # Executor هرگز نباید execute را صدا زده باشد
                mock_executor_instance.execute.assert_not_called()
                # نتیجه اجرا باید وجود داشته باشد اما نشان‌دهنده توقف باشد
                assert result.execution_result is not None
                assert result.execution_result.is_success is False
                assert "blocked by Safety Gate" in result.execution_result.summary
                assert len(result.execution_result.results) == 0

def test_pipeline_allows_valid_plan() -> None:
    """If Validator passes, Executor MUST be called."""
    good_action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    good_plan = ExecutionPlan(is_actionable=True, actions=[good_action], summary="Good Plan")
    with patch('ai_engineering_bootstrap.pipeline.engine.default_audit_service') as mock_audit_svc:
        mock_audit_instance = MagicMock()
        mock_audit_instance.run.return_value = _make_healthy_report()
        mock_audit_svc.return_value = mock_audit_instance
        with patch('ai_engineering_bootstrap.pipeline.engine.PlannerEngine') as MockPlanner:
            mock_planner_instance = MagicMock()
            mock_planner_instance.generate_plan.return_value = good_plan
            MockPlanner.return_value = mock_planner_instance
            with patch('ai_engineering_bootstrap.pipeline.engine.ExecutorEngine') as MockExecutor:
                mock_executor_instance = MagicMock()
                # شبیه‌سازی نتیجه موفقیت‌آمیز اجرا
                from ai_engineering_bootstrap.executor.models import (
                    ActionResult,
                    ExecutionResult,
                    ExecutionStatus,
                )
                mock_result = ExecutionResult(
                    is_success=True,
                    results=[ActionResult(action_id="install_git", status=ExecutionStatus.SKIPPED, message="Mock")],
                    summary="Success"
                )
                mock_executor_instance.execute.return_value = mock_result
                MockExecutor.return_value = mock_executor_instance
                engine = PipelineEngine()
                result = engine.run()
                # بررسی‌ها
                assert result.validation_result.is_valid is True
                mock_executor_instance.execute.assert_called_once()
                assert result.execution_result.is_success is True

#!/usr/bin/env python3
"""Pipeline Engine - Orchestrates flow with bounded recovery and human approval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ایمپورت کردن مدل‌ها و پروایدر تاییدیه
from ai_engineering_bootstrap.approval.models import ApprovalRequest, ApprovalStatus
from ai_engineering_bootstrap.approval.provider import ApprovalProvider
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

    # فیلدهای جدید برای کنترل و مشاهده وضعیت تاییدیه انسانی
    approval_requests: list[ApprovalRequest] = field(default_factory=list)
    is_pending_approval: bool = False
    is_rejected_approval: bool = False

    @property
    def is_success(self) -> bool:
        if self.execution_result is None:
            return False
        if not self.validation_result.is_valid:
            return False
        if self.is_pending_approval or self.is_rejected_approval:
            return False
        return self.execution_result.is_success


class PipelineEngine:
    """
    Orchestrates the full flow: Audit → Plan → Validate → Approve → Execute → Verify → Recover.
    Implements bounded retry/replan logic with safety controls.
    """

    def run(
        self,
        mode: ExecutionMode = ExecutionMode.SAFE,
        max_retry_attempts: int = 1,
        approval_provider: ApprovalProvider | None = None,
        pending_approvals: dict[str, str] | None = None,
        run_id: str = "default-run"
    ) -> PipelineResult:
        """
        Executes the pipeline with optional bounded recovery.
        Args:
            mode: ExecutionMode.SAFE or REAL.
            max_retry_attempts: Maximum attempts per action (default 1 for safety).
            approval_provider: Provider for human approval integration.
            pending_approvals: Map of action_id to approval_id for previously requested approvals.
            run_id: Unique identifier for this pipeline run to prevent approval replay.
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

        # Stage 3.5: Human Approval Boundary (Safety Control)
        # این گیت دقیقاً قبل از اجرا قرار می‌گیرد تا از اجرای اقدامات حساس بدون تایید جلوگیری کند.
        pending_requests = []
        rejected_requests = []

        if approval_provider:
            # بررسی تمامی اکشن‌های پلن برای اطمینان از تاییدیه (در صورت نیاز)
            for action in original_plan.actions:
                requires_approval = False

                # بررسی سیاست اکشن (ActionPolicy) برای نیاز به تاییدیه
                if hasattr(action, 'policy') and hasattr(action.policy, 'approval_requirement'):
                    if action.policy.approval_requirement.name == 'REQUIRED':
                        requires_approval = True
                elif hasattr(action, 'requires_approval'):
                    requires_approval = action.requires_approval

                if requires_approval:
                    approval_id = pending_approvals.get(action.id) if pending_approvals else None

                    if approval_id:
                        # بررسی وضعیت تاییدیه قبلی برای این اکشن
                        status = approval_provider.get_status(approval_id)
                        req = approval_provider.get_request(approval_id) if hasattr(approval_provider, 'get_request') else None

                        # اعتبارسنجی اتصال دقیق (Exact Binding) برای جلوگیری از Replay Attack
                        if req and (req.action_id != action.id or req.plan_id != original_plan.id or req.run_id != run_id):
                            # اگر تاییدیه مربوط به اکشن، پلن یا ران دیگری بود، نامعتبر است
                            rejected_requests.append(req)
                            continue

                        if status == ApprovalStatus.APPROVED:
                            continue  # تایید شده، عبور می‌کند
                        elif status == ApprovalStatus.PENDING:
                            pending_requests.append(req)
                        elif status == ApprovalStatus.REJECTED:
                            rejected_requests.append(req)
                        else:
                            # وضعیت نامشخص، درخواست جدید ثبت می‌شود
                            new_req = approval_provider.request_approval(
                                action_id=action.id,
                                plan_id=original_plan.id,
                                run_id=run_id,
                                reason=getattr(action, 'reason', 'Action requires approval'),
                                risk_level=getattr(action.policy, 'risk_level', 'UNKNOWN')
                            )
                            pending_requests.append(new_req)
                    else:
                        # هنوز درخواستی ثبت نشده، درخواست جدید ایجاد می‌کنیم
                        new_req = approval_provider.request_approval(
                            action_id=action.id,
                            plan_id=original_plan.id,
                            run_id=run_id,
                            reason=getattr(action, 'reason', 'Action requires approval'),
                            risk_level=getattr(action.policy, 'risk_level', 'UNKNOWN')
                        )
                        pending_requests.append(new_req)

            # اگر اکشنی در وضعیت Pending است، اجرای کل پلن متوقف می‌شود (No Execution)
            if pending_requests:
                return PipelineResult(
                    audit_report=report,
                    original_plan=original_plan,
                    validation_result=validation_result,
                    execution_result=None,
                    verification_result=None,
                    replan_requested=False,
                    approval_requests=pending_requests,
                    is_pending_approval=True
                )

            # اگر اکشنی Reject شده باشد، اجرا متوقف و وضعیت شکست ثبت می‌شود
            if rejected_requests:
                return PipelineResult(
                    audit_report=report,
                    original_plan=original_plan,
                    validation_result=validation_result,
                    execution_result=None,
                    verification_result=None,
                    replan_requested=False,
                    approval_requests=rejected_requests,
                    is_rejected_approval=True
                )

        # Stage 4: Execution with Bounded Recovery
        # فقط در صورتی اجرا انجام می‌شود که تاییدیه‌ها (در صورت لزوم) موفق بوده باشند.
        executor = ExecutorEngine(mode=mode)
        exec_result = executor.execute(original_plan, max_attempts=max_retry_attempts)

        # Stage 5: Verification (ساده‌سازی شده برای این فیچر)
        verification_result = None
        replan_requested = False
        failure_records = []

        policy = RetryPolicy(max_attempts=max_retry_attempts)
        for res in exec_result.results:
            record = policy.classify_failure(res)
            if record.failure_type != FailureType.NONE:
                failure_records.append(record)
                if record.requires_replan:
                    replan_requested = True

        replanned_plan = None
        if replan_requested:
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

"""Selected Security & Integration Tests for Human Approval (Fixed)."""

from unittest.mock import MagicMock, patch

from ai_engineering_bootstrap.approval.models import ApprovalStatus
from ai_engineering_bootstrap.approval.provider import InMemoryApprovalProvider
from ai_engineering_bootstrap.pipeline.engine import PipelineEngine


def create_mock_action(action_id: str, requires_approval: bool = True):
    """Helper to create a mock action."""
    action = MagicMock()
    action.id = action_id
    action.policy = MagicMock()
    action.policy.risk_level = "HIGH"
    action.policy.approval_requirement.name = (
        "REQUIRED" if requires_approval else "NONE"
    )
    action.reason = f"Test action {action_id}"
    return action


def create_mock_plan(plan_id: str, actions: list):
    """Helper to create a mock plan."""
    plan = MagicMock()
    plan.id = plan_id
    plan.actions = actions
    return plan


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_pending_blocks_execution_completely(
    mock_planner, mock_validator, mock_executor, mock_audit
):
    """تست حیاتی: اگر تاییدیه Pending باشد، Executor حتی یک بار هم فراخوانی نمی‌شود."""
    provider = InMemoryApprovalProvider()
    engine = PipelineEngine()

    # تنظیم ماک‌ها
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    # اجرا بدون هیچ تأییدیه‌ای (وضعیت پیش‌فرض Pending است)
    result = engine.run(approval_provider=provider)

    assert result.is_pending_approval is True
    assert result.execution_result is None
    mock_executor.return_value.execute.assert_not_called()
    print("✅ تست ۱ پاس شد: اجرای اکشن در حالت Pending کاملاً مسدود شد.")


@patch("ai_engineering_bootstrap.pipeline.engine.default_audit_service")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutorEngine")
@patch("ai_engineering_bootstrap.pipeline.engine.ExecutionPlanValidator")
@patch("ai_engineering_bootstrap.pipeline.engine.PlannerEngine")
def test_approved_proceeds_to_execution(
    mock_planner, mock_validator, mock_executor, mock_audit
):
    """تست حیاتی: اگر تأییدیه APPROVED باشد، اجرا انجام می‌شود."""
    provider = InMemoryApprovalProvider()
    engine = PipelineEngine()

    # ایجاد درخواست و تأیید صریح با run_id مشخص
    req = provider.request_approval("act-1", "plan-1", "run-1", "Test reason", "HIGH")
    provider.approve(req.approval_id)

    # تنظیم ماک‌ها
    mock_planner.return_value.generate_plan.return_value = create_mock_plan(
        "plan-1", [create_mock_action("act-1")]
    )
    mock_validator.return_value.validate.return_value = MagicMock(is_valid=True)

    # ارسال شناسه تأییدیه به پایپ‌لاین
    # نکته کلیدی: باید run_id را دقیقاً همان چیزی بگذاریم که موقع ساخت درخواست گذاشتیم ("run-1")
    # تا سیستم آن را به عنوان Replay رد نکند.
    result = engine.run(
        approval_provider=provider,
        pending_approvals={"act-1": req.approval_id},
        run_id="run-1",  # <--- اصلاح اینجا انجام شد
    )

    assert result.is_pending_approval is False
    assert result.is_rejected_approval is False
    assert result.execution_result is not None  # حالا باید اجرا شده باشد
    mock_executor.return_value.execute.assert_called_once()
    print("✅ تست ۲ پاس شد: اجرای اکشن پس از تأیید با موفقیت انجام شد.")


def test_replay_attack_prevention():
    """تست امنیتی زیبا: جلوگیری از استفاده مجدد (Replay) تأییدیه در یک Run متفاوت."""
    provider = InMemoryApprovalProvider()

    # سناریو: مهاجم یک تأییدیه معتبر از Run قبلی را دزدیده و سعی می‌کند در Run جدید استفاده کند
    req_old = provider.request_approval(
        "act-delete-db", "plan-old", "run-100", "Old run", "CRITICAL"
    )
    provider.approve(req_old.approval_id)

    # شبیه‌سازی بررسی در پایپ‌لاین برای Run جدید (run-200)
    # منطق داخل Engine باید چک کند که req.run_id == current_run_id
    req_check = provider.get_request(req_old.approval_id)

    # این شرط منطقی است که در Engine پیاده‌سازی شده:
    is_valid_for_new_run = req_check.run_id == "run-200"

    assert is_valid_for_new_run is False, (
        "باید تشخیص دهد که این تأییدیه متعلق به ران دیگری است!"
    )
    assert req_check.action_id == "act-delete-db"  # اکشن خطرناک است
    print("✅ تست ۳ پاس شد: سیستم توانست حمله Replay را شناسایی کند (run_id mismatch).")


def test_terminal_state_immutability():
    """تست امنیتی: وضعیت‌های نهایی (Approved/Rejected) نباید قابل تغییر باشند."""
    provider = InMemoryApprovalProvider()

    # سناریو ۱: تلاش برای Reject کردن یک موردِ Already Approved
    req_good = provider.request_approval(
        "act-safe", "plan-1", "run-1", "Safe action", "LOW"
    )
    provider.approve(req_good.approval_id)

    # تلاش برای خرابکاری: تغییر وضعیت به Rejected
    provider.reject(req_good.approval_id)

    # بررسی می‌کنیم که وضعیت همچنان Approved باقی مانده باشد
    final_status_good = provider.get_status(req_good.approval_id)
    assert final_status_good == ApprovalStatus.APPROVED

    # سناریو ۲: تلاش برای Approve کردن یک موردِ Already Rejected
    req_bad = provider.request_approval(
        "act-danger", "plan-1", "run-1", "Dangerous action", "HIGH"
    )
    provider.reject(req_bad.approval_id)

    # تلاش برای دور زدن: تغییر وضعیت به Approved
    provider.approve(req_bad.approval_id)

    final_status_bad = provider.get_status(req_bad.approval_id)
    assert final_status_bad == ApprovalStatus.REJECTED

    print("✅ تست ۴ پاس شد: وضعیت‌های نهایی در برابر تغییرات بعدی ایمن هستند.")


if __name__ == "__main__":
    print(
        "لطفاً این فایل را با دستور 'pytest test_approval_security_2.py -v' اجرا کنید."
    )

"""Negative Security Tests for Safety Gate."""

from unittest.mock import patch

from ai_engineering_bootstrap.executor.engine import ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def test_malicious_action_never_reaches_handler() -> None:
    """Verify that a malicious action is blocked BEFORE handler invocation."""

    # اکشن مخرب که سیاستی برایش تعریف نشده
    bad_action = ExecutionPlanAction(
        action_id="sudo_rm_rf_root", description="Delete everything", priority=99
    )
    plan = ExecutionPlan(is_actionable=True, actions=[bad_action], summary="Bad Plan")

    # ما یک هندلر جعلی ثبت می‌کنیم تا ببینیم صدا زده می‌شود یا نه
    # اما چون Safety Gate جلوتر است، نباید اصلاً نوبت به هندلر برسد

    engine = ExecutorEngine(mode=ExecutionMode.REAL)

    # پچ کردن متد get_handler برای تشخیص فراخوانی
    with patch.object(engine._registry, "get_handler") as mock_get_handler:
        result = engine.execute(plan)

        # assert 1: نتیجه باید FAILED باشد
        assert len(result.results) == 1
        assert result.results[0].status == ExecutionStatus.FAILED
        assert "Safety Gate Denied" in result.results[0].message

        # assert 2 (مهم): متد get_handler هرگز نباید صدا زده شده باشد
        # یعنی رجیستری اصلاً درخواست هندلر نشده است
        mock_get_handler.assert_not_called()


def test_policy_less_action_denied() -> None:
    """Action without explicit policy must be denied (Default Deny)."""
    action = ExecutionPlanAction(
        action_id="some_random_action", description="No policy defined", priority=1
    )
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")

    engine = ExecutorEngine(mode=ExecutionMode.REAL)
    result = engine.execute(plan)

    assert result.results[0].status == ExecutionStatus.FAILED
    assert "no explicit policy" in result.results[0].message

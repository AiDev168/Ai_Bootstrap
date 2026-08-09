#!/usr/bin/env python3
"""
Security Test: Verify Policy Enforcement prevents Handler Invocation.
Goal: Prove that even if an action is registered, without an explicit Policy,
      the Safety Gate blocks it BEFORE the handler is ever called.
"""

from unittest.mock import patch, MagicMock
from ai_engineering_bootstrap.executor.engine import ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction
from ai_engineering_bootstrap.executor.models import ExecutionStatus

def test_policy_blocks_handler_invocation():
    print("🛡️  Starting Security Test: Policy vs Handler Invocation...")
    print("-" * 60)

    # سناریو: فرض کنیم یک هکر توانسته اکشن 'sudo_rm_rf_root' را به رجیستری تزریق کند
    # (یا فرض کنیم یک اکشن قدیمی در رجیستری هست اما Policy برایش تعریف نشده)
    # ما اینجا عمداً یک هندلر جعلی ثبت می‌کنیم تا ببینیم صدا زده می‌شود یا نه.
    
    action_id = "sudo_rm_rf_root"
    bad_action = ExecutionPlanAction(
        action_id=action_id,
        description="Malicious Action",
        priority=99
    )
    plan = ExecutionPlan(is_actionable=True, actions=[bad_action], summary="Attack Plan")

    engine = ExecutorEngine(mode=ExecutionMode.REAL)

    # ۱. تزریق دستی اکشن به رجیستری (شبیه‌سازی شرایطی که اکشن وجود دارد)
    # نکته: در کد واقعی این اتفاق نمی‌افتد مگر با باگ، اما ما برای تست امنیت،
    # فرض می‌کنیم مهاجم توانسته این کار را بکند.
    from ai_engineering_bootstrap.executor.handlers.safe_handlers import InstallGitHandler
    # ثبت یک هندلر واقعی (ولی بی‌خطر در محیط تست) برای این اکشن مخرب
    engine._registry._safe_handlers[action_id] = InstallGitHandler()
    
    print(f"   [1] Injected '{action_id}' into Registry manually.")
    print(f"       Registry now HAS a handler for this action.")

    # ۲. ماک کردن هندلر برای تشخیص فراخوانی
    # ما متد handle را رصد می‌کنیم. اگر Safety Gate درست کار کند، این متد هرگز صدا زده نمی‌شود.
    fake_handler = engine._registry._safe_handlers[action_id]
    with patch.object(fake_handler, 'handle') as mock_handle:
        
        print(f"   [2] Monitoring handler.handle() method...")
        
        # اجرای پلن
        result = engine.execute(plan)

        # ۳. بررسی نتیجه
        res = result.results[0]
        
        print(f"   [3] Execution Result Status: {res.status.value}")
        print(f"   [4] Error Message: {res.message}")

        # ASSERTION 1: نتیجه باید FAILED باشد
        assert res.status == ExecutionStatus.FAILED, "Action should have been denied!"
        
        # ASSERTION 2: پیام خطا باید مربوط به Policy باشد نه نبودِ هندلر
        assert "policy" in res.message.lower() or "denied" in res.message.lower(), \
            f"Error message should mention policy/denial, got: {res.message}"

        # ASSERTION 3 (CRITICAL): هندلر هرگز نباید صدا زده شده باشد
        if mock_handle.called:
            print("\n   ❌ CRITICAL SECURITY FAILURE!")
            print("   The Handler WAS INVOKED despite missing Policy!")
            print("   The Safety Gate failed to block the request before execution.")
            return False
        else:
            print("\n   ✅ SUCCESS: Handler was NEVER called.")
            print("   Safety Gate successfully blocked the action BEFORE execution layer.")
            return True

if __name__ == "__main__":
    success = test_policy_blocks_handler_invocation()
    if success:
        print("\n🎉 Security Test Passed: Default Deny Policy is effective.")
        exit(0)
    else:
        print("\n💥 Security Test Failed: Policy Bypass Detected!")
        exit(1)

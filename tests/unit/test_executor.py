"""Unit tests for the Executor Engine."""

from ai_engineering_bootstrap.executor import ExecutionStatus, ExecutorEngine
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def test_execute_empty_plan() -> None:
    """Empty plan should yield success with no actions."""
    plan = ExecutionPlan(is_actionable=False, actions=[], summary="None")
    engine = ExecutorEngine()
    result = engine.execute(plan)
    
    assert result.is_success is True
    assert len(result.results) == 0
    assert "No actions" in result.summary

def test_execute_known_safe_action() -> None:
    """Known action should be handled safely (SKIPPED)."""
    action = ExecutionPlanAction(
        action_id="install_git",
        description="Install Git",
        priority=1
    )
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    
    engine = ExecutorEngine()
    result = engine.execute(plan)
    
    assert len(result.results) == 1
    res = result.results[0]
    assert res.action_id == "install_git"
    assert res.status == ExecutionStatus.SKIPPED
    assert "Safe Mode" in res.message

# ... (سایر ایمپورت‌ها)

def test_execute_unknown_action_fails_gracefully() -> None:
    """Unknown action should fail gracefully without crashing."""
    action = ExecutionPlanAction(
        action_id="unknown_weird_action",
        description="Do something weird",
        priority=99
    )
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    
    engine = ExecutorEngine()
    result = engine.execute(plan)
    
    assert len(result.results) == 1
    res = result.results[0]
    assert res.status == ExecutionStatus.FAILED
    # پیام جدید Safety Gate
    assert "Safety Gate Denied" in res.message
    assert "no explicit policy" in res.message
def test_execute_mixed_actions() -> None:
    """Mixed known and unknown actions should be handled correctly."""
    actions = [
        ExecutionPlanAction(action_id="install_git", description="Git", priority=1),
        ExecutionPlanAction(action_id="fake_action", description="Fake", priority=2),
        ExecutionPlanAction(action_id="install_docker", description="Docker", priority=3),
    ]
    plan = ExecutionPlan(is_actionable=True, actions=actions, summary="Test")
    
    engine = ExecutorEngine()
    result = engine.execute(plan)
    
    assert len(result.results) == 3
    # اولی باید SKIPPED (موفق در چارچوب ایمن) باشد
    assert result.results[0].status == ExecutionStatus.SKIPPED
    # دومی باید FAILED باشد
    assert result.results[1].status == ExecutionStatus.FAILED
    # سومی باید SKIPPED باشد
    assert result.results[2].status == ExecutionStatus.SKIPPED
    
    # کل پلن شکست خورده محسوب می‌شود
    assert result.is_success is False

def test_execute_deterministic_order() -> None:
    """Execution order must match plan order."""
    actions = [
        ExecutionPlanAction(action_id=f"action_{i}", description=f"Desc {i}", priority=i)
        for i in range(5)
    ]
    # ثبت دستی برای تست ترتیب (چون اکشن‌ها فیک هستند و در رجیستری نیستند)
    # اما ما اینجا فقط ترتیب خروجی را نسبت به ورودی چک می‌کنیم حتی اگر فال شوند
    plan = ExecutionPlan(is_actionable=True, actions=actions, summary="Test")
    
    engine = ExecutorEngine()
    result = engine.execute(plan)
    
    assert len(result.results) == 5
    for i, res in enumerate(result.results):
        assert res.action_id == f"action_{i}"


def test_safe_mode_skipped_actions_do_not_make_run_fail() -> None:
    """Safe-mode simulation is a successful execution outcome, not a failure."""
    action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    result = ExecutorEngine().execute(plan)
    assert result.results[0].status == ExecutionStatus.SKIPPED
    assert result.is_success is True

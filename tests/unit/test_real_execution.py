"""Tests for Controlled Real Execution capabilities."""

from ai_engineering_bootstrap.executor.engine import ExecutorEngine
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.executor.registry import ActionRegistry
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


def test_safe_mode_default_behavior() -> None:
    """SAFE mode should simulate everything."""
    action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    
    engine = ExecutorEngine(mode=ExecutionMode.SAFE)
    result = engine.execute(plan)
    
    assert len(result.results) == 1
    # باید شبیه‌سازی شده باشد (SKIPPED یا SUCCESS بسته به پیاده‌سازی Mock)
    assert result.results[0].status != ExecutionStatus.FAILED # نباید خطای ناشناخته بدهد

def test_real_mode_approved_action() -> None:
    """REAL mode should execute approved read-only actions."""
    action = ExecutionPlanAction(action_id="check_python_version_real", description="Check Py", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    
    engine = ExecutorEngine(mode=ExecutionMode.REAL)
    result = engine.execute(plan)
    
    assert len(result.results) == 1
    res = result.results[0]
    assert res.status == ExecutionStatus.SUCCESS
    assert "sys.version_info" in str(res.details) # باید منبع واقعی را ذکر کند

def test_real_mode_rejects_unapproved_action() -> None:
    """REAL mode must reject actions not explicitly approved for real execution."""
    action = ExecutionPlanAction(action_id="install_git", description="Git", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    
    engine = ExecutorEngine(mode=ExecutionMode.REAL)
    result = engine.execute(plan)
    
    assert len(result.results) == 1
    res = result.results[0]
    assert res.status == ExecutionStatus.FAILED
    assert "not approved for REAL execution" in res.message

def test_real_mode_rejects_unknown_action() -> None:
    """REAL mode must reject unknown malicious actions."""
    action = ExecutionPlanAction(action_id="sudo_rm_rf_root", description="Bad", priority=1)
    plan = ExecutionPlan(is_actionable=True, actions=[action], summary="Test")
    
    engine = ExecutorEngine(mode=ExecutionMode.REAL)
    result = engine.execute(plan)
    
    assert len(result.results) == 1
    assert result.results[0].status == ExecutionStatus.FAILED
    assert "not supported" in result.results[0].message

def test_registry_separation() -> None:
    """Registry must distinguish between safe and real handlers."""
    reg = ActionRegistry()
    
    # اکشن سیف باید در مود سیف کار کند
    assert reg.is_supported("install_git", ExecutionMode.SAFE) is True
    
    # اکشن سیف نباید در مود واقعی (به عنوان واقعی) کار کند
    assert reg.is_supported("install_git", ExecutionMode.REAL) is False
    
    # اکشن واقعی باید در مود واقعی کار کند
    assert reg.is_supported("check_python_version_real", ExecutionMode.REAL) is True

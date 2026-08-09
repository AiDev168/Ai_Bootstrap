"""Unit tests for Safe Handlers."""

from ai_engineering_bootstrap.executor.handlers.base import ExecutionContext
from ai_engineering_bootstrap.executor.handlers.safe_handlers import InstallGitHandler
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


def test_git_handler_simulates() -> None:
    handler = InstallGitHandler()
    action = ExecutionPlanAction(action_id="install_git", description="Install Git", priority=1)
    # ساخت کانتکست صحیح با مود SAFE
    context = ExecutionContext(mode=ExecutionMode.SAFE, dry_run=True)
    
    result = handler.execute(action, context)
    
    assert result.action_id == "install_git"
    assert result.status == ExecutionStatus.SKIPPED
    assert "simulated" in result.message.lower() or "Safe Mode" in result.message

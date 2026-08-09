"""Unit tests for Safe Handlers."""

from ai_engineering_bootstrap.executor.handlers import BaseContext
from ai_engineering_bootstrap.executor.handlers.safe_handlers import InstallGitHandler
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


def test_git_handler_simulates() -> None:
    handler = InstallGitHandler()
    action = ExecutionPlanAction(action_id="install_git", description="Install Git", priority=1)
    context = BaseContext()
    
    result = handler.handle(action, context)
    
    assert result.action_id == "install_git"
    assert result.status == ExecutionStatus.SKIPPED
    assert "simulated" in result.message.lower() or "Safe Mode" in result.message

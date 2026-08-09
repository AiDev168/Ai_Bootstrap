"""Base contracts for Action Handlers and Execution Context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ActionResult
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


@dataclass(frozen=True)
class ExecutionContext:
    """
    Minimal execution context passed to handlers.
    Contains only what is strictly necessary for deterministic execution.
    """
    mode: ExecutionMode
    dry_run: bool = True
    is_approved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ActionHandler(Protocol):
    """
    Protocol for all action handlers (Safe/Mock and Real).
    
    Any handler implementing this protocol can be registered in the ActionRegistry.
    """

    def execute(self, action: ExecutionPlanAction, context: ExecutionContext) -> ActionResult:
        """
        Execute the action and return a structured result.
        
        Args:
            action: The action to execute.
            context: Execution context containing mode, approval state, etc.
            
        Returns:
            ActionResult representing the outcome.
        """
        ...


__all__ = ["ActionHandler", "ExecutionContext"]

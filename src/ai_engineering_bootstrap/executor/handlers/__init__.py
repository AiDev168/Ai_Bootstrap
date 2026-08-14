"""Base contracts for Action Handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ai_engineering_bootstrap.executor.models import ActionResult
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


@dataclass(frozen=True)
class BaseContext:
    """Minimal execution context passed to handlers."""

    dry_run: bool = True
    platform: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


class ActionHandler(Protocol):
    """Protocol for action handlers."""

    def handle(self, action: ExecutionPlanAction, context: BaseContext) -> ActionResult:
        """Execute the action and return a structured result."""
        ...


__all__ = ["ActionHandler", "BaseContext"]

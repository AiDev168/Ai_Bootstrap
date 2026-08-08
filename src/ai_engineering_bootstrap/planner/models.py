"""Models for Execution Planning."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionPlanAction:
    """Represents a single actionable step in an execution plan."""
    action_id: str
    description: str
    priority: int
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    """Represents a complete execution plan derived from an audit report."""
    is_actionable: bool
    actions: list[ExecutionPlanAction]
    summary: str = ""
    
    @staticmethod
    def create_from_audit(report: Any) -> "ExecutionPlan":
        """Factory method to create a plan from an AuditReport."""
        # این متد توسط Engine پر می‌شود، اما ساختار را اینجا تعریف می‌کنیم

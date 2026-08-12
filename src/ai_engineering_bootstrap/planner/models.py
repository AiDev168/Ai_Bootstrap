"""Models for deterministic execution planning."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionPlanAction:
    """Represents a single explicit execution step."""

    action_id: str
    description: str
    priority: int
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    """Execution plan with a stable content-derived plan ID and integrity check."""

    is_actionable: bool
    actions: list[ExecutionPlanAction]
    summary: str = ""
    plan_id: str = ""

    def __post_init__(self) -> None:
        if self.plan_id:
            return
        object.__setattr__(self, "plan_id", self.computed_plan_id())

    def computed_plan_id(self) -> str:
        """Return the content-derived identifier for the current plan contents."""
        canonical = [
            {
                "action_id": action.action_id,
                "description": action.description,
                "priority": action.priority,
                "context": action.context,
            }
            for action in self.actions
        ]
        payload = json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def is_intact(self) -> bool:
        """Return true when the plan contents still match its immutable plan ID."""
        return self.plan_id == self.computed_plan_id()

    @staticmethod
    def create_from_audit(report: Any) -> ExecutionPlan:
        """Compatibility factory for callers that delegate planning elsewhere."""
        return ExecutionPlan(
            is_actionable=False, actions=[], summary="No actions required."
        )

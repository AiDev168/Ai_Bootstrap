"""Models for Execution Results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    """Status of an executed action."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ActionResult:
    """Result of a single action execution."""
    action_id: str
    status: ExecutionStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    """Complete result of an execution run."""
    is_success: bool
    results: list[ActionResult]
    summary: str = ""
    
    @staticmethod
    def create_from_actions(results: list[ActionResult]) -> "ExecutionResult":
        """Factory to create a result from a list of action results."""
        failed_count = sum(1 for r in results if r.status == ExecutionStatus.FAILED)
        is_success = failed_count == 0
        
        if not results:
            summary = "No actions were executed."
        elif is_success:
            summary = f"All {len(results)} actions executed successfully."
        else:
            summary = f"{failed_count} action(s) failed out of {len(results)}."
            
        return ExecutionResult(
            is_success=is_success,
            results=results,
            summary=summary
        )

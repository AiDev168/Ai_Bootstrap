"""Verification contracts and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from ai_engineering_bootstrap.executor.models import ActionResult
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class VerificationStatus(str, Enum):
    """Status of a verification check."""
    VERIFIED = "verified"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class VerificationResult:
    """Result of verifying a single action's outcome."""
    action_id: str
    status: VerificationStatus
    message: str
    expected: Any = None
    observed: Any = None
    details: dict[str, Any] = field(default_factory=dict)


class ActionVerifier(Protocol):
    """Protocol for action verifiers."""

    def verify(
        self, 
        action: ExecutionPlanAction, 
        execution_result: ActionResult, 
        context: Any
    ) -> VerificationResult:
        """
        Independently observe the environment to verify the action's effect.
        
        Must NOT modify the system.
        Must NOT trust execution_result blindly.
        """
        ...


class VerifierRegistry:
    """Registry mapping action IDs to their verifiers."""

    def __init__(self) -> None:
        self._verifiers: dict[str, ActionVerifier] = {}
        # Load default verifiers if any
        from ai_engineering_bootstrap.executor.handlers.verifiers import (
            DEFAULT_VERIFIERS,
        )
        for action_id, verifier in DEFAULT_VERIFIERS.items():
            self._verifiers[action_id] = verifier

    def get_verifier(self, action_id: str) -> ActionVerifier | None:
        return self._verifiers.get(action_id)

    def is_registered(self, action_id: str) -> bool:
        return action_id in self._verifiers


__all__ = [
    "ActionVerifier",
    "VerificationResult",
    "VerificationStatus",
    "VerifierRegistry"
]

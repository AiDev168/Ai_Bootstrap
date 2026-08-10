"""Structured decision models for the Agent layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentDecision:
    """
    Structured decision produced by an Agent/LLM.

    Contains ONLY metadata and intent.
    NO executable code, shell commands, or handler references.
    """

    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reasoning_summary: str = ""
    selected_capability_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    requires_human_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_actionable(self) -> bool:
        """Check if the decision contains selected capabilities."""
        return len(self.selected_capability_ids) > 0


__all__ = ["AgentDecision"]

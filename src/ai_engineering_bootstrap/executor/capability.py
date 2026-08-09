"""Capability Registry for Agent/LLM discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_engineering_bootstrap.executor.mode import ExecutionMode


class CapabilityRisk(str, Enum):
    """Risk classification for capabilities."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Capability:
    """
    Metadata describing a system capability.

    This class contains NO executable logic, handlers, or callables.
    It is purely for discovery and description by future Agent/LLM layers.
    """

    capability_id: str
    name: str
    description: str
    action_id: str
    risk: CapabilityRisk = CapabilityRisk.LOW
    supported_modes: list[ExecutionMode] = field(default_factory=lambda: [ExecutionMode.SAFE])
    requires_human_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports_mode(self, mode: ExecutionMode) -> bool:
        """Check if this capability supports the given execution mode."""
        return mode in self.supported_modes


class DuplicateCapabilityError(ValueError):
    """Raised when attempting to register a duplicate capability ID."""


class CapabilityRegistry:
    """
    Central registry for capability metadata.

    Provides discovery APIs for future Agent/LLM layers without exposing
    execution internals or handlers.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        """
        Register a new capability.

        Raises:
            DuplicateCapabilityError: If the capability_id already exists.
            ValueError: If the capability definition is invalid.
        """
        if not capability.capability_id:
            raise ValueError("capability_id cannot be empty.")
        if not capability.action_id:
            raise ValueError("action_id cannot be empty.")

        if capability.capability_id in self._capabilities:
            raise DuplicateCapabilityError(
                f"Capability '{capability.capability_id}' is already registered."
            )

        self._capabilities[capability.capability_id] = capability

    def get(self, capability_id: str) -> Capability | None:
        """Retrieve a capability by ID. Returns None if not found."""
        return self._capabilities.get(capability_id)

    def list_capabilities(self) -> list[Capability]:
        """Return a sorted list of all registered capabilities."""
        return sorted(self._capabilities.values(), key=lambda c: c.capability_id)

    def find_by_action(self, action_id: str) -> list[Capability]:
        """Find all capabilities associated with a specific action_id."""
        return [c for c in self._capabilities.values() if c.action_id == action_id]

    def is_registered(self, capability_id: str) -> bool:
        """Check if a capability ID is registered."""
        return capability_id in self._capabilities


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CapabilityRisk",
    "DuplicateCapabilityError",
]

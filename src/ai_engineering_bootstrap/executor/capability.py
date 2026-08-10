"""Capability metadata and discovery registry."""

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
    """Pure metadata describing an executable capability."""

    capability_id: str
    name: str
    description: str
    action_id: str
    risk: CapabilityRisk = CapabilityRisk.LOW
    supported_modes: list[ExecutionMode] = field(
        default_factory=lambda: [ExecutionMode.SAFE]
    )
    requires_human_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports_mode(self, mode: ExecutionMode) -> bool:
        """Return whether the capability advertises support for a mode."""
        return mode in self.supported_modes


class DuplicateCapabilityError(ValueError):
    """Raised when attempting to register a duplicate capability ID."""


class CapabilityRegistry:
    """Registry containing discovery metadata only; never execution objects."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        """Register a capability with fail-closed validation."""
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
        """Retrieve capability metadata by ID."""
        return self._capabilities.get(capability_id)

    def list_capabilities(self) -> list[Capability]:
        """Return capabilities in deterministic order."""
        return sorted(self._capabilities.values(), key=lambda item: item.capability_id)

    def find_by_action(self, action_id: str) -> list[Capability]:
        """Return capabilities mapped to an action."""
        return [
            capability
            for capability in self._capabilities.values()
            if capability.action_id == action_id
        ]

    def is_registered(self, capability_id: str) -> bool:
        """Return whether a capability is registered."""
        return capability_id in self._capabilities


_DEFAULT_CAPABILITIES = (
    Capability(
        "check_python_version",
        "Check Python version",
        "Read the active Python version and compare it with the project minimum.",
        "check_python_version_real",
        CapabilityRisk.LOW,
        [ExecutionMode.SAFE, ExecutionMode.REAL],
    ),
    Capability(
        "create_virtual_environment",
        "Create Python virtual environment",
        "Create the project's isolated .venv without executing arbitrary shell commands.",
        "create_virtualenv",
        CapabilityRisk.MEDIUM,
        [ExecutionMode.SAFE, ExecutionMode.REAL],
        True,
    ),
    Capability(
        "install_python_package",
        "Install Python package",
        "Install one explicitly identified Python package into the selected interpreter.",
        "install_python_package",
        CapabilityRisk.MEDIUM,
        [ExecutionMode.SAFE, ExecutionMode.REAL],
        True,
    ),
    Capability(
        "install_project_dependencies",
        "Install project dependencies",
        "Install dependencies declared by the project's pyproject.toml.",
        "install_project_dependencies",
        CapabilityRisk.MEDIUM,
        [ExecutionMode.SAFE, ExecutionMode.REAL],
        True,
    ),
    Capability(
        "install_git",
        "Install Git",
        "Install Git using a future approved platform-specific remediation handler.",
        "install_git",
        CapabilityRisk.MEDIUM,
        [ExecutionMode.SAFE],
        True,
    ),
    Capability(
        "install_docker",
        "Install Docker",
        "Install Docker using a future approved platform-specific remediation handler.",
        "install_docker",
        CapabilityRisk.MEDIUM,
        [ExecutionMode.SAFE],
        True,
    ),
    Capability(
        "fix_editable_install",
        "Install project in editable mode",
        "Install the current project in editable mode with development dependencies.",
        "fix_editable",
        CapabilityRisk.MEDIUM,
        [ExecutionMode.SAFE],
        True,
    ),
)


def default_capability_registry() -> CapabilityRegistry:
    """Build the canonical discovery registry for the bootstrap platform."""
    registry = CapabilityRegistry()
    for capability in _DEFAULT_CAPABILITIES:
        registry.register(capability)
    return registry


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CapabilityRisk",
    "DuplicateCapabilityError",
    "default_capability_registry",
]

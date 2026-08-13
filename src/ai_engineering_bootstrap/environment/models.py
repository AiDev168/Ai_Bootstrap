"""Environment request and state models for AI Engineering Bootstrap."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ToolRequirementLevel(str, Enum):
    """Requirement level for a tool."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    ABSENT = "absent"


@dataclass(frozen=True)
class ToolRequirement:
    """Specification for a single tool requirement."""

    tool_id: str
    level: ToolRequirementLevel = ToolRequirementLevel.REQUIRED
    version_constraint: str | None = None
    configuration: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PythonPackageRequirement:
    """Specification for a Python package requirement."""

    name: str
    version_constraint: str | None = None
    extras: list[str] = field(default_factory=list)


@dataclass
class EnvironmentRequest:
    """
    User request to prepare an engineering environment.

    This is the primary input model that captures what the user wants.
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str | None = None
    project_path: Path | None = None
    natural_language_goal: str = ""
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    project_dependencies: list[PythonPackageRequirement] = field(default_factory=list)
    configurations: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    platform_preferences: dict[str, Any] = field(default_factory=dict)
    user_preferences: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "project_path": str(self.project_path) if self.project_path else None,
            "natural_language_goal": self.natural_language_goal,
            "required_tools": self.required_tools,
            "optional_tools": self.optional_tools,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "project_dependencies": [
                {"name": p.name, "version_constraint": p.version_constraint, "extras": p.extras}
                for p in self.project_dependencies
            ],
            "configurations": self.configurations,
            "constraints": self.constraints,
            "platform_preferences": self.platform_preferences,
            "user_preferences": self.user_preferences,
        }

    def to_desired_state(self) -> DesiredEnvironmentState:
        """Convert this request into a structured desired state."""
        tools = {
            tool_id: ToolRequirement(tool_id=tool_id, level=ToolRequirementLevel.REQUIRED)
            for tool_id in self.required_tools
        }
        for tool_id in self.optional_tools:
            if tool_id not in tools:
                tools[tool_id] = ToolRequirement(tool_id=tool_id, level=ToolRequirementLevel.OPTIONAL)

        return DesiredEnvironmentState(
            tools=tools,
            python_packages=self.project_dependencies,
            configurations=self.configurations,
            project_requirements=self.project_dependencies,
            constraints=self.constraints,
        )


@dataclass(frozen=True)
class DesiredEnvironmentState:
    """
    Structured target state for an engineering environment.

    This represents what we want the environment to look like after completion.
    """

    tools: dict[str, ToolRequirement] = field(default_factory=dict)
    python_packages: list[PythonPackageRequirement] = field(default_factory=list)
    configurations: dict[str, Any] = field(default_factory=dict)
    project_requirements: list[PythonPackageRequirement] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolStatus:
    """Observed status of a single tool in the actual environment."""

    tool_id: str
    status: str  # "installed", "missing", "error"
    version: str | None = None
    location: str | None = None
    health: str = "unknown"  # "healthy", "degraded", "broken", "unknown"
    probe_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActualEnvironmentState:
    """
    Observed current state of the engineering environment.

    This comes from real audit/probe systems, not from LLM inference.
    """

    tools: dict[str, ToolStatus] = field(default_factory=dict)
    python_packages: dict[str, str] = field(default_factory=dict)  # name -> version
    system_info: dict[str, Any] = field(default_factory=dict)
    probe_timestamp: str = ""
    probe_evidence: dict[str, Any] = field(default_factory=dict)


class DeltaAction(str, Enum):
    """Action type for environment delta."""

    INSTALL = "install"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    CONFIGURE = "configure"
    REMOVE = "remove"
    NONE = "none"


@dataclass(frozen=True)
class ToolDelta:
    """Delta for a single tool between actual and desired state."""

    tool_id: str
    action: DeltaAction
    desired_requirement: ToolRequirement | None = None
    actual_status: ToolStatus | None = None
    reason: str = ""


@dataclass(frozen=True)
class PackageDelta:
    """Delta for a single Python package between actual and desired state."""

    package_name: str
    action: DeltaAction
    desired_version: str | None = None
    actual_version: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class EnvironmentDelta:
    """
    Computed difference between actual and desired environment states.

    This is calculated deterministically, not by LLM.
    """

    tool_deltas: list[ToolDelta] = field(default_factory=list)
    package_deltas: list[PackageDelta] = field(default_factory=list)
    configuration_deltas: dict[str, Any] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes required."""
        return (
            any(d.action != DeltaAction.NONE for d in self.tool_deltas)
            or any(d.action != DeltaAction.NONE for d in self.package_deltas)
            or bool(self.configuration_deltas)
        )

    @property
    def required_actions_count(self) -> int:
        """Count of required (non-optional) actions."""
        count = sum(
            1 for d in self.tool_deltas
            if d.action != DeltaAction.NONE
            and d.desired_requirement
            and d.desired_requirement.level == ToolRequirementLevel.REQUIRED
        )
        count += sum(1 for d in self.package_deltas if d.action != DeltaAction.NONE)
        count += len(self.configuration_deltas)
        return count

    @property
    def optional_actions_count(self) -> int:
        """Count of optional actions."""
        return sum(
            1 for d in self.tool_deltas
            if d.action != DeltaAction.NONE
            and d.desired_requirement
            and d.desired_requirement.level == ToolRequirementLevel.OPTIONAL
        )


__all__ = [
    "EnvironmentRequest",
    "DesiredEnvironmentState",
    "ActualEnvironmentState",
    "ToolRequirement",
    "ToolRequirementLevel",
    "ToolStatus",
    "PythonPackageRequirement",
    "EnvironmentDelta",
    "ToolDelta",
    "PackageDelta",
    "DeltaAction",
]

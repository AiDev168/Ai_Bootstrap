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
    """User request to prepare an engineering environment."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str | None = None
    project_path: Path | None = None
    natural_language_goal: str = ""
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    excluded_tools: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    project_dependencies: list[PythonPackageRequirement] = field(default_factory=list)
    excluded_packages: list[str] = field(default_factory=list)
    configurations: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    platform_preferences: dict[str, Any] = field(default_factory=dict)
    user_preferences: dict[str, Any] = field(default_factory=dict)

    def to_desired_state(self) -> DesiredEnvironmentState:
        """Convert this request into a structured desired state."""
        force_install = bool(self.constraints.get("force_install", False))
        excluded_tools = {tool.lower() for tool in self.excluded_tools}
        excluded_packages = {package.lower() for package in self.excluded_packages}
        tools = {
            tool_id: ToolRequirement(
                tool_id=tool_id,
                level=ToolRequirementLevel.REQUIRED,
                configuration={"force_install": force_install} if force_install else {},
            )
            for tool_id in self.required_tools
            if tool_id.lower() not in excluded_tools
        }
        for tool_id in self.optional_tools:
            if tool_id not in tools and tool_id.lower() not in excluded_tools:
                tools[tool_id] = ToolRequirement(
                    tool_id=tool_id,
                    level=ToolRequirementLevel.OPTIONAL,
                    configuration={"force_install": force_install} if force_install else {},
                )

        packages = [
            package
            for package in self.project_dependencies
            if package.name.lower() not in excluded_packages
        ]
        constraints = dict(self.constraints)
        if self.excluded_tools:
            constraints["excluded_tools"] = list(self.excluded_tools)
        if self.excluded_packages:
            constraints["excluded_packages"] = list(self.excluded_packages)

        return DesiredEnvironmentState(
            tools=tools,
            python_packages=packages,
            configurations=self.configurations,
            project_requirements=packages,
            constraints=constraints,
        )


@dataclass(frozen=True)
class DesiredEnvironmentState:
    """Structured target state for an engineering environment."""

    tools: dict[str, ToolRequirement] = field(default_factory=dict)
    python_packages: list[PythonPackageRequirement] = field(default_factory=list)
    configurations: dict[str, Any] = field(default_factory=dict)
    project_requirements: list[PythonPackageRequirement] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolStatus:
    """Observed status of a single tool in the actual environment."""

    tool_id: str
    status: str
    version: str | None = None
    location: str | None = None
    health: str = "unknown"
    probe_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActualEnvironmentState:
    """Observed current state of the engineering environment."""

    tools: dict[str, ToolStatus] = field(default_factory=dict)
    python_packages: dict[str, str] = field(default_factory=dict)
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
    """Computed difference between actual and desired environment states."""

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
        """Count of required non-optional actions."""
        count = sum(
            1
            for d in self.tool_deltas
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
            1
            for d in self.tool_deltas
            if d.action != DeltaAction.NONE
            and d.desired_requirement
            and d.desired_requirement.level == ToolRequirementLevel.OPTIONAL
        )


__all__ = [
    "ActualEnvironmentState",
    "DeltaAction",
    "DesiredEnvironmentState",
    "EnvironmentDelta",
    "PackageDelta",
    "PythonPackageRequirement",
    "ToolDelta",
    "ToolRequirement",
    "ToolRequirementLevel",
    "ToolStatus",
]

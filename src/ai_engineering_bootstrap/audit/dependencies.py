"""Project dependency discovery and read-only availability checks."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from ai_engineering_bootstrap.audit.models import AuditCheck, AuditStatus

_DEPENDENCY_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*")


@dataclass(frozen=True)
class DependencyRequirement:
    """A normalized Python dependency requirement."""

    name: str
    requirement: str
    source: str


class DependencyDiscovery:
    """Discover Python dependencies from a project's pyproject.toml."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def discover(self, include_dev: bool = True) -> list[DependencyRequirement]:
        """Return deterministic runtime and optional development dependencies."""
        pyproject = self.project_root / "pyproject.toml"
        if not pyproject.is_file():
            return []

        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)

        requirements: list[DependencyRequirement] = []
        project = data.get("project", {})
        requirements.extend(
            self._normalize(project.get("dependencies", []), "project")
        )

        if include_dev:
            optional = project.get("optional-dependencies", {})
            for group_name in sorted(optional):
                requirements.extend(
                    self._normalize(optional[group_name], f"optional:{group_name}")
                )

        unique: dict[str, DependencyRequirement] = {}
        for requirement in requirements:
            unique.setdefault(requirement.name.lower(), requirement)
        return sorted(unique.values(), key=lambda item: item.name.lower())

    @staticmethod
    def _normalize(
        requirements: list[str], source: str
    ) -> list[DependencyRequirement]:
        normalized: list[DependencyRequirement] = []
        for requirement in requirements:
            match = _DEPENDENCY_NAME.match(requirement.strip())
            if match:
                normalized.append(
                    DependencyRequirement(
                        name=match.group(0),
                        requirement=requirement.strip(),
                        source=source,
                    )
                )
        return normalized


class ProjectDependencyProbe:
    """Read-only probe for one discovered Python dependency."""

    def __init__(self, requirement: DependencyRequirement) -> None:
        self.requirement = requirement

    def run(self) -> AuditCheck:
        """Check whether the required distribution is installed."""
        try:
            installed = metadata.version(self.requirement.name)
        except metadata.PackageNotFoundError:
            return AuditCheck(
                name=self.requirement.name,
                status=AuditStatus.NOT_FOUND,
                facts={
                    "package": self.requirement.name,
                    "requirement": self.requirement.requirement,
                    "source": self.requirement.source,
                    "installed_version": None,
                    "remediation_action": "install_python_package",
                    "remediation_description": f"Install Python dependency: {self.requirement.requirement}",
                    "remediation_priority": 50,
                },
                details=f"Package '{self.requirement.requirement}' is not installed.",
            )

        return AuditCheck(
            name=self.requirement.name,
            status=AuditStatus.AVAILABLE,
            facts={
                "package": self.requirement.name,
                "requirement": self.requirement.requirement,
                "source": self.requirement.source,
                "installed_version": installed,
            },
            details=installed,
        )

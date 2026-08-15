"""Tests for project dependency discovery and planning metadata."""

from pathlib import Path

from ai_engineering_bootstrap.audit.dependencies import (
    DependencyDiscovery,
    ProjectDependencyProbe,
)
from ai_engineering_bootstrap.audit.models import AuditStatus


def test_dependency_discovery_reads_project_and_dev_dependencies(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = ["rich>=13", "typer"]
[project.optional-dependencies]
dev = ["pytest", "ruff"]
"""
    )
    requirements = DependencyDiscovery(tmp_path).discover()
    assert [item.name for item in requirements] == ["pytest", "rich", "ruff", "typer"]


def test_dependency_discovery_deduplicates_case_insensitively(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = ["Rich>=13"]
[project.optional-dependencies]
dev = ["rich"]
"""
    )
    requirements = DependencyDiscovery(tmp_path).discover()
    assert len(requirements) == 1


def test_dependency_probe_missing_package_contains_remediation() -> None:
    from importlib import metadata
    from unittest.mock import patch

    from ai_engineering_bootstrap.audit.dependencies import DependencyRequirement

    requirement = DependencyRequirement("missing-demo", "missing-demo>=1", "project")
    with patch.object(metadata, "version", side_effect=metadata.PackageNotFoundError):
        result = ProjectDependencyProbe(requirement).run()

    assert result.status == AuditStatus.NOT_FOUND
    assert result.facts["remediation_action"] == "install_python_package"
    assert result.facts["requirement"] == "missing-demo>=1"

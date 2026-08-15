"""Read-only engineering-environment bootstrap verification."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolStatus:
    """Observed state of one engineering tool."""

    name: str
    required: bool
    available: bool
    path: str | None = None


@dataclass(frozen=True)
class EngineeringEnvironmentReport:
    """Deterministic report for engineering tooling and Cursor integration."""

    tools: tuple[ToolStatus, ...]
    cursor_rules_present: bool
    cursor_available: bool
    project_root: Path

    @property
    def required_tools_ready(self) -> bool:
        """Return true when every required tool is available."""
        return all(tool.available for tool in self.tools if tool.required)

    @property
    def is_ready(self) -> bool:
        """Return true when required tools and Cursor rules are ready."""
        return self.required_tools_ready and self.cursor_rules_present


class EngineeringEnvironmentService:
    """Inspect the engineering environment without modifying the host."""

    REQUIRED_TOOLS = ("git", "pytest", "ruff", "cursor")
    OPTIONAL_TOOLS = ("docker",)

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()

    def run(self) -> EngineeringEnvironmentReport:
        """Return deterministic tool and Cursor integration status."""
        tools: list[ToolStatus] = []
        for name in self.REQUIRED_TOOLS:
            path = self._tool_path(name)
            tools.append(ToolStatus(name, True, path is not None, path))
        for name in self.OPTIONAL_TOOLS:
            path = self._tool_path(name)
            tools.append(ToolStatus(name, False, path is not None, path))

        rules_path = self.project_root / ".cursor" / "rules"
        cursor_rules_present = (rules_path / "project.mdc").is_file()
        cursor_path = self._tool_path("cursor")

        return EngineeringEnvironmentReport(
            tools=tuple(tools),
            cursor_rules_present=cursor_rules_present,
            cursor_available=cursor_path is not None,
            project_root=self.project_root,
        )

    @staticmethod
    def _tool_path(name: str) -> str | None:
        if name == "pytest":
            return shutil.which(
                "pytest"
            ) or EngineeringEnvironmentService._python_module_path("pytest")
        if name == "ruff":
            return shutil.which(
                "ruff"
            ) or EngineeringEnvironmentService._python_module_path("ruff")
        if name == "git":
            return shutil.which("git")
        if name == "docker":
            return shutil.which("docker")
        if name == "cursor":
            return shutil.which("cursor")
        return shutil.which(name)

    @staticmethod
    def _python_module_path(module_name: str) -> str | None:
        try:
            __import__(module_name)
        except ImportError:
            return None
        return f"{sys.executable} -m {module_name}"


__all__ = [
    "EngineeringEnvironmentReport",
    "EngineeringEnvironmentService",
    "ToolStatus",
]

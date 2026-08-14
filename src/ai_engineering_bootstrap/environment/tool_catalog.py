"""Tool Catalog for AI Engineering Bootstrap.

This module defines the ToolDefinition model and provides a catalog of available tools
with their installation strategies, detection probes, and verification methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Platform(str, Enum):
    """Supported platforms."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"


class Architecture(str, Enum):
    """Supported architectures."""

    X86_64 = "x86_64"
    ARM64 = "arm64"
    AARCH64 = "aarch64"


class ArtifactFormat(str, Enum):
    """Package artifact formats."""

    DEB = "deb"
    RPM = "rpm"
    TARBALL = "tarball"
    BINARY = "binary"
    PIP = "pip"
    APPIMAGE = "appimage"
    DMG = "dmg"
    EXE = "exe"


class PrivilegeLevel(str, Enum):
    """Privilege level required for installation."""

    USER = "user"
    SYSTEM = "system"
    ROOT = "root"


class RiskLevel(str, Enum):
    """Risk classification for tool installation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class InstallationStrategy:
    """Describes how to install a tool on a specific platform."""

    strategy_id: str
    platform: Platform
    architecture: list[Architecture]
    artifact_format: ArtifactFormat | None = None
    source_url: str | None = None
    package_name: str | None = None
    commands: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    post_install_steps: list[str] = field(default_factory=list)
    privilege_level: PrivilegeLevel = PrivilegeLevel.USER
    interactive: bool = False


@dataclass(frozen=True)
class ProbeDefinition:
    """Definition for detecting or verifying a tool."""

    probe_id: str
    command: list[str]
    expected_exit_code: int = 0
    timeout_seconds: float = 5.0
    parse_version: bool = True
    version_line_index: int = 0


@dataclass(frozen=True)
class ToolDefinition:
    """
    Complete definition of an engineering tool.

    This includes detection, installation strategies, configuration, and verification.
    """

    tool_id: str
    display_name: str
    description: str
    platforms: list[Platform]
    architectures: list[Architecture]
    detect_probe: ProbeDefinition | None = None
    version_probe: ProbeDefinition | None = None
    installation_strategies: list[InstallationStrategy] = field(default_factory=list)
    configuration_strategies: list[dict[str, Any]] = field(default_factory=list)
    verification_strategies: list[ProbeDefinition] = field(default_factory=list)
    privilege_level: PrivilegeLevel = PrivilegeLevel.USER
    risk_level: RiskLevel = RiskLevel.LOW
    official_sources: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    artifact_formats: list[ArtifactFormat] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Tool Definitions
# =============================================================================


def _python_tool() -> ToolDefinition:
    """Define Python tool."""
    return ToolDefinition(
        tool_id="python",
        display_name="Python",
        description="Python programming language interpreter",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="python_detect",
            command=["python3", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="python_version",
            command=["python3", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="python_apt",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.DEB,
                package_name="python3",
                commands=[
                    "sudo apt-get update",
                    "sudo apt-get install -y python3 python3-pip python3-venv",
                ],
                privilege_level=PrivilegeLevel.ROOT,
                interactive=True,
            ),
        ],
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://www.python.org/"],
        allowed_domains=["python.org", "packages.python.org"],
        artifact_formats=[
            ArtifactFormat.DEB,
            ArtifactFormat.RPM,
            ArtifactFormat.TARBALL,
        ],
    )


def _git_tool() -> ToolDefinition:
    """Define Git tool."""
    return ToolDefinition(
        tool_id="git",
        display_name="Git",
        description="Distributed version control system",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="git_detect",
            command=["git", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="git_version",
            command=["git", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="git_apt",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.DEB,
                package_name="git",
                commands=["sudo apt-get install -y git"],
                privilege_level=PrivilegeLevel.ROOT,
                interactive=True,
            ),
        ],
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://git-scm.com/"],
        allowed_domains=["git-scm.com"],
        artifact_formats=[
            ArtifactFormat.DEB,
            ArtifactFormat.RPM,
            ArtifactFormat.TARBALL,
        ],
    )


def _cursor_tool() -> ToolDefinition:
    """Define Cursor tool."""
    return ToolDefinition(
        tool_id="cursor",
        display_name="Cursor",
        description="AI-powered code editor",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64],
        detect_probe=ProbeDefinition(
            probe_id="cursor_detect",
            command=["cursor", "--version"],
            timeout_seconds=10.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="cursor_version",
            command=["cursor", "--version"],
            timeout_seconds=10.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="cursor_deb_linux",
                platform=Platform.LINUX,
                architecture=[Architecture.X86_64],
                artifact_format=ArtifactFormat.DEB,
                source_url="https://www.cursor.com/api/download?platform=linux-x64&releaseTrack=stable",
                commands=["sudo apt-get install -y {artifact_path}"],
                privilege_level=PrivilegeLevel.ROOT,
                interactive=True,
            ),
            InstallationStrategy(
                strategy_id="cursor_arm64_linux",
                platform=Platform.LINUX,
                architecture=[Architecture.ARM64, Architecture.AARCH64],
                artifact_format=ArtifactFormat.DEB,
                source_url="https://www.cursor.com/api/download?platform=linux-arm64&releaseTrack=stable",
                commands=["sudo apt-get install -y {artifact_path}"],
                privilege_level=PrivilegeLevel.ROOT,
                interactive=True,
            ),
        ],
        privilege_level=PrivilegeLevel.SYSTEM,
        risk_level=RiskLevel.MEDIUM,
        official_sources=["https://www.cursor.com/"],
        allowed_domains=["cursor.com", "downloads.cursor.com", "www.cursor.com"],
        artifact_formats=[ArtifactFormat.DEB, ArtifactFormat.DMG, ArtifactFormat.EXE],
        metadata={
            "api_endpoint": "https://www.cursor.com/api/download",
            "release_track": "stable",
        },
    )


def _docker_tool() -> ToolDefinition:
    """Define Docker tool."""
    return ToolDefinition(
        tool_id="docker",
        display_name="Docker",
        description="Container runtime and orchestration platform",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="docker_detect",
            command=["docker", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="docker_version",
            command=["docker", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="docker_apt",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.DEB,
                package_name="docker.io",
                commands=[
                    "sudo apt-get update",
                    "sudo apt-get install -y docker.io",
                    "sudo systemctl enable --now docker",
                ],
                privilege_level=PrivilegeLevel.ROOT,
                interactive=True,
            ),
        ],
        privilege_level=PrivilegeLevel.ROOT,
        risk_level=RiskLevel.HIGH,
        official_sources=["https://docs.docker.com/"],
        allowed_domains=["docker.com", "docker.io"],
        artifact_formats=[
            ArtifactFormat.DEB,
            ArtifactFormat.RPM,
            ArtifactFormat.TARBALL,
        ],
        dependencies=["containerd", "runc"],
    )


def _ruff_tool() -> ToolDefinition:
    """Define Ruff tool."""
    return ToolDefinition(
        tool_id="ruff",
        display_name="Ruff",
        description="Fast Python linter and formatter",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="ruff_detect",
            command=["ruff", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="ruff_version",
            command=["ruff", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="ruff_pip",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.PIP,
                package_name="ruff",
                commands=["pip install ruff"],
                privilege_level=PrivilegeLevel.USER,
                interactive=False,
            ),
        ],
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://docs.astral.sh/ruff/"],
        allowed_domains=["pypi.org", "astral.sh"],
        artifact_formats=[ArtifactFormat.PIP, ArtifactFormat.BINARY],
    )


def _pytest_tool() -> ToolDefinition:
    """Define Pytest tool."""
    return ToolDefinition(
        tool_id="pytest",
        display_name="Pytest",
        description="Python testing framework",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="pytest_detect",
            command=["pytest", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="pytest_version",
            command=["pytest", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="pytest_pip",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.PIP,
                package_name="pytest",
                commands=["pip install pytest"],
                privilege_level=PrivilegeLevel.USER,
                interactive=False,
            ),
        ],
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://docs.pytest.org/"],
        allowed_domains=["pypi.org", "pytest.org"],
        artifact_formats=[ArtifactFormat.PIP],
    )


def _black_tool() -> ToolDefinition:
    """Define Black tool."""
    return ToolDefinition(
        tool_id="black",
        display_name="Black",
        description="Python code formatter",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="black_detect",
            command=["black", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="black_version",
            command=["black", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="black_pip",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.PIP,
                package_name="black",
                commands=["pip install black"],
                privilege_level=PrivilegeLevel.USER,
                interactive=False,
            ),
        ],
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://black.readthedocs.io/"],
        allowed_domains=["pypi.org", "readthedocs.io"],
        artifact_formats=[ArtifactFormat.PIP],
    )


def _github_cli_tool() -> ToolDefinition:
    """Define GitHub CLI tool."""
    return ToolDefinition(
        tool_id="gh",
        display_name="GitHub CLI",
        description="GitHub command-line interface",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="gh_detect",
            command=["gh", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="gh_version",
            command=["gh", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="gh_apt",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.DEB,
                commands=[
                    "type -p curl >/dev/null || (sudo apt update && sudo apt-get install curl -y)",
                    "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg",
                    "sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg",
                    'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null',
                    "sudo apt update",
                    "sudo apt install gh -y",
                ],
                privilege_level=PrivilegeLevel.ROOT,
                interactive=True,
            ),
        ],
        privilege_level=PrivilegeLevel.SYSTEM,
        risk_level=RiskLevel.MEDIUM,
        official_sources=["https://cli.github.com/"],
        allowed_domains=["github.com", "cli.github.com"],
        artifact_formats=[
            ArtifactFormat.DEB,
            ArtifactFormat.RPM,
            ArtifactFormat.TARBALL,
        ],
    )


def _nodejs_tool() -> ToolDefinition:
    """Define Node.js tool."""
    return ToolDefinition(
        tool_id="nodejs",
        display_name="Node.js",
        description="JavaScript runtime environment",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="nodejs_detect",
            command=["node", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="nodejs_version",
            command=["node", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="nodejs_apt",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.DEB,
                commands=[
                    "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -",
                    "sudo apt-get install -y nodejs",
                ],
                privilege_level=PrivilegeLevel.ROOT,
                interactive=True,
            ),
        ],
        privilege_level=PrivilegeLevel.SYSTEM,
        risk_level=RiskLevel.MEDIUM,
        official_sources=["https://nodejs.org/"],
        allowed_domains=["nodejs.org", "nodesource.com"],
        artifact_formats=[
            ArtifactFormat.DEB,
            ArtifactFormat.RPM,
            ArtifactFormat.TARBALL,
        ],
    )


def _npm_tool() -> ToolDefinition:
    """Define npm tool."""
    return ToolDefinition(
        tool_id="npm",
        display_name="npm",
        description="Node.js package manager",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="npm_detect",
            command=["npm", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="npm_version",
            command=["npm", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[],  # Comes with Node.js
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://www.npmjs.com/"],
        allowed_domains=["npmjs.com"],
        artifact_formats=[],
        dependencies=["nodejs"],
    )


def _uv_tool() -> ToolDefinition:
    """Define uv tool."""
    return ToolDefinition(
        tool_id="uv",
        display_name="uv",
        description="Fast Python package installer and resolver",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="uv_detect",
            command=["uv", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="uv_version",
            command=["uv", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="uv_pip",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.PIP,
                package_name="uv",
                commands=["pip install uv"],
                privilege_level=PrivilegeLevel.USER,
                interactive=False,
            ),
        ],
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://docs.astral.sh/uv/"],
        allowed_domains=["astral.sh", "pypi.org"],
        artifact_formats=[ArtifactFormat.PIP, ArtifactFormat.BINARY],
    )


def _poetry_tool() -> ToolDefinition:
    """Define Poetry tool."""
    return ToolDefinition(
        tool_id="poetry",
        display_name="Poetry",
        description="Python dependency management and packaging",
        platforms=[Platform.LINUX, Platform.MACOS, Platform.WINDOWS],
        architectures=[Architecture.X86_64, Architecture.ARM64, Architecture.AARCH64],
        detect_probe=ProbeDefinition(
            probe_id="poetry_detect",
            command=["poetry", "--version"],
            timeout_seconds=5.0,
        ),
        version_probe=ProbeDefinition(
            probe_id="poetry_version",
            command=["poetry", "--version"],
            timeout_seconds=5.0,
            parse_version=True,
        ),
        installation_strategies=[
            InstallationStrategy(
                strategy_id="poetry_pip",
                platform=Platform.LINUX,
                architecture=[
                    Architecture.X86_64,
                    Architecture.ARM64,
                    Architecture.AARCH64,
                ],
                artifact_format=ArtifactFormat.PIP,
                package_name="poetry",
                commands=["pip install poetry"],
                privilege_level=PrivilegeLevel.USER,
                interactive=False,
            ),
        ],
        privilege_level=PrivilegeLevel.USER,
        risk_level=RiskLevel.LOW,
        official_sources=["https://python-poetry.org/"],
        allowed_domains=["python-poetry.org", "pypi.org"],
        artifact_formats=[ArtifactFormat.PIP],
    )


# =============================================================================
# Tool Catalog Registry
# =============================================================================


class ToolCatalog:
    """Registry of all available tools with their definitions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        tools = [
            _python_tool(),
            _git_tool(),
            _cursor_tool(),
            _docker_tool(),
            _ruff_tool(),
            _pytest_tool(),
            _black_tool(),
            _github_cli_tool(),
            _nodejs_tool(),
            _npm_tool(),
            _uv_tool(),
            _poetry_tool(),
        ]
        for tool in tools:
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        if not tool.tool_id:
            raise ValueError("tool_id cannot be empty")
        if tool.tool_id in self._tools:
            raise DuplicateToolError(f"Tool '{tool.tool_id}' is already registered")
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> ToolDefinition | None:
        """Get a tool definition by ID."""
        return self._tools.get(tool_id)

    def list_tools(self) -> list[ToolDefinition]:
        """Return all registered tools in deterministic order."""
        return sorted(self._tools.values(), key=lambda t: t.tool_id)

    def is_registered(self, tool_id: str) -> bool:
        """Check if a tool is registered."""
        return tool_id in self._tools

    def find_by_platform(
        self, platform: Platform, architecture: Architecture | None = None
    ) -> list[ToolDefinition]:
        """Find all tools that support a specific platform/architecture."""
        result = []
        for tool in self._tools.values():
            if platform not in tool.platforms:
                continue
            if architecture and architecture not in tool.architectures:
                continue
            result.append(tool)
        return result

    def get_installation_strategy(
        self,
        tool_id: str,
        platform: Platform,
        architecture: Architecture | None = None,
    ) -> InstallationStrategy | None:
        """Get the best installation strategy for a tool on a platform."""
        tool = self.get(tool_id)
        if not tool:
            return None

        for strategy in tool.installation_strategies:
            if strategy.platform != platform:
                continue
            if architecture and architecture not in strategy.architecture:
                continue
            return strategy

        return None


class DuplicateToolError(ValueError):
    """Raised when attempting to register a duplicate tool."""


# =============================================================================
# Singleton Instance
# =============================================================================


_default_catalog: ToolCatalog | None = None


def get_tool_catalog() -> ToolCatalog:
    """Get the default tool catalog instance."""
    global _default_catalog
    if _default_catalog is None:
        _default_catalog = ToolCatalog()
    return _default_catalog


__all__ = [
    "Architecture",
    "ArtifactFormat",
    "DuplicateToolError",
    "InstallationStrategy",
    "Platform",
    "PrivilegeLevel",
    "ProbeDefinition",
    "RiskLevel",
    "ToolCatalog",
    "ToolDefinition",
    "get_tool_catalog",
]

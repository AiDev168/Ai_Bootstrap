"""Installation Strategies for AI Engineering Bootstrap.

This module provides controlled installation strategies with a deterministic lifecycle:
- discover_artifact
- validate_artifact
- install
- verify

The LLM may select a registered strategy but must not invent arbitrary installation commands.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ai_engineering_bootstrap.environment.tool_catalog import (
    Architecture,
    ArtifactFormat,
    InstallationStrategy,
    Platform,
    ToolDefinition,
)


class StrategyStatus(str, Enum):
    """Status of an installation strategy execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ArtifactMetadata:
    """Metadata about a discovered artifact."""

    source_url: str
    source_domain: str
    platform: Platform
    architecture: Architecture
    format: ArtifactFormat
    version: str | None = None
    checksum: str | None = None
    checksum_algorithm: str | None = None
    trust_level: str = "unknown"  # "official", "verified", "unknown"
    size_bytes: int | None = None


@dataclass
class InstallationResult:
    """Result of an installation operation."""

    strategy_id: str
    tool_id: str
    status: StrategyStatus
    message: str
    artifact_metadata: ArtifactMetadata | None = None
    version_installed: str | None = None
    error_details: dict[str, Any] | None = None
    verification_passed: bool = False


class InstallationStrategyError(Exception):
    """Base exception for installation strategy errors."""


class ArtifactDiscoveryError(InstallationStrategyError):
    """Raised when artifact discovery fails."""


class ArtifactValidationError(InstallationStrategyError):
    """Raised when artifact validation fails."""


class InstallationError(InstallationStrategyError):
    """Raised when installation fails."""


class VerificationError(InstallationStrategyError):
    """Raised when verification fails."""


class InstallationStrategyBase(ABC):
    """Abstract base class for installation strategies."""

    def __init__(
        self, strategy: InstallationStrategy, tool_definition: ToolDefinition
    ) -> None:
        self._strategy = strategy
        self._tool_definition = tool_definition

    @abstractmethod
    def discover_artifact(self) -> ArtifactMetadata:
        """Discover the artifact to install."""

    @abstractmethod
    def validate_artifact(self, metadata: ArtifactMetadata) -> bool:
        """Validate the artifact before installation."""

    @abstractmethod
    def install(
        self, metadata: ArtifactMetadata, dry_run: bool = False
    ) -> InstallationResult:
        """Install the artifact."""

    @abstractmethod
    def verify(self) -> bool:
        """Verify the installation was successful."""


class DebInstallStrategy(InstallationStrategyBase):
    """Installation strategy for Debian packages."""

    def discover_artifact(self) -> ArtifactMetadata:
        """Discover DEB artifact from official source."""
        source_url = self._strategy.source_url
        if not source_url:
            raise ArtifactDiscoveryError(
                f"No source URL provided for {self._tool_definition.tool_id}"
            )

        # Parse domain from URL
        from urllib.parse import urlparse

        parsed = urlparse(source_url)
        source_domain = parsed.netloc

        # Validate against allowed domains
        if source_domain not in self._tool_definition.allowed_domains:
            raise ArtifactDiscoveryError(
                f"Source domain {source_domain} not in allowed domains: {self._tool_definition.allowed_domains}"
            )

        return ArtifactMetadata(
            source_url=source_url,
            source_domain=source_domain,
            platform=self._strategy.platform,
            architecture=self._strategy.architecture[0]
            if self._strategy.architecture
            else Architecture.X86_64,
            format=ArtifactFormat.DEB,
            trust_level="official"
            if source_domain in self._tool_definition.allowed_domains
            else "unknown",
        )

    def validate_artifact(self, metadata: ArtifactMetadata) -> bool:
        """Validate DEB artifact metadata."""
        if metadata.format != ArtifactFormat.DEB:
            raise ArtifactValidationError(f"Expected DEB format, got {metadata.format}")

        if metadata.trust_level not in ("official", "verified"):
            raise ArtifactValidationError(
                f"Artifact trust level too low: {metadata.trust_level}"
            )

        return True

    def install(
        self, metadata: ArtifactMetadata, dry_run: bool = False
    ) -> InstallationResult:
        """Install DEB package."""
        if dry_run:
            return InstallationResult(
                strategy_id=self._strategy.strategy_id,
                tool_id=self._tool_definition.tool_id,
                status=StrategyStatus.SKIPPED,
                message=f"Dry run: Would install {self._tool_definition.tool_id} from {metadata.source_url}",
                artifact_metadata=metadata,
            )

        try:
            # Download artifact to temp location
            with tempfile.TemporaryDirectory(prefix="bootstrap-deb-") as temp_dir:
                deb_path = Path(temp_dir) / f"{self._tool_definition.tool_id}.deb"

                # Download with validation
                request = urllib.request.Request(
                    metadata.source_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                        "Accept": "application/octet-stream,*/*",
                    },
                )

                with (
                    urllib.request.urlopen(request, timeout=300) as response,
                    open(deb_path, "wb") as f,
                ):
                    while chunk := response.read(1024 * 1024):
                        f.write(chunk)

                if not deb_path.exists() or deb_path.stat().st_size == 0:
                    raise InstallationError("Downloaded artifact is empty or missing")

                # Install using apt
                result = subprocess.run(
                    ["sudo", "apt-get", "install", "-y", str(deb_path)],
                    capture_output=True,
                    text=True,
                    timeout=900,
                    check=False,
                )

                if result.returncode != 0:
                    output = (result.stderr or result.stdout or "").strip()[-3000:]
                    raise InstallationError(f"Installation failed: {output}")

                # Verify installation
                verified = self.verify()

                return InstallationResult(
                    strategy_id=self._strategy.strategy_id,
                    tool_id=self._tool_definition.tool_id,
                    status=StrategyStatus.SUCCESS,
                    message=f"{self._tool_definition.display_name} installed successfully",
                    artifact_metadata=metadata,
                    version_installed=self._get_version(),
                    verification_passed=verified,
                )

        except (OSError, subprocess.SubprocessError, urllib.error.URLError) as e:
            return InstallationResult(
                strategy_id=self._strategy.strategy_id,
                tool_id=self._tool_definition.tool_id,
                status=StrategyStatus.FAILED,
                message=f"Installation failed: {e}",
                artifact_metadata=metadata,
                error_details={"error": str(e)},
            )

    def verify(self) -> bool:
        """Verify DEB installation."""
        if not self._tool_definition.version_probe:
            return True  # No verification probe defined

        try:
            result = subprocess.run(
                self._tool_definition.version_probe.command,
                capture_output=True,
                text=True,
                timeout=self._tool_definition.version_probe.timeout_seconds,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _get_version(self) -> str | None:
        """Get installed version."""
        if not self._tool_definition.version_probe:
            return None

        try:
            result = subprocess.run(
                self._tool_definition.version_probe.command,
                capture_output=True,
                text=True,
                timeout=self._tool_definition.version_probe.timeout_seconds,
                check=False,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip().splitlines()[0]
        except (OSError, subprocess.SubprocessError):
            pass
        return None


class PipInstallStrategy(InstallationStrategyBase):
    """Installation strategy for Python pip packages."""

    def discover_artifact(self) -> ArtifactMetadata:
        """Discover pip package artifact."""
        package_name = self._strategy.package_name or self._tool_definition.tool_id

        return ArtifactMetadata(
            source_url=f"https://pypi.org/project/{package_name}/",
            source_domain="pypi.org",
            platform=self._strategy.platform,
            architecture=self._strategy.architecture[0]
            if self._strategy.architecture
            else Architecture.X86_64,
            format=ArtifactFormat.PIP,
            trust_level="official",
        )

    def validate_artifact(self, metadata: ArtifactMetadata) -> bool:
        """Validate pip package metadata."""
        if metadata.format != ArtifactFormat.PIP:
            raise ArtifactValidationError(f"Expected PIP format, got {metadata.format}")

        if metadata.source_domain != "pypi.org":
            raise ArtifactValidationError(
                f"Expected pypi.org, got {metadata.source_domain}"
            )

        return True

    def install(
        self, metadata: ArtifactMetadata, dry_run: bool = False
    ) -> InstallationResult:
        """Install Python package via pip."""
        if dry_run:
            return InstallationResult(
                strategy_id=self._strategy.strategy_id,
                tool_id=self._tool_definition.tool_id,
                status=StrategyStatus.SKIPPED,
                message=f"Dry run: Would install {self._tool_definition.tool_id} via pip",
                artifact_metadata=metadata,
            )

        package_name = self._strategy.package_name or self._tool_definition.tool_id

        try:
            result = subprocess.run(
                [shutil.which("pip") or "pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            if result.returncode != 0:
                output = (result.stderr or result.stdout or "").strip()[-2000:]
                raise InstallationError(f"pip install failed: {output}")

            verified = self.verify()

            return InstallationResult(
                strategy_id=self._strategy.strategy_id,
                tool_id=self._tool_definition.tool_id,
                status=StrategyStatus.SUCCESS,
                message=f"{self._tool_definition.display_name} installed successfully",
                artifact_metadata=metadata,
                version_installed=self._get_version(),
                verification_passed=verified,
            )

        except (OSError, subprocess.SubprocessError) as e:
            return InstallationResult(
                strategy_id=self._strategy.strategy_id,
                tool_id=self._tool_definition.tool_id,
                status=StrategyStatus.FAILED,
                message=f"Installation failed: {e}",
                artifact_metadata=metadata,
                error_details={"error": str(e)},
            )

    def verify(self) -> bool:
        """Verify pip installation."""
        if not self._tool_definition.version_probe:
            # Try importing the package
            package_name = self._strategy.package_name or self._tool_definition.tool_id
            try:
                result = subprocess.run(
                    ["python3", "-c", f"import {package_name.replace('-', '_')}"],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                    check=False,
                )
                return result.returncode == 0
            except (OSError, subprocess.SubprocessError):
                return False

        try:
            result = subprocess.run(
                self._tool_definition.version_probe.command,
                capture_output=True,
                text=True,
                timeout=self._tool_definition.version_probe.timeout_seconds,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _get_version(self) -> str | None:
        """Get installed version."""
        package_name = self._strategy.package_name or self._tool_definition.tool_id

        try:
            result = subprocess.run(
                [shutil.which("pip") or "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=10.0,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return None


class BinaryInstallStrategy(InstallationStrategyBase):
    """Installation strategy for binary artifacts."""

    def discover_artifact(self) -> ArtifactMetadata:
        """Discover binary artifact."""
        source_url = self._strategy.source_url
        if not source_url:
            raise ArtifactDiscoveryError(
                f"No source URL provided for {self._tool_definition.tool_id}"
            )

        from urllib.parse import urlparse

        parsed = urlparse(source_url)
        source_domain = parsed.netloc

        return ArtifactMetadata(
            source_url=source_url,
            source_domain=source_domain,
            platform=self._strategy.platform,
            architecture=self._strategy.architecture[0]
            if self._strategy.architecture
            else Architecture.X86_64,
            format=ArtifactFormat.BINARY,
            trust_level="official"
            if source_domain in self._tool_definition.allowed_domains
            else "unknown",
        )

    def validate_artifact(self, metadata: ArtifactMetadata) -> bool:
        """Validate binary artifact metadata."""
        if metadata.format != ArtifactFormat.BINARY:
            raise ArtifactValidationError(
                f"Expected BINARY format, got {metadata.format}"
            )

        if metadata.trust_level not in ("official", "verified"):
            raise ArtifactValidationError(
                f"Artifact trust level too low: {metadata.trust_level}"
            )

        return True

    def install(
        self, metadata: ArtifactMetadata, dry_run: bool = False
    ) -> InstallationResult:
        """Install binary artifact."""
        if dry_run:
            return InstallationResult(
                strategy_id=self._strategy.strategy_id,
                tool_id=self._tool_definition.tool_id,
                status=StrategyStatus.SKIPPED,
                message=f"Dry run: Would install binary for {self._tool_definition.tool_id}",
                artifact_metadata=metadata,
            )

        # This is a simplified implementation - real binary installs vary widely
        return InstallationResult(
            strategy_id=self._strategy.strategy_id,
            tool_id=self._tool_definition.tool_id,
            status=StrategyStatus.FAILED,
            message="Binary installation requires tool-specific implementation",
            artifact_metadata=metadata,
            error_details={"reason": "not_implemented"},
        )

    def verify(self) -> bool:
        """Verify binary installation."""
        if not self._tool_definition.version_probe:
            return False

        try:
            result = subprocess.run(
                self._tool_definition.version_probe.command,
                capture_output=True,
                text=True,
                timeout=self._tool_definition.version_probe.timeout_seconds,
                check=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False


class StrategyFactory:
    """Factory for creating installation strategy instances."""

    @staticmethod
    def create_strategy(
        strategy: InstallationStrategy,
        tool_definition: ToolDefinition,
    ) -> InstallationStrategyBase:
        """Create appropriate strategy instance based on artifact format."""
        if strategy.artifact_format == ArtifactFormat.DEB:
            return DebInstallStrategy(strategy, tool_definition)
        elif strategy.artifact_format == ArtifactFormat.PIP:
            return PipInstallStrategy(strategy, tool_definition)
        elif strategy.artifact_format in (
            ArtifactFormat.BINARY,
            ArtifactFormat.TARBALL,
        ):
            return BinaryInstallStrategy(strategy, tool_definition)
        else:
            raise InstallationStrategyError(
                f"No strategy implementation for artifact format: {strategy.artifact_format}"
            )


def get_current_platform() -> tuple[Platform, Architecture]:
    """Detect current platform and architecture."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    platform_map = {
        "linux": Platform.LINUX,
        "darwin": Platform.MACOS,
        "windows": Platform.WINDOWS,
    }

    arch_map = {
        "x86_64": Architecture.X86_64,
        "amd64": Architecture.X86_64,
        "arm64": Architecture.ARM64,
        "aarch64": Architecture.AARCH64,
    }

    return (
        platform_map.get(system, Platform.LINUX),
        arch_map.get(machine, Architecture.X86_64),
    )


__all__ = [
    "ArtifactDiscoveryError",
    "ArtifactMetadata",
    "ArtifactValidationError",
    "BinaryInstallStrategy",
    "DebInstallStrategy",
    "InstallationError",
    "InstallationResult",
    "InstallationStrategyBase",
    "InstallationStrategyError",
    "PipInstallStrategy",
    "StrategyFactory",
    "StrategyStatus",
    "VerificationError",
    "get_current_platform",
]

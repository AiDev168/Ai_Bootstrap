"""Probes for environment doctor checks."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Protocol

from ai_engineering_bootstrap.audit.models import AuditCheck, AuditStatus


@dataclass
class DoctorResult:
    """Container for all doctor probe results."""

    checks: dict[str, dict[str, Any]] = field(default_factory=dict)


class Probe(Protocol):
    """Protocol for environment probes."""

    def run(self) -> AuditCheck:
        """Run the probe and return a check result."""
        ...


class PythonVersionProbe:
    """Check Python version."""

    def __init__(self, min_version: tuple[int, int] = (3, 8)):
        self.min_version = min_version

    def run(self) -> AuditCheck:
        current = sys.version_info[:3]
        is_ok = current[:2] >= self.min_version
        return AuditCheck(
            name="Python Version",
            status=AuditStatus.AVAILABLE if is_ok else AuditStatus.UNSUPPORTED,
            facts={
                "current": f"{current[0]}.{current[1]}.{current[2]}",
                "required": f">={self.min_version[0]}.{self.min_version[1]}",
            },
            details=""
            if is_ok
            else f"Python {current[0]}.{current[1]} is too old. Upgrade to {self.min_version[0]}.{self.min_version[1]}+",
        )


class VirtualEnvProbe:
    """Check if running inside a virtual environment."""

    def run(self) -> AuditCheck:
        in_venv = (
            sys.prefix != sys.base_prefix or "VIRTUAL_ENV" in __import__("os").environ
        )
        venv_path = __import__("os").environ.get(
            "VIRTUAL_ENV", sys.prefix if in_venv else "N/A"
        )
        venv_name = venv_path.split("/")[-1] if venv_path != "N/A" else "N/A"
        return AuditCheck(
            name="Virtual Environment",
            status=AuditStatus.AVAILABLE if in_venv else AuditStatus.NOT_FOUND,
            facts={"in_venv": str(in_venv), "path": venv_name},
            details="" if in_venv else "Not running in a virtual environment",
        )


class EditableInstallProbe:
    """Check if package is installed in editable mode."""

    def run(self) -> AuditCheck:
        from importlib import metadata

        try:
            dist = metadata.distribution("ai-engineering-bootstrap")
            # Check if it's an editable install by looking at direct_url.json
            direct_url_path = (
                dist._path / "direct_url.json" if hasattr(dist, "_path") else None
            )
            is_editable = False

            if direct_url_path and direct_url_path.exists():
                import json

                with open(direct_url_path) as f:
                    direct_url = json.load(f)
                    is_editable = direct_url.get("dir_info", {}).get("editable", False)

            # Alternative check: see if package location is in site-packages or source dir
            if not is_editable:
                loc = dist.locate_file("")
                is_editable = "site-packages" not in str(loc)

            return AuditCheck(
                name="Editable Install",
                status=AuditStatus.AVAILABLE if is_editable else AuditStatus.NOT_FOUND,
                facts={
                    "editable": str(is_editable),
                    "package": "ai-engineering-bootstrap",
                },
                details=""
                if is_editable
                else "Package is not installed in editable mode",
            )
        except metadata.PackageNotFoundError:
            return AuditCheck(
                name="Editable Install",
                status=AuditStatus.NOT_FOUND,
                facts={"editable": "false", "package": "ai-engineering-bootstrap"},
                details="Package not found. Install with: pip install -e '.'",
            )


class PackageProbe:
    """Check if a required package is installed."""

    def __init__(self, package_name: str):
        self.package_name = package_name

    def run(self) -> AuditCheck:
        from importlib import metadata

        try:
            version = metadata.version(self.package_name)
            return AuditCheck(
                name=self.package_name.capitalize(),
                status=AuditStatus.AVAILABLE,
                facts={"version": version},
                details="",
            )
        except metadata.PackageNotFoundError:
            return AuditCheck(
                name=self.package_name.capitalize(),
                status=AuditStatus.NOT_FOUND,
                facts={"version": "missing"},
                details=f"Package '{self.package_name}' is not installed",
            )


class GitExecutableProbe:
    """Check if git executable is available."""

    def run(self) -> AuditCheck:
        import shutil

        git_path = shutil.which("git")
        is_ok = git_path is not None

        if is_ok:
            import subprocess

            try:
                result = subprocess.run(
                    [git_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                version = result.stdout.strip()
            except (subprocess.SubprocessError, OSError):
                version = "unknown"
        else:
            version = "not found"

        return AuditCheck(
            name="Git",
            status=AuditStatus.AVAILABLE if is_ok else AuditStatus.NOT_FOUND,
            facts={"version": version},
            details="" if is_ok else "Git is not installed or not in PATH",
        )


class DockerExecutableProbe:
    """Check if docker executable is available."""

    def run(self) -> AuditCheck:
        import shutil

        docker_path = shutil.which("docker")
        is_ok = docker_path is not None

        if is_ok:
            import subprocess

            try:
                result = subprocess.run(
                    [docker_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                version = result.stdout.strip()
            except (subprocess.SubprocessError, OSError):
                version = "unknown"
        else:
            version = "not found"

        return AuditCheck(
            name="Docker",
            status=AuditStatus.AVAILABLE if is_ok else AuditStatus.NOT_FOUND,
            facts={"version": version},
            details="" if is_ok else "Docker is not installed or not in PATH",
        )


class CursorExecutableProbe:
    """Check whether the Cursor desktop executable is available."""

    def run(self) -> AuditCheck:
        import shutil
        import subprocess

        cursor_path = shutil.which("cursor")
        if cursor_path is None:
            return AuditCheck(
                name="Cursor",
                status=AuditStatus.NOT_FOUND,
                facts={
                    "remediation_action": "install_cursor",
                    "remediation_description": "Install Cursor desktop and integrate it with the development environment.",
                    "remediation_priority": 5,
                },
                details="Cursor is not installed or not in PATH",
            )

        try:
            result = subprocess.run(
                [cursor_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                shell=False,
            )
            version = (result.stdout or result.stderr).strip()
        except (subprocess.SubprocessError, OSError):
            version = "unknown"

        return AuditCheck(
            name="Cursor",
            status=AuditStatus.AVAILABLE,
            facts={"version": version or "unknown", "path": cursor_path},
            details="",
        )


class OSProbe:
    """Check operating system."""

    def run(self) -> AuditCheck:
        import platform

        os_name = platform.system()
        os_version = platform.version()

        if os_name == "Windows":
            win_ver = platform.win32_ver()
            os_display = (
                f"Windows {win_ver[0]} {win_ver[1]}" if win_ver[0] else "Windows"
            )
        elif os_name == "Darwin":
            mac_ver = platform.mac_ver()
            os_display = f"macOS {mac_ver[0]}"
        else:
            # Linux - try to get distribution info
            try:
                distro_info = platform.freedesktop_os_release()
                os_display = f"{distro_info.get('NAME', os_name)} {distro_info.get('VERSION', os_version)}".strip()
            except OSError:
                os_display = f"{os_name} {os_version.split()[0] if os_version else ''}"

        return AuditCheck(
            name="OS",
            status=AuditStatus.AVAILABLE,
            facts={"system": os_name, "version": os_display},
            details="",
        )


class PlatformProbe:
    """Check platform (Windows/Linux/macOS) and architecture."""

    def run(self) -> AuditCheck:
        import platform

        system = platform.system()
        platform_name = (
            "Windows"
            if system == "Windows"
            else ("macOS" if system == "Darwin" else "Linux")
        )

        # Get architecture
        machine = platform.machine()
        arch = (
            "ARM64"
            if machine in ("arm64", "aarch64")
            else "x86_64"
            if machine in ("x86_64", "AMD64")
            else machine
        )

        return AuditCheck(
            name="Platform",
            status=AuditStatus.AVAILABLE,
            facts={"platform": platform_name, "architecture": arch},
            details="",
        )


class RuntimeTargetProbe:
    """Check runtime target information."""

    def run(self) -> AuditCheck:
        import platform

        system = platform.system()
        is_windows = system == "Windows"

        # Development platform
        if system == "Windows":
            win_ver = platform.win32_ver()
            dev_platform = (
                f"Windows {win_ver[0]} {win_ver[1]}" if win_ver[0] else "Windows"
            )
        elif system == "Darwin":
            mac_ver = platform.mac_ver()
            dev_platform = f"macOS {mac_ver[0]}"
        else:
            try:
                distro_info = platform.freedesktop_os_release()
                dev_platform = f"{distro_info.get('NAME', system)} {distro_info.get('VERSION', '')}".strip()
            except OSError:
                dev_platform = system

        # Target runtime is always Ubuntu 24.04 LTS for production/validation
        target_runtime = "Ubuntu 24.04 LTS"

        return AuditCheck(
            name="Runtime Target",
            status=AuditStatus.AVAILABLE,
            facts={
                "development": dev_platform,
                "target": target_runtime,
                "is_windows_dev": str(is_windows),
            },
            details="",
        )

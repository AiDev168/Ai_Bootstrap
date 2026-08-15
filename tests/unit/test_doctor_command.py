"""Unit tests for the Environment Doctor command."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from ai_engineering_bootstrap.audit.models import AuditStatus
from ai_engineering_bootstrap.probes.doctor import (
    DockerExecutableProbe,
    EditableInstallProbe,
    GitExecutableProbe,
    OSProbe,
    PackageProbe,
    PlatformProbe,
    PythonVersionProbe,
    VirtualEnvProbe,
)


class TestPythonVersionProbe:
    """Tests for Python version probe."""

    def test_python_version_available(self):
        """Test that Python version is detected as available."""
        probe = PythonVersionProbe(min_version=(3, 8))
        result = probe.run()

        assert result.name == "Python Version"
        assert result.status == AuditStatus.AVAILABLE
        assert "current" in result.facts

    def test_python_version_unsupported_old_version(self):
        """Test that old Python version is reported as unsupported."""
        # This would only fail if running on very old Python
        probe = PythonVersionProbe(min_version=(99, 0))
        result = probe.run()

        assert result.name == "Python Version"
        assert result.status == AuditStatus.UNSUPPORTED
        assert result.details is not None


class TestVirtualEnvProbe:
    """Tests for virtual environment probe."""

    @patch("sys.prefix", "/path/to/venv")
    @patch("sys.base_prefix", "/usr")
    def test_in_venv_detected(self):
        """Test that virtual environment is detected."""
        probe = VirtualEnvProbe()
        result = probe.run()

        assert result.name == "Virtual Environment"
        assert result.status == AuditStatus.AVAILABLE

    @patch("sys.prefix", "/usr")
    @patch("sys.base_prefix", "/usr")
    def test_not_in_venv(self):
        """Test that non-venv environment is detected."""
        with patch.dict("os.environ", {}, clear=False):
            # Remove VIRTUAL_ENV if it exists
            env = {
                k: v for k, v in __import__("os").environ.items() if k != "VIRTUAL_ENV"
            }
            with patch.dict("os.environ", env, clear=True):
                probe = VirtualEnvProbe()
                result = probe.run()

                assert result.name == "Virtual Environment"
                assert result.status == AuditStatus.NOT_FOUND


class TestEditableInstallProbe:
    """Tests for editable install probe."""

    def test_editable_install_not_found_when_package_missing(self):
        """Test that missing package is reported."""
        from importlib import metadata

        with patch.object(
            metadata,
            "distribution",
            side_effect=metadata.PackageNotFoundError("Package not found"),
        ):
            probe = EditableInstallProbe()
            result = probe.run()

            assert result.name == "Editable Install"
            assert result.status == AuditStatus.NOT_FOUND
            assert result.details is not None


class TestPackageProbe:
    """Tests for package probe."""

    def test_package_available(self):
        """Test that installed package is detected."""
        with patch("importlib.metadata.version", return_value="1.0.0"):
            probe = PackageProbe("testpkg")
            result = probe.run()

            assert result.name == "Testpkg"
            assert result.status == AuditStatus.AVAILABLE
            assert result.facts["version"] == "1.0.0"

    def test_package_not_found(self):
        """Test that missing package is detected."""
        from importlib import metadata

        with patch.object(
            metadata, "version", side_effect=metadata.PackageNotFoundError("Not found")
        ):
            probe = PackageProbe("missing_pkg")
            result = probe.run()

            assert result.name == "Missing_pkg"
            assert result.status == AuditStatus.NOT_FOUND
            assert result.facts["version"] == "missing"


class TestGitExecutableProbe:
    """Tests for git executable probe."""

    def test_git_available(self):
        """Test that git is detected when available."""
        mock_result = MagicMock()
        mock_result.stdout = "git version 2.40.0"

        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch("subprocess.run", return_value=mock_result),
        ):
            probe = GitExecutableProbe()
            result = probe.run()

            assert result.name == "Git"
            assert result.status == AuditStatus.AVAILABLE
            assert "git version" in result.facts["version"]

    def test_git_not_found(self):
        """Test that missing git is detected."""
        with patch("shutil.which", return_value=None):
            probe = GitExecutableProbe()
            result = probe.run()

            assert result.name == "Git"
            assert result.status == AuditStatus.NOT_FOUND
            assert result.facts["version"] == "not found"

    def test_git_timeout_error(self):
        """Test that timeout error is handled gracefully."""
        with (
            patch("shutil.which", return_value="/usr/bin/git"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)),
        ):
            probe = GitExecutableProbe()
            result = probe.run()

            assert result.name == "Git"
            assert result.status == AuditStatus.AVAILABLE
            assert result.facts["version"] == "unknown"


class TestDockerExecutableProbe:
    """Tests for docker executable probe."""

    def test_docker_available(self):
        """Test that docker is detected when available."""
        mock_result = MagicMock()
        mock_result.stdout = "Docker version 24.0.0"

        with (
            patch("shutil.which", return_value="/usr/bin/docker"),
            patch("subprocess.run", return_value=mock_result),
        ):
            probe = DockerExecutableProbe()
            result = probe.run()

            assert result.name == "Docker"
            assert result.status == AuditStatus.AVAILABLE

    def test_docker_not_found(self):
        """Test that missing docker is detected."""
        with patch("shutil.which", return_value=None):
            probe = DockerExecutableProbe()
            result = probe.run()

            assert result.name == "Docker"
            assert result.status == AuditStatus.NOT_FOUND


class TestOSProbe:
    """Tests for OS probe."""

    def test_os_probe_always_available(self):
        """Test that OS probe always returns available."""
        probe = OSProbe()
        result = probe.run()

        assert result.name == "OS"
        assert result.status == AuditStatus.AVAILABLE
        assert "system" in result.facts


class TestPlatformProbe:
    """Tests for platform probe."""

    def test_platform_probe_always_available(self):
        """Test that platform probe always returns available."""
        probe = PlatformProbe()
        result = probe.run()

        assert result.name == "Platform"
        assert result.status == AuditStatus.AVAILABLE
        assert "platform" in result.facts

    @patch("platform.system", return_value="Windows")
    def test_platform_windows(self, mock_system):
        """Test Windows platform detection."""
        probe = PlatformProbe()
        result = probe.run()

        assert result.facts["platform"] == "Windows"

    @patch("platform.system", return_value="Darwin")
    def test_platform_macos(self, mock_system):
        """Test macOS platform detection."""
        probe = PlatformProbe()
        result = probe.run()

        assert result.facts["platform"] == "macOS"

    @patch("platform.system", return_value="Linux")
    def test_platform_linux(self, mock_system):
        """Test Linux platform detection."""
        probe = PlatformProbe()
        result = probe.run()

        assert result.facts["platform"] == "Linux"


class TestDoctorCommandIntegration:
    """Integration tests for the doctor command."""

    def test_doctor_command_exists(self):
        """Test that doctor command is registered."""
        from ai_engineering_bootstrap.cli import app

        # Check that doctor command exists in the app
        # The command functions are stored with their __name__ as key
        assert hasattr(app, "registered_commands")
        # Look for the doctor function in registered callbacks
        found = False
        for cmd in app.registered_commands:
            if hasattr(cmd, "callback") and cmd.callback.__name__ == "doctor":
                found = True
                break
        assert found, "doctor command not found in registered commands"

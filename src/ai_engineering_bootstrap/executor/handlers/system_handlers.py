"""Controlled real handlers for engineering-system tooling."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

from ai_engineering_bootstrap.executor.handlers.base import (
    ActionHandler,
    ExecutionContext,
)
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
Downloader = Callable[[str, Path], None]


class _UbuntuAptHandler(ActionHandler):
    """Base for explicitly typed Ubuntu/Debian apt actions."""

    def __init__(self, runner: CommandRunner = subprocess.run) -> None:
        self._runner = runner

    def _run(
        self, command: Sequence[str], timeout: float
    ) -> subprocess.CompletedProcess[str]:
        return self._runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )

    @staticmethod
    def _result(
        action: ExecutionPlanAction,
        status: ExecutionStatus,
        message: str,
        **details: object,
    ) -> ActionResult:
        return ActionResult(action.action_id, status, message, dict(details))

    def _platform_error(self, action: ExecutionPlanAction) -> ActionResult | None:
        if platform.system() != "Linux":
            return self._result(
                action,
                ExecutionStatus.FAILED,
                "This real handler supports Linux only.",
            )
        if not shutil.which("apt-get"):
            return self._result(
                action,
                ExecutionStatus.FAILED,
                "apt-get is not available on this system.",
            )
        if not shutil.which("sudo"):
            return self._result(
                action,
                ExecutionStatus.FAILED,
                "sudo is not available on this system.",
            )
        return None


class InstallGitRealHandler(_UbuntuAptHandler):
    """Install Git through the system package manager."""

    def execute(
        self, action: ExecutionPlanAction, context: ExecutionContext
    ) -> ActionResult:
        if context.dry_run:
            return self._result(
                action,
                ExecutionStatus.SKIPPED,
                "Git installation simulated in Safe Mode.",
                simulated=True,
            )
        error = self._platform_error(action)
        if error:
            return error
        try:
            result = self._run(("sudo", "apt-get", "install", "-y", "git"), 600)
        except (OSError, subprocess.SubprocessError) as exc:
            return self._result(
                action, ExecutionStatus.FAILED, f"Git installation failed: {exc}"
            )
        if result.returncode != 0:
            output = (result.stderr or result.stdout or "").strip()
            return self._result(
                action,
                ExecutionStatus.FAILED,
                "Git installation failed.",
                returncode=result.returncode,
                output=output[-2000:],
            )
        return self._result(
            action, ExecutionStatus.SUCCESS, "Git installed successfully."
        )


class InstallDockerRealHandler(_UbuntuAptHandler):
    """Install Docker Engine and enable its system service."""

    def execute(
        self, action: ExecutionPlanAction, context: ExecutionContext
    ) -> ActionResult:
        if context.dry_run:
            return self._result(
                action,
                ExecutionStatus.SKIPPED,
                "Docker installation simulated in Safe Mode.",
                simulated=True,
            )
        error = self._platform_error(action)
        if error:
            return error
        try:
            install = self._run(
                ("sudo", "apt-get", "install", "-y", "docker.io"), 900
            )
            if install.returncode != 0:
                output = (install.stderr or install.stdout or "").strip()
                return self._result(
                    action,
                    ExecutionStatus.FAILED,
                    "Docker installation failed.",
                    returncode=install.returncode,
                    output=output[-3000:],
                )
            service = self._run(
                ("sudo", "systemctl", "enable", "--now", "docker"), 120
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return self._result(
                action, ExecutionStatus.FAILED, f"Docker installation failed: {exc}"
            )
        if service.returncode != 0:
            output = (service.stderr or service.stdout or "").strip()
            return self._result(
                action,
                ExecutionStatus.FAILED,
                "Docker was installed but its service could not be started.",
                returncode=service.returncode,
                output=output[-3000:],
            )
        return self._result(
            action,
            ExecutionStatus.SUCCESS,
            "Docker installed and service enabled.",
        )


class InstallCursorRealHandler(_UbuntuAptHandler):
    """Install the official Cursor Linux DEB through apt."""

    API_URL = (
        "https://www.cursor.com/api/download?platform={platform}&releaseTrack=stable"
    )

    def __init__(
        self,
        runner: CommandRunner = subprocess.run,
        downloader: Downloader | None = None,
    ) -> None:
        super().__init__(runner)
        self._downloader = downloader or self._download

    @staticmethod
    def _open_url(url: str, timeout: float):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/151.0 Safari/537.36"
                ),
                "Accept": "application/json,application/octet-stream,*/*",
            },
        )
        return urllib.request.urlopen(request, timeout=timeout)

    @classmethod
    def _download(cls, url: str, destination: Path) -> None:
        with cls._open_url(url, 60) as response, destination.open("wb") as handle:
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)

    @classmethod
    def _fetch_metadata(cls, url: str) -> dict[str, object]:
        with cls._open_url(url, 30) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise TypeError("Cursor download metadata is not a JSON object.")
        return data

    @staticmethod
    def _approved_deb_url(value: object) -> str | None:
        if not isinstance(value, str) or not value.startswith("https://"):
            return None
        parsed = urllib.parse.urlparse(value)
        if parsed.netloc != "downloads.cursor.com":
            return None
        if not parsed.path.lower().endswith(".deb"):
            return None
        return value


    def _resolve_download_url(self, metadata_url: str) -> str:
        metadata = self._fetch_metadata(metadata_url)
        for key in ("debUrl", "downloadUrl"):
            resolved = self._approved_deb_url(metadata.get(key))
            if resolved:
                return resolved
        raise RuntimeError(
            "Cursor metadata did not provide an approved official DEB package or official Cursor download endpoint."
        )

    @staticmethod
    def _cursor_platform() -> str:
        machine = platform.machine().lower()
        if machine in {"aarch64", "arm64"}:
            return "linux-arm64"
        return "linux-x64"

    def execute(
        self, action: ExecutionPlanAction, context: ExecutionContext
    ) -> ActionResult:
        if context.dry_run:
            return self._result(
                action,
                ExecutionStatus.SKIPPED,
                "Cursor installation simulated in Safe Mode.",
                simulated=True,
            )
        error = self._platform_error(action)
        if error:
            return error
        metadata_url = str(
            action.context.get(
                "download_url",
                self.API_URL.format(platform=self._cursor_platform()),
            )
        )
        if not metadata_url.startswith("https://www.cursor.com/api/download?"):
            return self._result(
                action,
                ExecutionStatus.FAILED,
                "Cursor metadata URL is not an approved official Cursor endpoint.",
            )
        try:
            deb_url = self._resolve_download_url(metadata_url)
            with tempfile.TemporaryDirectory(prefix="cursor-bootstrap-") as temp_dir:
                deb = Path(temp_dir) / "cursor.deb"
                self._downloader(deb_url, deb)
                if not deb.is_file() or deb.stat().st_size == 0:
                    return self._result(
                        action,
                        ExecutionStatus.FAILED,
                        "Cursor installer download produced an empty package.",
                    )
                result = self._run(
                    ("sudo", "apt-get", "install", "-y", str(deb)), 900
                )
        except RuntimeError as exc:
            return self._result(
                action,
                ExecutionStatus.FAILED,
                f"Cursor installation failed: {exc}",
                replan_recommended=True,
            )
        except (OSError, subprocess.SubprocessError, urllib.error.URLError) as exc:
            return self._result(
                action, ExecutionStatus.FAILED, f"Cursor installation failed: {exc}"
            )
        if result.returncode != 0:
            output = (result.stderr or result.stdout or "").strip()
            return self._result(
                action,
                ExecutionStatus.FAILED,
                "Cursor installation failed.",
                returncode=result.returncode,
                output=output[-3000:],
            )
        return self._result(
            action, ExecutionStatus.SUCCESS, "Cursor installed successfully."
        )


__all__ = [
    "InstallCursorRealHandler",
    "InstallDockerRealHandler",
    "InstallGitRealHandler",
]

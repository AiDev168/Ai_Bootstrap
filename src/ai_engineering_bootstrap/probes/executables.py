"""Read-only availability probes for external executables."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence

from ai_engineering_bootstrap.models import AuditCheck, AuditStatus

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class ExecutableProbe:
    """Check an executable version without invoking a shell."""

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        runner: CommandRunner = subprocess.run,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._name = name
        self._command = tuple(command)
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def run(self) -> AuditCheck:
        """Run a non-mutating version command and normalize its outcome."""
        try:
            result = self._runner(
                self._command,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError:
            return AuditCheck(name=self._name, status=AuditStatus.NOT_FOUND)
        except subprocess.TimeoutExpired:
            return AuditCheck(
                name=self._name,
                status=AuditStatus.ERROR,
                diagnostic="version check timed out",
            )
        except (OSError, subprocess.SubprocessError) as error:
            return AuditCheck(
                name=self._name,
                status=AuditStatus.ERROR,
                diagnostic=str(error),
            )

        output = (result.stdout or result.stderr).strip()
        if result.returncode != 0:
            return AuditCheck(
                name=self._name,
                status=AuditStatus.ERROR,
                diagnostic=output or f"command exited with status {result.returncode}",
            )
        if not output:
            return AuditCheck(
                name=self._name,
                status=AuditStatus.ERROR,
                diagnostic="version command returned no output",
            )
        return AuditCheck(
            name=self._name,
            status=AuditStatus.AVAILABLE,
            facts={"version": output.splitlines()[0]},
        )


def git_probe() -> ExecutableProbe:
    """Build the Git availability probe."""
    return ExecutableProbe("git", ("git", "--version"))


def docker_probe() -> ExecutableProbe:
    """Build the Docker CLI availability probe."""
    return ExecutableProbe("docker", ("docker", "--version"))

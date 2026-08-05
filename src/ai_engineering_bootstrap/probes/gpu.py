"""Best-effort, read-only GPU information probe."""

from __future__ import annotations

import subprocess

from ai_engineering_bootstrap.audit.models import AuditCheck, AuditStatus
from ai_engineering_bootstrap.probes.executables import CommandRunner


class GpuProbe:
    """Inspect NVIDIA GPU information when its vendor utility is available."""

    _COMMAND = (
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total",
        "--format=csv,noheader,nounits",
    )

    def __init__(
        self,
        runner: CommandRunner = subprocess.run,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._runner = runner
        self._timeout_seconds = timeout_seconds

    def run(self) -> AuditCheck:
        """Return detected GPU facts or a non-fatal availability status."""
        try:
            result = self._runner(
                self._COMMAND,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError:
            return AuditCheck(
                name="gpu",
                status=AuditStatus.UNSUPPORTED,
                diagnostic="GPU vendor utility not available",
            )
        except subprocess.TimeoutExpired:
            return AuditCheck(
                name="gpu",
                status=AuditStatus.ERROR,
                diagnostic="GPU check timed out",
            )
        except (OSError, subprocess.SubprocessError) as error:
            return AuditCheck(
                name="gpu",
                status=AuditStatus.ERROR,
                diagnostic=str(error),
            )

        output = result.stdout.strip()
        if result.returncode != 0 or not output:
            diagnostic = result.stderr.strip() or "GPU information is not available"
            return AuditCheck(
                name="gpu",
                status=AuditStatus.UNSUPPORTED,
                diagnostic=diagnostic,
            )

        devices = [line.strip() for line in output.splitlines() if line.strip()]
        return AuditCheck(
            name="gpu",
            status=AuditStatus.AVAILABLE,
            facts={"devices": " | ".join(devices), "count": str(len(devices))},
        )

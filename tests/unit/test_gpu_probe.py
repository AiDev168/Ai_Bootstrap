"""Unit tests for best-effort GPU detection."""

import subprocess

from ai_engineering_bootstrap.models import AuditStatus
from ai_engineering_bootstrap.probes.gpu import GpuProbe


def test_gpu_probe_reports_detected_devices() -> None:
    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "GPU A, 550.1, 8192\n", "")

    check = GpuProbe(runner=runner).run()

    assert check.status is AuditStatus.AVAILABLE
    assert check.facts == {"devices": "GPU A, 550.1, 8192", "count": "1"}


def test_gpu_probe_is_nonfatal_when_vendor_utility_is_missing() -> None:
    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError

    check = GpuProbe(runner=runner).run()

    assert check.status is AuditStatus.UNSUPPORTED
    assert check.diagnostic == "GPU vendor utility not available"


def test_gpu_probe_reports_vendor_error_as_unsupported() -> None:
    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "no devices found")

    check = GpuProbe(runner=runner).run()

    assert check.status is AuditStatus.UNSUPPORTED
    assert check.diagnostic == "no devices found"

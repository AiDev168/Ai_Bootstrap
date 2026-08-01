"""Unit tests for standard-library system probes."""

from ai_engineering_bootstrap.models import AuditStatus
from ai_engineering_bootstrap.probes.system import (
    OperatingSystemProbe,
    PythonVersionProbe,
)


def test_operating_system_probe_returns_normalized_facts() -> None:
    probe = OperatingSystemProbe(
        system=lambda: "TestOS",
        release=lambda: "1.0",
        machine=lambda: "test64",
    )

    check = probe.run()

    assert check.status is AuditStatus.AVAILABLE
    assert check.facts == {
        "name": "TestOS",
        "release": "1.0",
        "architecture": "test64",
    }


def test_operating_system_probe_normalizes_platform_error() -> None:
    def fail() -> str:
        raise OSError("platform unavailable")

    check = OperatingSystemProbe(system=fail).run()

    assert check.status is AuditStatus.ERROR
    assert check.diagnostic == "platform unavailable"


def test_python_probe_reports_running_interpreter() -> None:
    check = PythonVersionProbe().run()

    assert check.status is AuditStatus.AVAILABLE
    assert check.facts["version"]
    assert check.facts["executable"]
    assert check.facts["implementation"]

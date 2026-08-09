"""Audit module public API."""

from ai_engineering_bootstrap.audit.models import (
    AuditCheck,
    AuditReport,
    EnvironmentReadiness,
)
from ai_engineering_bootstrap.audit.service import AuditService
from ai_engineering_bootstrap.probes.doctor import (
    DockerExecutableProbe,
    EditableInstallProbe,
    GitExecutableProbe,
    OSProbe,
    PackageProbe,
    PlatformProbe,
    PythonVersionProbe,
    RuntimeTargetProbe,
    VirtualEnvProbe,
)
from ai_engineering_bootstrap.probes.gpu import GpuProbe


def default_audit_service() -> AuditService:
    """Create the default audit service with standard probes."""
    probes = [
        PythonVersionProbe(),
        VirtualEnvProbe(),
        EditableInstallProbe(),
        PackageProbe("typer"),
        PackageProbe("rich"),
        PackageProbe("pytest"),
        PackageProbe("ruff"),
        GitExecutableProbe(),
        DockerExecutableProbe(),
        OSProbe(),
        PlatformProbe(),
        RuntimeTargetProbe(),
        GpuProbe(),
    ]
    return AuditService(probes=probes)

__all__ = ["AuditCheck", "AuditReport", "AuditService", "EnvironmentReadiness", "default_audit_service"]

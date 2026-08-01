"""Unit tests for audit aggregation."""

from ai_engineering_bootstrap.audit import AuditService
from ai_engineering_bootstrap.models import AuditCheck, AuditStatus


class SuccessfulProbe:
    """Probe test double returning a fixed successful check."""

    def run(self) -> AuditCheck:
        return AuditCheck("success", AuditStatus.AVAILABLE)


class FailingProbe:
    """Probe test double raising an unexpected error."""

    def run(self) -> AuditCheck:
        raise RuntimeError("unexpected failure")


def test_audit_service_continues_after_probe_failure() -> None:
    report = AuditService((FailingProbe(), SuccessfulProbe())).run()

    assert len(report.checks) == 2
    assert report.checks[0].status is AuditStatus.ERROR
    assert report.checks[0].diagnostic == "unexpected failure"
    assert report.checks[1].name == "success"

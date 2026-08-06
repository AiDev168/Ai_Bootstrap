"""Unit tests for audit aggregation."""

from ai_engineering_bootstrap.audit import AuditService
from ai_engineering_bootstrap.audit.models import AuditCheck, AuditStatus, CheckStatus


class SuccessfulProbe:
    """Probe test double returning a fixed successful check."""

    def run(self) -> AuditCheck:
        return AuditCheck("success", AuditStatus.AVAILABLE, facts={})


class FailingProbe:
    """Probe test double raising an unexpected error."""

    def run(self) -> AuditCheck:
        raise RuntimeError("unexpected failure")


def test_audit_service_continues_after_probe_failure() -> None:
    """Verify that the service captures exceptions as failed checks and continues."""
    report = AuditService((FailingProbe(), SuccessfulProbe())).run()

    assert len(report.checks) == 2
    
    # بررسی چک اول (که خطا داده است)
    first_check = report.checks[0]
    assert first_check.status is CheckStatus.FAILED
    assert "unexpected failure" in first_check.details or "unexpected failure" in str(first_check.facts)
    
    # بررسی چک دوم (که موفق بوده است)
    second_check = report.checks[1]
    assert second_check.name == "success"
    assert second_check.status is CheckStatus.PASSED

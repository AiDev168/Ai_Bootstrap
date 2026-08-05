"""Audit models for Doctor V2."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CheckStatus(str, Enum):
    """Status of an audit check mapped from AuditStatus."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    # سایر وضعیت‌ها در صورت نیاز


@dataclass(frozen=True)
class AuditCheck:
    """Represents a single audit check result normalized for reporting."""
    name: str
    status: CheckStatus
    details: str = ""
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnvironmentReadiness:
    """Determines readiness for Development and Production environments."""
    development_ready: bool
    production_ready: bool
    passed_count: int
    failed_count: int
    warning_count: int
    health_score: int = 100

    @staticmethod
    def calculate(checks: list[AuditCheck]) -> "EnvironmentReadiness":
        """Calculate readiness and health score based on audit checks."""
        passed = sum(1 for c in checks if c.status == CheckStatus.PASSED)
        failed = sum(1 for c in checks if c.status == CheckStatus.FAILED)
        warnings = sum(1 for c in checks if c.status == CheckStatus.WARNING)

        # نگاشت نام‌های نمایشی (از doctor.py) به نام‌های منطقی
        # توجه: نام‌ها دقیقاً باید با مقدار name در AuditCheck برگشتی از پروب‌ها مطابقت داشته باشند
        dev_critical_names = {
            "Python Version",
            "Virtual Environment",
            "Editable Install",
            "Typer",
            "Rich",
            "Pytest",
            "Ruff",
            "Git",
        }

        dev_ready = True
        for check in checks:
            if check.name in dev_critical_names and check.status == CheckStatus.FAILED:
                dev_ready = False
                break

        # Production Ready: Dev Ready + Docker
        docker_check = next((c for c in checks if c.name == "Docker"), None)

        prod_ready = dev_ready
        if docker_check and docker_check.status == CheckStatus.FAILED:
            prod_ready = False

        # Calculate Health Score (0-100)
        total_checks = len(checks)
        if total_checks == 0:
            health_score = 100
        else:
            # Each failed check reduces score by ~10 points
            # Each warning reduces score by ~5 points
            failure_penalty = 10
            warning_penalty = 5
            
            raw_score = 100 - (failed * failure_penalty) - (warnings * warning_penalty)
            health_score = max(0, min(100, raw_score))

        return EnvironmentReadiness(
            development_ready=dev_ready,
            production_ready=prod_ready,
            passed_count=passed,
            failed_count=failed,
            warning_count=warnings,
            health_score=health_score,
        )


@dataclass(frozen=True)
class AuditReport:
    """Complete audit report including readiness status."""
    checks: list[AuditCheck]
    readiness: EnvironmentReadiness

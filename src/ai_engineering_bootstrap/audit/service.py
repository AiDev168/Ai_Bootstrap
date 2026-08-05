"""Audit Service - Orchestrates probes and generates reports."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ai_engineering_bootstrap.audit.models import (
    AuditCheck as NewAuditCheck,
)
from ai_engineering_bootstrap.audit.models import (
    AuditReport,
    CheckStatus,
    EnvironmentReadiness,
)
from ai_engineering_bootstrap.models import AuditCheck, AuditStatus


class AuditService:
    """Executes audit probes and compiles the final report."""

    def __init__(self, probes: Iterable[Any]) -> None:
        self._probes = list(probes)

    def run(self) -> AuditReport:
        """Run all probes and generate the audit report."""
        checks: list[NewAuditCheck] = []

        for probe in self._probes:
            try:
                result: AuditCheck = probe.run()
                
                # نگاشت وضعیت از AuditStatus به CheckStatus
                status_map = {
                    AuditStatus.AVAILABLE: CheckStatus.PASSED,
                    AuditStatus.NOT_FOUND: CheckStatus.FAILED,
                    AuditStatus.UNSUPPORTED: CheckStatus.FAILED,
                    AuditStatus.ERROR: CheckStatus.FAILED,
                }
                status = status_map.get(result.status, CheckStatus.FAILED)

                # استخراج جزئیات
                details = ""
                facts = result.facts or {}
                
                if result.diagnostic:
                    details = result.diagnostic
                elif "version" in facts:
                    details = facts["version"]
                elif "current" in facts:
                    details = facts["current"]
                elif "path" in facts:
                    details = facts["path"]
                elif "system" in facts:
                    details = facts.get("version", facts["system"])
                elif "platform" in facts:
                    arch = facts.get("architecture", "")
                    details = f"{facts['platform']} {arch}".strip()
                elif "editable" in facts:
                    details = facts.get("package", "ai-engineering-bootstrap")
                elif facts:
                    # اگر هیچکدام نبود، اولین مقدار فکت را بگیر (رفع خطای Ruff PERF102)
                    details = str(next(iter(facts.values())))
                
                check = NewAuditCheck(
                    name=result.name,
                    status=status,
                    details=details,
                    facts=facts,
                )
                checks.append(check)

            except Exception as error:  # noqa: BLE001
                # مدیریت خطا: اگر پروب خطا داد، آن را به عنوان Failed ثبت کن
                checks.append(NewAuditCheck(
                    name=getattr(probe, 'name', 'Unknown Probe'),
                    status=CheckStatus.FAILED,
                    details="Probe execution failed",
                    facts={"error": str(error)}
                ))

        readiness = EnvironmentReadiness.calculate(checks)
        return AuditReport(checks=checks, readiness=readiness)

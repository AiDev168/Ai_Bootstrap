"""Audit Service - Orchestrates probes and generates reports."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ai_engineering_bootstrap.audit.models import (
    AuditCheck as NewAuditCheck,
)
from ai_engineering_bootstrap.audit.models import (
    AuditReport,
    AuditStatus,
    CheckCategory,
    CheckStatus,
    EnvironmentReadiness,
)


class AuditService:
    """Executes audit probes and compiles the final report."""

    def __init__(self, probes: Iterable[Any]) -> None:
        self._probes = list(probes)

    @staticmethod
    def _map_category(name: str) -> CheckCategory:
        """Map a check name to its category."""
        name_lower = name.lower()
        
        if "python" in name_lower:
            return CheckCategory.PYTHON
        if "virtual" in name_lower or "editable" in name_lower:
            return CheckCategory.ENVIRONMENT
        if name_lower in ["typer", "rich", "pytest", "ruff"]:
            return CheckCategory.DEPENDENCIES
        if "git" in name_lower:
            return CheckCategory.TOOLS
        if "docker" in name_lower:
            return CheckCategory.CONTAINER
        if "os" in name_lower or "platform" in name_lower:
            return CheckCategory.PLATFORM
        
        return CheckCategory.SYSTEM

    def run(self) -> AuditReport:
        """Run all probes and generate the audit report."""
        checks: list[NewAuditCheck] = []

        for probe in self._probes:
            try:
                result: Any = probe.run()
                
                # نگاشت وضعیت
                status_map = {
                    AuditStatus.AVAILABLE: CheckStatus.PASSED,
                    AuditStatus.NOT_FOUND: CheckStatus.FAILED,
                    AuditStatus.UNSUPPORTED: CheckStatus.FAILED,
                    AuditStatus.ERROR: CheckStatus.FAILED,
                }
                status = status_map.get(result.status, CheckStatus.FAILED)

                # تعیین دسته‌بندی
                category = self._map_category(getattr(result, 'name', 'Unknown'))

                # استخراج جزئیات
                details = getattr(result, 'details', "")
                facts = getattr(result, 'facts', {}) or {}
                
                if not details and hasattr(result, 'diagnostic') and result.diagnostic:
                    details = result.diagnostic
                elif not details and "version" in facts:
                    details = facts["version"]
                elif not details and "current" in facts:
                    details = facts["current"]
                elif not details and "path" in facts:
                    details = facts["path"]
                elif not details and "system" in facts:
                    details = facts.get("version", facts["system"])
                elif not details and "platform" in facts:
                    arch = facts.get("architecture", "")
                    details = f"{facts['platform']} {arch}".strip()
                elif not details and "editable" in facts:
                    details = facts.get("package", "ai-engineering-bootstrap")
                elif not details and facts:
                    details = str(next(iter(facts.values())))
                
                check = NewAuditCheck(
                    name=getattr(result, 'name', 'Unknown'),
                    status=status,
                    category=category,
                    details=details,
                    facts=facts,
                )
                checks.append(check)

            except Exception as error:  # noqa: BLE001
                probe_name = getattr(probe, 'name', 'Unknown Probe')
                category = self._map_category(probe_name)
                checks.append(NewAuditCheck(
                    name=probe_name,
                    status=CheckStatus.FAILED,
                    category=category,
                    details="Probe execution failed",
                    facts={"error": str(error)}
                ))

        readiness = EnvironmentReadiness.calculate(checks)
        return AuditReport(checks=checks, readiness=readiness)

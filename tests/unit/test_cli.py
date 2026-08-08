"""Unit tests for the Typer audit command."""

import json

from typer.testing import CliRunner

from ai_engineering_bootstrap import cli
from ai_engineering_bootstrap.audit.models import (
    AuditCheck,
    AuditReport,
    CheckCategory,
    CheckStatus,
    EnvironmentReadiness,
)

runner = CliRunner()


class StubAuditService:
    """Audit service test double with a deterministic report."""

    def run(self) -> AuditReport:
        checks = [
            AuditCheck(
                name="python",
                status=CheckStatus.PASSED,
                category=CheckCategory.PYTHON,
                details="3.12.0",
                facts={"version": "3.12.0"},
            ),
        ]
        readiness = EnvironmentReadiness(
            development_ready=True,
            production_ready=True,
            passed_count=1,
            failed_count=0,
            warning_count=0,
            health_score=100,
        )
        return AuditReport(checks=checks, readiness=readiness)


def test_audit_command_emits_deterministic_json(monkeypatch: object) -> None:
    monkeypatch.setattr(cli, "default_audit_service", StubAuditService)

    result = runner.invoke(cli.app, ["audit", "--format", "json"])

    assert result.exit_code == 0

    output_data = json.loads(result.stdout)

    # بررسی ساختار جدید خروجی JSON
    # health_score اکنون داخل آبجکت readiness قرار دارد
    assert "readiness" in output_data
    readiness = output_data["readiness"]

    assert readiness["health_score"] == 100
    assert readiness["development_ready"] is True
    assert readiness["production_ready"] is True

    assert "checks" in output_data
    assert len(output_data["checks"]) == 1

    check = output_data["checks"][0]
    assert check["name"] == "python"
    assert check["status"] == "passed"
    assert check["category"] == "Python"
    assert check["facts"]["version"] == "3.12.0"


def test_cli_help_exposes_audit_command() -> None:
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "audit" in result.stdout


def test_audit_json_exit_code_on_success(monkeypatch: object) -> None:
    """Verify that audit --format json returns exit code 0 when development_ready is True."""
    monkeypatch.setattr(cli, "default_audit_service", StubAuditService)

    result = runner.invoke(cli.app, ["audit", "--format", "json"])

    assert result.exit_code == 0

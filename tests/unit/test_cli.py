"""Unit tests for the Typer audit command."""

import json

from typer.testing import CliRunner

from ai_engineering_bootstrap import cli
from ai_engineering_bootstrap.models import AuditCheck, AuditReport, AuditStatus

runner = CliRunner()


class StubAuditService:
    """Audit service test double with a deterministic report."""

    def run(self) -> AuditReport:
        return AuditReport(
            checks=(
                AuditCheck(
                    name="python",
                    status=AuditStatus.AVAILABLE,
                    facts={"version": "3.12.0"},
                ),
            )
        )


def test_audit_command_emits_deterministic_json(monkeypatch: object) -> None:
    monkeypatch.setattr(cli, "default_audit_service", StubAuditService)

    result = runner.invoke(cli.app, ["audit", "--format", "json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "checks": [
            {
                "diagnostic": None,
                "facts": {"version": "3.12.0"},
                "name": "python",
                "status": "available",
            }
        ]
    }


def test_cli_help_exposes_audit_command() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "audit" in result.stdout

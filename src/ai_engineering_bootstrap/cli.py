"""Typer command-line interface for AI Engineering Bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.exceptions import BootstrapError
from ai_engineering_bootstrap.generation import (
    default_project_generator,
    default_template_catalog,
)
from ai_engineering_bootstrap.models import AuditReport, GenerationRequest

app = typer.Typer(
    name="ai-bootstrap",
    help="Audit an AI engineering environment.",
    no_args_is_help=True,
)
console = Console()


def _report_data(report: AuditReport) -> dict[str, list[dict[str, object]]]:
    """Convert an audit report into deterministic JSON-compatible data."""
    return {
        "checks": [
            {
                "name": check.name,
                "status": check.status.value,
                "facts": check.facts,
                "diagnostic": check.diagnostic,
            }
            for check in report.checks
        ]
    }


def _render_table(report: AuditReport) -> None:
    """Render an audit report for interactive use."""
    table = Table(title="Environment Audit")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for check in report.checks:
        details = ", ".join(f"{key}: {value}" for key, value in check.facts.items())
        if check.diagnostic:
            details = check.diagnostic
        table.add_row(check.name, check.status.value, details)
    console.print(table)


@app.command()
def audit(
    output_format: Literal["table", "json"] = typer.Option(
        "table",
        "--format",
        help="Output format.",
    ),
) -> None:
    """Run a read-only audit of the local engineering environment."""
    report = default_audit_service().run()
    if output_format == "json":
        typer.echo(json.dumps(_report_data(report), sort_keys=True))
        return
    _render_table(report)


@app.command("list-templates")
def list_templates() -> None:
    """List template identifiers discovered in the template directory."""
    templates = default_template_catalog().list_templates()
    if not templates:
        typer.echo("No templates found.")
        return
    for template in templates:
        typer.echo(template.template_id)


@app.command("create-project")
def create_project(
    project_name: str = typer.Argument(..., help="Name of the project to create."),
    template_name: str = typer.Option(..., "--template", help="Template identifier."),
) -> None:
    """Create a project from a template without overwriting existing files."""
    try:
        result = default_project_generator().generate(
            GenerationRequest(
                project_name=project_name,
                template_id=template_name,
                destination=Path.cwd(),
            )
        )
    except BootstrapError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Created project: {result.project_path}")


if __name__ == "__main__":
    app()

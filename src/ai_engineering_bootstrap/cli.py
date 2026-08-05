"""Typer command-line interface for AI Engineering Bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport, CheckStatus
from ai_engineering_bootstrap.exceptions import BootstrapError
from ai_engineering_bootstrap.generation import (
    default_project_generator,
    default_template_catalog,
)
from ai_engineering_bootstrap.models import GenerationRequest
from ai_engineering_bootstrap.planner import BootstrapPlanner

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
                "diagnostic": getattr(check, 'diagnostic', ''),
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
        if getattr(check, 'diagnostic', None):
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

    console.print()

    readiness = report.readiness

    if readiness.failed_count == 0:
        console.print(
            Panel.fit(
                "Environment already satisfies the project requirements.",
                title="No Actions Required",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"Passed: {readiness.passed_count}\n"
                f"Failed: {readiness.failed_count}\n"
                f"Warnings: {readiness.warning_count}",
                title="Actions Required",
                border_style="yellow",
            )
        )

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


@app.command()
def doctor() -> None:
    """Run a read-only environment health check (Environment Doctor V2)."""
    # Execute the audit service which runs all probes and calculates readiness
    audit_service = default_audit_service()
    report = audit_service.run()
    
    # Create and render the table with three columns
    table = Table(title="Environment Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")
    
    for check in report.checks:
        # Skip informational checks like Runtime Target from the main grid if desired
        # But usually we show them. Let's show all except purely internal ones.
        if check.name == "Runtime Target":
            continue
            
        status_str = "OK" if check.status == CheckStatus.PASSED else "FAILED"
        if check.status == CheckStatus.WARNING:
            status_str = "WARNING"
        
        # Get meaningful details
        details = check.details
        if not details:
            details = check.facts.get("version", check.facts.get("current", check.facts.get("path", "")))
            if not details or details == "N/A":
                details = check.facts.get("platform", "")
                if check.facts.get("architecture"):
                    details = f"{check.facts.get('platform', '')} {check.facts.get('architecture', '')}".strip()
        
        # Special handling for specific checks to ensure clean output
        if "Python Version" in check.name:
            details = check.facts.get("current", "")
        elif "Virtual Environment" in check.name:
            details = check.facts.get("path", "N/A")
        elif "Editable Install" in check.name:
            details = check.facts.get("package", "ai-engineering-bootstrap")
        elif check.name.lower() in ["typer", "rich", "pytest", "ruff"]:
            details = check.facts.get("version", "missing")
        elif "Git" in check.name or "Docker" in check.name:
            details = check.facts.get("version", "not found")
        elif "OS" in check.name:
            details = check.facts.get("version", "")
        
        table.add_row(check.name, status_str, details)
    
    console.print(table)
    
    # Print runtime target info separately (if available in facts)
    # We look for it in the checks list
    runtime_check = next((c for c in report.checks if c.name == "Runtime Target"), None)
    if runtime_check:
        console.print()
        dev_platform = runtime_check.facts.get("development", "Unknown")
        target_runtime = runtime_check.facts.get("target", "Ubuntu 24.04 LTS")
        
        console.print(f"[bold]Development Platform:[/bold] {dev_platform}")
        console.print(f"[bold]Target Runtime:[/bold]      {target_runtime}")
    
    # Print Summary with Development/Production Readiness
    console.print()
    r = report.readiness
    
    dev_status_str = "[green]YES[/green]" if r.development_ready else "[red]NO[/red]"
    prod_status_str = "[green]YES[/green]" if r.production_ready else "[red]NO[/red]"
    
    console.print(f"[bold]Development Ready :[/bold] {dev_status_str}")
    console.print(f"[bold]Production Ready  :[/bold] {prod_status_str}")
    console.print(f"[bold]Passed :[/bold] {r.passed_count}  [bold]Failed :[/bold] {r.failed_count}  [bold]Warnings :[/bold] {r.warning_count}")
    
    # Print recommendations for failed checks
    if not r.development_ready:
        console.print()
        console.print("[yellow bold]Recommended actions:[/yellow bold]")
        
        recommendations = []
        for check in report.checks:
            if check.status == CheckStatus.FAILED:
                if "Virtual Environment" in check.name:
                    recommendations.append("• Create virtual environment")
                    recommendations.append("• Activate virtual environment")
                elif "Editable Install" in check.name:
                    recommendations.append("• Install project")
                    recommendations.append('  python -m pip install -e ".[dev]"')
                elif check.name.lower() in ["typer", "rich", "pytest", "ruff"]:
                    pkg_name = check.name.lower()
                    recommendations.append(f"• Install {check.name}")
                    recommendations.append(f'  pip install {pkg_name}')
                elif "Git" in check.name:
                    recommendations.append("• Install Git from https://git-scm.com/")
                elif "Docker" in check.name:
                    recommendations.append("• Install Docker from https://docker.com/")
                elif "Python" in check.name:
                    recommendations.append("• Upgrade Python to 3.8+")
                else:
                    recommendations.append(f"• Fix {check.name}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        for rec in unique_recommendations:
            console.print(rec)


@app.command()
def plan() -> None:
    """Generate a read-only execution plan based on environment diagnostics."""
    planner = BootstrapPlanner(console)
    planner.run()


if __name__ == "__main__":
    app()

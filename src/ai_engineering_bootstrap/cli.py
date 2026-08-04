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
from ai_engineering_bootstrap.models import AuditReport, AuditStatus, GenerationRequest
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


@app.command()
def doctor() -> None:
    """Run a read-only environment health check (Environment Doctor)."""
    # Define all probes to run
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
    ]
    
    # Run all probes and collect results
    results = [probe.run() for probe in probes]
    
    # Create and render the table with three columns
    table = Table(title="Environment Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")
    
    passed = 0
    failed = 0
    warnings = 0
    
    for result in results:
        # Skip RuntimeTarget from the main table - it's informational
        if result.name == "Runtime Target":
            continue
            
        status_str = "OK" if result.status == AuditStatus.AVAILABLE else "Missing"
        if result.status == AuditStatus.AVAILABLE:
            passed += 1
        else:
            failed += 1
        
        # Get meaningful details
        details = result.facts.get("version", result.facts.get("current", result.facts.get("path", "")))
        if not details or details == "N/A":
            details = result.facts.get("platform", "")
            if result.facts.get("architecture"):
                details = f"{result.facts.get('platform', '')} {result.facts.get('architecture', '')}".strip()
        
        # Special handling for specific checks
        if "Python Version" in result.name:
            details = result.facts.get("current", "")
        elif "Virtual Environment" in result.name:
            details = result.facts.get("path", "N/A")
        elif "Editable Install" in result.name:
            details = result.facts.get("package", "ai-engineering-bootstrap")
        elif result.name in ["Typer", "Rich", "Pytest", "Ruff"]:
            details = result.facts.get("version", "missing")
        elif "Git" in result.name or "Docker" in result.name:
            details = result.facts.get("version", "not found")
        elif "OS" in result.name:
            details = result.facts.get("version", "")
        
        table.add_row(result.name, status_str, details)
    
    console.print(table)
    
    # Print runtime target info separately
    runtime_probe = next((p for p in results if p.name == "Runtime Target"), None)
    if runtime_probe:
        console.print()
        dev_platform = runtime_probe.facts.get("development", "Unknown")
        target_runtime = runtime_probe.facts.get("target", "Ubuntu 24.04 LTS")
        
        console.print(f"[bold]Development Platform:[/bold] {dev_platform}")
        console.print(f"[bold]Target Runtime:[/bold]      {target_runtime}")
    
    # Print summary
    console.print()
    if failed == 0:
        console.print("[green bold]Environment Ready[/green bold]")
    else:
        console.print("[red bold]Environment NOT Ready[/red bold]")
    
    console.print(f"Passed: {passed}  Failed: {failed}  Warnings: {warnings}")
    
    # Print recommendations for failed checks
    failed_checks = [r for r in results if r.status != AuditStatus.AVAILABLE]
    if failed_checks:
        console.print()
        console.print("[yellow bold]Recommended actions:[/yellow bold]")
        
        recommendations = []
        for check in failed_checks:
            if "Virtual Environment" in check.name:
                recommendations.append("• Create virtual environment")
                recommendations.append("• Activate virtual environment")
            elif "Editable Install" in check.name:
                recommendations.append("• Install project")
                recommendations.append('  python -m pip install -e ".[dev]"')
            elif check.name in ["Typer", "Rich", "Pytest", "Ruff"]:
                pkg_name = check.name.lower()
                recommendations.append(f"• Install {check.name}")
                recommendations.append(f'  pip install {pkg_name}')
            elif "Git" in check.name:
                recommendations.append("• Install Git from https://git-scm.com/")
            elif "Docker" in check.name:
                recommendations.append("• Install Docker from https://docker.com/")
            elif "Python" in check.name:
                recommendations.append("• Upgrade Python to 3.8+")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        for rec in unique_recommendations:
            console.print(rec)


if __name__ == "__main__":
    app()

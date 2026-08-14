#!/usr/bin/env python3
"""Typer command-line interface for AI Engineering Bootstrap."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from ai_engineering_bootstrap.agent.engine import AgentDecisionEngine
from ai_engineering_bootstrap.agent.planning import AgentPlanningService
from ai_engineering_bootstrap.agent.provider import ProviderConfig, build_provider
from ai_engineering_bootstrap.audit import default_audit_service
from ai_engineering_bootstrap.audit.models import AuditReport, CheckStatus
from ai_engineering_bootstrap.backend.server import serve
from ai_engineering_bootstrap.bootstrap import EnvironmentBootstrapService
from ai_engineering_bootstrap.engineering import EngineeringEnvironmentService
from ai_engineering_bootstrap.exceptions import BootstrapError
from ai_engineering_bootstrap.executor import ExecutorEngine
from ai_engineering_bootstrap.executor.capability import default_capability_registry
from ai_engineering_bootstrap.generation import (
    default_project_generator,
    default_template_catalog,
)
from ai_engineering_bootstrap.models import GenerationRequest
from ai_engineering_bootstrap.pipeline import PipelineEngine
from ai_engineering_bootstrap.planner import PlannerEngine

app = typer.Typer(
    name="ai-bootstrap",
    help="Audit an AI engineering environment.",
    no_args_is_help=True,
)
console = Console()


def _build_recovery_agent() -> AgentPlanningService | None:
    """Build the optional LLM-backed recovery planner from environment settings."""
    provider_type = os.getenv("AI_BOOTSTRAP_AGENT_PROVIDER", "").strip()
    if not provider_type:
        return None
    config = ProviderConfig(
        provider_type=provider_type,
        model=os.getenv("AI_BOOTSTRAP_AGENT_MODEL"),
        base_url=os.getenv("AI_BOOTSTRAP_AGENT_BASE_URL"),
        api_key=os.getenv("AI_BOOTSTRAP_AGENT_API_KEY"),
        timeout=int(os.getenv("AI_BOOTSTRAP_AGENT_TIMEOUT", "30")),
        options={
            "api_key_env": os.getenv("AI_BOOTSTRAP_AGENT_API_KEY_ENV", ""),
            "temperature": float(os.getenv("AI_BOOTSTRAP_AGENT_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("AI_BOOTSTRAP_AGENT_MAX_TOKENS", "700")),
        },
    )
    provider = build_provider(config)
    return AgentPlanningService(
        AgentDecisionEngine(provider, default_capability_registry()),
        PlannerEngine(),
        default_capability_registry(),
    )


def _report_data(report: AuditReport) -> dict[str, Any]:
    """Convert an audit report into deterministic JSON-compatible data."""
    return {
        "checks": [
            {
                "name": check.name,
                "status": check.status.value,
                "category": check.category.value,
                "facts": check.facts,
                "details": check.details,
                "recommendations": check.recommendations,
            }
            for check in report.checks
        ],
        "readiness": {
            "development_ready": report.readiness.development_ready,
            "production_ready": report.readiness.production_ready,
            "health_score": report.readiness.health_score,
            "passed": report.readiness.passed_count,
            "failed": report.readiness.failed_count,
            "warnings": report.readiness.warning_count,
        },
    }


def _render_table(report: AuditReport) -> None:
    """Render an audit report for interactive use (Legacy flat view)."""
    table = Table(title="Environment Audit")
    table.add_column("Category")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for check in report.checks:
        status_str = "OK" if check.status == CheckStatus.PASSED else "FAILED"
        if check.status == CheckStatus.WARNING:
            status_str = "WARNING"
        table.add_row(check.category.value, check.name, status_str, check.details)
    console.print(table)


@app.command()
def audit(
    output_format: str = typer.Option("table", "--format", help="Output format."),
) -> None:
    """Run a read-only audit of the local engineering environment."""
    if output_format not in ("table", "json"):
        typer.echo(
            f"Error: Invalid format '{output_format}'. Use 'table' or 'json'.", err=True
        )
        raise typer.Exit(code=1)
    report = default_audit_service().run()
    if output_format == "json":
        exit_code = 0 if report.readiness.development_ready else 1
        typer.echo(json.dumps(_report_data(report), sort_keys=True, indent=2))
        raise typer.Exit(code=exit_code)
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
    """Run a read-only environment health check (Environment Doctor V3)."""
    audit_service = default_audit_service()
    report = audit_service.run()
    grouped_checks: dict[str, list] = {}
    for check in report.checks:
        cat = check.category.value
        if cat not in grouped_checks:
            grouped_checks[cat] = []
        grouped_checks[cat].append(check)
    for category, checks in grouped_checks.items():
        table = Table(title=f"[bold cyan]{category}[/bold cyan]")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        table.add_column("Recommendations", style="yellow")
        for check in checks:
            status = (
                "[green]PASS[/green]"
                if check.status == CheckStatus.PASSED
                else "[red]FAIL[/red]"
                if check.status == CheckStatus.FAILED
                else "[yellow]WARN[/yellow]"
            )
            recommendations = (
                "\n".join(f"• {item}" for item in check.recommendations) or "—"
            )
            table.add_row(check.name, status, check.details or "—", recommendations)
        console.print(table)
    console.print(f"\n[bold]Health Score: {report.readiness.health_score}/100[/bold]")


@app.command()
def engineering() -> None:
    """Inspect engineering environment readiness."""
    report = EngineeringEnvironmentService().run()
    console.print(f"[bold]Project:[/bold] {report.project_root}")
    console.print(f"[bold]Ready:[/bold] {'YES' if report.is_ready else 'NO'}")
    console.print(
        f"[bold]Required tools:[/bold] {'OK' if report.required_tools_ready else 'MISSING'}"
    )
    rules = (
        "[green]PRESENT[/green]"
        if report.cursor_rules_present
        else "[yellow]NOT DETECTED[/yellow]"
    )
    cursor = (
        "[green]AVAILABLE[/green]"
        if report.cursor_available
        else "[yellow]NOT DETECTED[/yellow]"
    )
    console.print(f"• Cursor rules: {rules}")
    console.print(f"• Cursor CLI: {cursor}")
    console.print()
    if report.is_ready:
        console.print("[green bold]✓ Engineering environment is ready.[/green bold]")
    else:
        console.print(
            "[yellow bold]⚠ Engineering environment needs attention.[/yellow bold]"
        )


@app.command()
def plan() -> None:
    """Generate an execution plan based on the latest audit."""
    report = default_audit_service().run()
    plan = PlannerEngine().generate_plan(report)
    if not plan.is_actionable:
        console.print("[green]✓ Environment is healthy. No actions required.[/green]")
        return
    console.print("[bold]Execution Plan:[/bold]\n")
    for i, action in enumerate(plan.actions, 1):
        console.print(f"{i}. [cyan]{action.description}[/cyan]")
        console.print(
            f"   [dim]ID: {action.action_id} | Priority: {action.priority}[/dim]"
        )
        console.print()


@app.command()
def execute() -> None:
    """Execute the generated plan in SAFE mode."""
    report = default_audit_service().run()
    plan = PlannerEngine().generate_plan(report)
    if not plan.is_actionable:
        console.print("[green]✓ Environment is healthy. No actions to execute.[/green]")
        return
    console.print("[yellow bold]⚠️ SAFE MODE ACTIVE[/yellow bold]")
    console.print(
        "The following actions would be taken, but are currently simulated:\n"
    )
    result = ExecutorEngine().execute(plan)
    for res in result.results:
        status_color = (
            "green"
            if res.status.value == "success"
            else "red"
            if res.status.value == "failed"
            else "yellow"
        )
        console.print(
            f"[{status_color}]• [{res.status.value.upper()}] {res.action_id}[/{status_color}]"
        )
        console.print(f"  [dim]{res.message}[/dim]")
    console.print()
    final_color = "green" if result.is_success else "red"
    console.print(f"[{final_color} bold]{result.summary}[/{final_color} bold]")


@app.command()
def serve_gui(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8787, "--port", min=1, max=65535),
) -> None:
    """Run the stable backend API and web GUI."""
    serve(host, port)


@app.command()
def run_pipeline(
    real_execution: bool = typer.Option(
        False, "--real-execution", help="Enable REAL execution mode."
    ),
    interactive_approval: bool = typer.Option(
        False,
        "--interactive-approval",
        help="Prompt for required human approvals before REAL execution.",
    ),
) -> None:
    from ai_engineering_bootstrap.executor.mode import ExecutionMode

    mode = ExecutionMode.REAL if real_execution else ExecutionMode.SAFE
    console.print(f"[bold cyan]Running Full Pipeline ({mode.value.upper()} MODE)...\n")
    if mode == ExecutionMode.REAL:
        console.print("[yellow bold]⚠️ REAL EXECUTION MODE ACTIVE[/yellow bold]")
        console.print("Only pre-approved, non-destructive actions will run.\n")
    engine = PipelineEngine()
    recovery_agent = _build_recovery_agent()
    approval_provider = None
    run_id = "cli-run"
    pending_approvals = None
    if interactive_approval:
        if not real_execution:
            typer.echo(
                "Error: --interactive-approval requires --real-execution", err=True
            )
            raise typer.Exit(code=2)
        from ai_engineering_bootstrap.approval.provider import InMemoryApprovalProvider

        approval_provider = InMemoryApprovalProvider()
    if interactive_approval:
        bootstrap_result = EnvironmentBootstrapService().run(
            mode=mode,
            approval_provider=approval_provider,
            approval_callback=lambda request: typer.confirm(
                f"Approve {request.reason or request.action_id} ({request.risk_level})?",
                default=False,
            ),
            run_id=run_id,
            agent_planning_service=recovery_agent,
        )
        result = bootstrap_result.pipeline_result
        if result is None:
            raise typer.Exit(code=1)
    else:
        result = engine.run(
            mode=mode,
            approval_provider=approval_provider,
            pending_approvals=pending_approvals,
            run_id=run_id,
            agent_planning_service=recovery_agent,
        )
    readiness = result.audit_report.readiness
    console.print(
        f"[bold]1. Audit Complete:[/bold] Health Score {readiness.health_score}/100"
    )
    console.print(
        f"[bold]2. Plan Generated:[/bold] {len(result.original_plan.actions)} action(s)."
    )
    console.print(
        f"[bold]3. Validation:[/bold] {'PASSED' if result.validation_result.is_valid else 'FAILED'}"
    )
    if result.execution_result is not None:
        console.print("[bold]4. Execution:[/bold]")
        for item in result.execution_result.results:
            color = (
                "green"
                if item.status.value == "success"
                else "red"
                if item.status.value == "failed"
                else "yellow"
            )
            console.print(
                f"   • [{color}][{item.status.value.upper()}] {item.action_id}[/{color}]"
            )
    else:
        console.print("[bold]4. Execution:[/bold] SKIPPED")
    if result.verification_result is not None:
        console.print("[bold]5. Verification:[/bold]")
        for item in result.verification_result:
            console.print(f"   • {item.action_id}: {item.status.value}")
    else:
        console.print("[bold]5. Verification:[/bold] SKIPPED")
    if result.is_success:
        console.print("\n[green bold]✓ Pipeline Completed Successfully.[/green bold]")
    else:
        console.print("\n[red bold]⚠ Pipeline Completed with Issues.[/red bold]")


@app.command()
def bootstrap(
    interactive_approval: bool = typer.Option(
        False,
        "--interactive-approval",
        help="Require human approval for REAL bootstrap actions.",
    ),
) -> None:
    """Bootstrap the environment through the canonical pipeline."""
    if interactive_approval:
        typer.echo("Error: --interactive-approval requires --real-execution", err=True)
        raise typer.Exit(code=2)
    result = EnvironmentBootstrapService().run(
        mode=__import__(
            "ai_engineering_bootstrap.executor.mode", fromlist=["ExecutionMode"]
        ).ExecutionMode.SAFE
    )
    if result.pipeline_result is None:
        raise typer.Exit(code=1)
    if result.pipeline_result.is_success:
        console.print("[green]Bootstrap completed successfully.[/green]")
        return
    raise typer.Exit(code=1)

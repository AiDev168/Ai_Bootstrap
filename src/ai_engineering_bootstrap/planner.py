"""Bootstrap Planner - generates execution plans based on Doctor results."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_engineering_bootstrap.audit import (
    AuditCheck,
    AuditReport,
    default_audit_service,
)


class BootstrapPlanner:
    """Generates a read-only execution plan based on environment diagnostics."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self._audit_report: AuditReport | None = None

    def run(self) -> None:
        """Run the planner and display the execution plan."""
        audit_service = default_audit_service()
        self._audit_report = audit_service.run()
        
        actions = self._generate_actions()
        
        if not actions:
            self.console.print(
                Panel(
                    "[green]Environment already satisfies the project requirements.[/green]",
                    title="No Actions Required",
                )
            )
            return
        
        self._display_plan(actions)

    def _generate_actions(self) -> list[dict[str, str]]:
        """Generate action steps based on audit report results."""
        actions: list[dict[str, str]] = []
        
        if not self._audit_report:
            return actions
        
        checks = self._audit_report.checks
        
        for check in checks:
            if check.status != "failed":
                continue
            
            action = self._create_action_for_check(check)
            if action:
                actions.append(action)
        
        return actions

    def _create_action_for_check(self, check: AuditCheck) -> dict[str, str] | None:
        """Create an action item for a failed audit check."""
        check_name = check.name
        
        # Python version check
        if check_name == "python_version":
            return {
                "step": 0,  # Will be updated later
                "action": "Install Python 3.12",
                "command": "Download from https://www.python.org/downloads/",
                "effort": "Medium",
                "duration": "5 min",
            }
        
        # Virtual environment check
        if check_name == "virtualenv":
            venv_actions = [
                {
                    "step": 0,
                    "action": "Create virtual environment",
                    "command": "python -m venv .venv",
                    "effort": "Low",
                    "duration": "1 min",
                },
                {
                    "step": 0,
                    "action": "Activate virtual environment",
                    "command": "source .venv/bin/activate (Linux/macOS) or .venv\\Scripts\\activate (Windows)",
                    "effort": "Low",
                    "duration": "< 1 min",
                },
            ]
            # Special handling for multiple actions from one check
            # We'll handle this in _generate_actions by extending the list
            return venv_actions  # type: ignore[return-value]
        
        # Editable install check
        if check_name == "editable_install":
            return {
                "step": 0,
                "action": "Install project in editable mode",
                "command": 'python -m pip install -e ".[dev]"',
                "effort": "Low",
                "duration": "2 min",
            }
        
        # Package checks
        if check_name.startswith("package_"):
            pkg_name = check_name.replace("package_", "")
            return {
                "step": 0,
                "action": f"Install {pkg_name}",
                "command": f"pip install {pkg_name}",
                "effort": "Low",
                "duration": "1 min",
            }
        
        # Executable checks
        if check_name.startswith("executable_"):
            exe_name = check_name.replace("executable_", "")
            install_cmd = (
                "Install Docker Desktop (Windows/macOS) or Docker Engine (Linux)"
                if exe_name == "docker"
                else "Install from https://git-scm.com/downloads"
            )
            effort = "High" if exe_name == "docker" else "Medium"
            duration = "10 min" if exe_name == "docker" else "5 min"
            return {
                "step": 0,
                "action": f"Install {exe_name.capitalize()}",
                "command": install_cmd,
                "effort": effort,
                "duration": duration,
            }
        
        return None

    def _display_plan(self, actions: list[dict[str, str]]) -> None:
        """Display the execution plan table."""
        self.console.print("\n[bold blue]Execution Plan[/bold blue]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Step", style="dim", width=6)
        table.add_column("Action", style="cyan")
        table.add_column("Command", style="green")
        table.add_column("Effort", style="yellow")
        table.add_column("Duration", style="magenta")
        
        for idx, action in enumerate(actions, start=1):
            action["step"] = idx
            table.add_row(
                str(action["step"]),
                action["action"],
                action["command"],
                action["effort"],
                action["duration"],
            )
        
        self.console.print(table)
        
        # Summary
        total_effort = self._calculate_total_effort(actions)
        total_duration = self._calculate_total_duration(actions)
        
        self.console.print("\n[bold]Summary:[/bold]")
        self.console.print(f"  Total Steps: {len(actions)}")
        self.console.print(f"  Estimated Effort: {total_effort}")
        self.console.print(f"  Estimated Duration: {total_duration}")

    def _calculate_total_effort(self, actions: list[dict[str, str]]) -> str:
        """Calculate overall effort level."""
        effort_scores = {"Low": 1, "Medium": 2, "High": 3}
        total = sum(effort_scores.get(a["effort"], 1) for a in actions)
        
        if total >= 8:
            return "High"
        if total >= 4:
            return "Medium"
        return "Low"

    def _calculate_total_duration(self, actions: list[dict[str, str]]) -> str:
        """Calculate total estimated duration."""
        duration_map = {
            "< 1 min": 0.5,
            "1 min": 1,
            "2 min": 2,
            "5 min": 5,
            "10 min": 10,
        }
        
        total_minutes = sum(
            duration_map.get(a["duration"], 1) for a in actions
        )
        
        if total_minutes >= 15:
            return f"{total_minutes} min"
        return f"{total_minutes} min"

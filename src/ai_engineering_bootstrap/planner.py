"""Bootstrap Planner - generates execution plans based on Doctor results."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_engineering_bootstrap.probes.doctor import (
    DockerExecutableProbe,
    DoctorResult,
    EditableInstallProbe,
    GitExecutableProbe,
    PackageProbe,
    PythonVersionProbe,
    VirtualEnvProbe,
)


class BootstrapPlanner:
    """Generates a read-only execution plan based on environment diagnostics."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self._doctor_result: DoctorResult | None = None

    def run(self) -> None:
        """Run the planner and display the execution plan."""
        self._doctor_result = self._gather_diagnostics()
        
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

    def _gather_diagnostics(self) -> DoctorResult:
        """Gather diagnostics from all probes without duplication."""
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
        ]
        
        results: dict[str, dict[str, Any]] = {}
        for probe in probes:
            result = probe.run()
            results[probe.name] = {
                "status": result.status.value,
                "details": result.facts.get("version", result.facts.get("current", "")),
            }
        
        return DoctorResult(checks=results)

    def _generate_actions(self) -> list[dict[str, str]]:
        """Generate action steps based on diagnostic results."""
        actions: list[dict[str, str]] = []
        
        if not self._doctor_result:
            return actions
        
        checks = self._doctor_result.checks
        
        # Python version check
        python_check = checks.get("python_version", {})
        if python_check.get("status") == "failed":
            actions.append({
                "step": len(actions) + 1,
                "action": "Install Python 3.12",
                "command": "Download from https://www.python.org/downloads/",
                "effort": "Medium",
                "duration": "5 min",
            })
        
        # Virtual environment check
        venv_check = checks.get("virtualenv", {})
        if venv_check.get("status") == "failed":
            actions.append({
                "step": len(actions) + 1,
                "action": "Create virtual environment",
                "command": "python -m venv .venv",
                "effort": "Low",
                "duration": "1 min",
            })
            actions.append({
                "step": len(actions) + 1,
                "action": "Activate virtual environment",
                "command": "source .venv/bin/activate (Linux/macOS) or .venv\\Scripts\\activate (Windows)",
                "effort": "Low",
                "duration": "< 1 min",
            })
        
        # Editable install check
        editable_check = checks.get("editable_install", {})
        if editable_check.get("status") == "failed":
            actions.append({
                "step": len(actions) + 1,
                "action": "Install project in editable mode",
                "command": 'python -m pip install -e ".[dev]"',
                "effort": "Low",
                "duration": "2 min",
            })
        
        # Package checks
        for pkg in ["typer", "rich", "pytest", "ruff"]:
            pkg_check = checks.get(f"package_{pkg}", {})
            if pkg_check.get("status") == "failed":
                actions.append({
                    "step": len(actions) + 1,
                    "action": f"Install {pkg}",
                    "command": f"pip install {pkg}",
                    "effort": "Low",
                    "duration": "1 min",
                })
        
        # Executable checks
        for exe in ["git", "docker"]:
            exe_check = checks.get(f"executable_{exe}", {})
            if exe_check.get("status") == "failed":
                install_cmd = (
                    "Install Docker Desktop (Windows/macOS) or Docker Engine (Linux)"
                    if exe == "docker"
                    else "Install from https://git-scm.com/downloads"
                )
                effort = "High" if exe == "docker" else "Medium"
                duration = "10 min" if exe == "docker" else "5 min"
                actions.append({
                    "step": len(actions) + 1,
                    "action": f"Install {exe.capitalize()}",
                    "command": install_cmd,
                    "effort": effort,
                    "duration": duration,
                })
        
        return actions

    def _display_plan(self, actions: list[dict[str, str]]) -> None:
        """Display the execution plan table."""
        self.console.print("\n[bold blue]Execution Plan[/bold blue]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Step", style="dim", width=6)
        table.add_column("Action", style="cyan")
        table.add_column("Command", style="green")
        table.add_column("Effort", style="yellow")
        table.add_column("Duration", style="magenta")
        
        for action in actions:
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

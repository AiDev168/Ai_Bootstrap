"""Planning Engine - Converts Audit Reports to Execution Plans."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction

if TYPE_CHECKING:
    from ai_engineering_bootstrap.audit.models import AuditReport


class PlannerEngine:
    """Generates an ExecutionPlan based on an AuditReport."""

    # نگاشت نام چک‌ها به شناسه اکشن، توضیحات و اولویت
    # این نگاشت باید پایدار و بدون وابستگی به جزئیات داخلی Probe باشد.
    ACTION_MAP: ClassVar[dict[str, tuple[str, str, int]]] = {
        "Virtual Environment": (
            "fix_venv",
            "Create and activate a virtual environment",
            1,
        ),
        "Editable Install": ("fix_editable", 'Run: pip install -e ".[dev]"', 2),
        "Git": ("install_git", "Install Git and add to PATH", 3),
        "Docker": ("install_docker", "Install Docker and start the daemon", 4),
        "Cursor": (
            "install_cursor",
            "Install Cursor desktop and integrate it with the development environment",
            5,
        ),
        "Python Version": (
            "upgrade_python",
            "Upgrade Python to the required version",
            5,
        ),
    }

    def generate_plan(self, report: AuditReport) -> ExecutionPlan:
        """Generate a deterministic remediation plan from an audit report."""
        actions: list[ExecutionPlanAction] = []
        seen_keys: set[tuple[str, str]] = set()

        failed_checks = [
            check for check in report.checks if check.status.value == "failed"
        ]
        for check in failed_checks:
            facts = check.facts or {}
            action_id = facts.get("remediation_action")
            description = facts.get("remediation_description")
            priority = facts.get("remediation_priority")

            if action_id is None and check.name in self.ACTION_MAP:
                action_id, description, priority = self.ACTION_MAP[check.name]

            if not action_id:
                continue

            package = str(facts.get("package", ""))
            key = (str(action_id), package)
            if key in seen_keys:
                continue

            context = {"check_name": check.name, "details": check.details, **facts}
            if action_id == "create_virtualenv":
                context.setdefault("venv_path", str(Path.cwd() / ".venv"))
            if action_id in {
                "install_python_package",
                "install_project_dependencies",
                "fix_editable",
            }:
                context.setdefault("project_root", str(Path.cwd()))
            if action_id in {
                "install_python_package",
                "install_project_dependencies",
                "fix_editable",
            }:
                context.setdefault(
                    "python_executable", str(Path.cwd() / ".venv" / "bin" / "python")
                )

            actions.append(
                ExecutionPlanAction(
                    action_id=str(action_id),
                    description=str(
                        description
                        or facts.get("remediation_description")
                        or f"Remediate {check.name}"
                    ),
                    priority=int(priority or 50),
                    context=context,
                )
            )
            seen_keys.add(key)

        actions.sort(
            key=lambda item: (
                item.priority,
                item.action_id,
                str(item.context.get("package", "")),
            )
        )
        if any(
            action.action_id == "install_python_package" for action in actions
        ) and any(action.action_id == "create_virtualenv" for action in actions):
            for action in actions:
                if action.action_id == "install_python_package":
                    action.context.setdefault(
                        "python_executable",
                        str(Path.cwd() / ".venv" / "bin" / "python"),
                    )
        return self._build_plan(actions)

    def generate_plan_from_decision(
        self, decision, capability_registry
    ) -> ExecutionPlan:
        """Convert validated Agent capability IDs into a deterministic plan."""
        actions: list[ExecutionPlanAction] = []
        for capability_id in decision.selected_capability_ids:
            capability = capability_registry.get(capability_id)
            if capability is None:
                raise ValueError(f"Unknown capability: {capability_id}")
            priority = int(capability.metadata.get("priority", 50))
            actions.append(
                ExecutionPlanAction(
                    action_id=capability.action_id,
                    description=capability.description,
                    priority=priority,
                    context={
                        "capability_id": capability.capability_id,
                        **capability.metadata,
                    },
                )
            )
        actions.sort(key=lambda item: (item.priority, item.action_id))
        return self._build_plan(actions)

    @staticmethod
    def _build_plan(actions: list[ExecutionPlanAction]) -> ExecutionPlan:
        """Build the immutable plan result from ordered actions."""
        if not actions:
            return ExecutionPlan(False, [], "No actions required.")
        return ExecutionPlan(
            True,
            actions,
            f"{len(actions)} action(s) required to fix the environment.",
        )

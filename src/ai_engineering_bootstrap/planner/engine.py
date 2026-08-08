"""Planning Engine - Converts Audit Reports to Execution Plans."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction

if TYPE_CHECKING:
    from ai_engineering_bootstrap.audit.models import AuditReport


class PlannerEngine:
    """Generates an ExecutionPlan based on an AuditReport."""

    # نگاشت نام چک‌ها به شناسه اکشن، توضیحات و اولویت
    # این نگاشت باید پایدار و بدون وابستگی به جزئیات داخلی Probe باشد.
    ACTION_MAP: ClassVar[dict[str, tuple[str, str, int]]] = {
        "Virtual Environment": ("fix_venv", "Create and activate a virtual environment", 1),
        "Editable Install": ("fix_editable", 'Run: pip install -e ".[dev]"', 2),
        "Git": ("install_git", "Install Git and add to PATH", 3),
        "Docker": ("install_docker", "Install Docker and start the daemon", 4),
        "Python Version": ("upgrade_python", "Upgrade Python to the required version", 5),
    }

    def generate_plan(self, report: AuditReport) -> ExecutionPlan:
        """Generate an execution plan from an audit report."""
        actions: list[ExecutionPlanAction] = []
        seen_ids: set[str] = set()

        failed_checks = [
            c for c in report.checks if c.status.value == "failed"
        ]

        for check in failed_checks:
            if check.name in self.ACTION_MAP:
                action_id, description, priority = self.ACTION_MAP[check.name]
                
                if action_id not in seen_ids:
                    actions.append(ExecutionPlanAction(
                        action_id=action_id,
                        description=description,
                        priority=priority,
                        context={"check_name": check.name, "details": check.details}
                    ))
                    seen_ids.add(action_id)
        
        # مرتب‌سازی بر اساس اولویت برای اطمینان از ترتیب قطعی
        actions.sort(key=lambda x: x.priority)

        is_actionable = len(actions) > 0
        summary = "No actions required." if not is_actionable else f"{len(actions)} action(s) required to fix the environment."

        return ExecutionPlan(
            is_actionable=is_actionable,
            actions=actions,
            summary=summary
        )

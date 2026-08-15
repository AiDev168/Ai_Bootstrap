"""Execution Plan Validator - Safety Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from ai_engineering_bootstrap.executor.security import (
    validate_project_dependency_context,
    validate_python_package_context,
    validate_virtualenv_context,
)
from ai_engineering_bootstrap.planner.models import ExecutionPlan


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating an execution plan."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ExecutionPlanValidator:
    """Validate execution plans before they reach the executor."""

    ALLOWED_ACTIONS: ClassVar[set[str]] = {
        "fix_venv",
        "fix_editable",
        "install_git",
        "install_docker",
        "install_cursor",
        "upgrade_python",
        "check_python_version_real",
        "create_virtualenv",
        "install_python_package",
        "install_project_dependencies",
    }

    @staticmethod
    def canonical_action_id(action_id: str) -> str:
        """Map per-instance action IDs to their canonical executor action IDs."""
        prefix, separator, _subject = action_id.partition(":")
        return prefix if separator and prefix == "install_python_package" else action_id

    def validate(self, plan: ExecutionPlan) -> ValidationResult:
        """Validate structure, canonical action allowlist and typed security context."""
        errors: list[str] = []
        warnings: list[str] = []

        if not plan.is_intact():
            errors.append("Execution plan integrity check failed: plan contents changed after creation.")

        if not plan.actions:
            return ValidationResult(is_valid=not errors, errors=errors, warnings=warnings)

        seen_actions: set[tuple[str, str]] = set()

        for action in plan.actions:
            if not action.action_id or not action.action_id.strip():
                errors.append("Action ID cannot be empty.")
                continue

            canonical_id = self.canonical_action_id(action.action_id)
            package = str(action.context.get("package", "")).strip().lower()
            duplicate_key = (canonical_id, package or action.action_id)
            if duplicate_key in seen_actions:
                errors.append(
                    f"Duplicate action found: '{action.action_id}'"
                    + (f" for package '{package}'." if package else ".")
                )
            seen_actions.add(duplicate_key)

            if canonical_id not in self.ALLOWED_ACTIONS:
                errors.append(
                    f"Action ID '{action.action_id}' is not recognized/implemented and is blocked by Safety Gate."
                )

            context = action.context if isinstance(action.context, dict) else {}
            if canonical_id == "install_python_package":
                errors.extend(validate_python_package_context(context))
            elif canonical_id == "install_project_dependencies":
                errors.extend(validate_project_dependency_context(context))
            elif canonical_id == "create_virtualenv":
                errors.extend(validate_virtualenv_context(context))

            if not action.description or not action.description.strip():
                warnings.append(f"Action '{action.action_id}' has no description.")

        return ValidationResult(is_valid=not errors, errors=errors, warnings=warnings)

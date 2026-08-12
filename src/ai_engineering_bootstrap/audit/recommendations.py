"""Recommendation Engine for Doctor V3 - Context-Aware Suggestions."""

from __future__ import annotations

from ai_engineering_bootstrap.audit.models import AuditCheck, CheckStatus


class RecommendationEngine:
    """Generates context-aware recommendations based on audit check results."""

    @staticmethod
    def generate(check: AuditCheck) -> list[str]:
        """Generate a list of recommendations for a failed or warning check."""
        if check.status == CheckStatus.PASSED:
            return []

        recommendations: list[str] = []
        name_lower = check.name.lower()
        facts = check.facts or {}

        # Python Version
        if "python" in name_lower:
            current = facts.get("current", "unknown")
            required = facts.get("required", "latest")
            recommendations.append(f"Upgrade Python from {current} to {required}.")

        # Virtual Environment
        elif "virtual environment" in name_lower:
            in_venv = facts.get("in_venv", "False")
            if str(in_venv).lower() == "false":
                recommendations.append("Create and activate a virtual environment.")
                recommendations.append("Run: python -m venv .venv && source .venv/bin/activate (Linux/Mac) or .venv\\Scripts\\activate (Windows).")

        # Editable Install
        elif "editable" in name_lower:
            recommendations.append('Install the project in editable mode: python -m pip install -e ".[dev]"')

        # Project/runtime dependencies
        elif facts.get("remediation_action") == "install_python_package":
            requirement = facts.get("requirement", facts.get("package", check.name))
            recommendations.append(f"Install Python dependency: {requirement}")

        # Dependencies (Typer, Rich, Pytest, Ruff)
        elif name_lower == "typer":
            recommendations.append("Install Typer: python -m pip install typer")
        elif name_lower == "rich":
            recommendations.append("Install Rich: python -m pip install rich")
        elif name_lower == "pytest":
            recommendations.append("Install Pytest: python -m pip install pytest")
        elif name_lower == "ruff":
            recommendations.append("Install Ruff: python -m pip install ruff")

        # Tools
        elif "git" in name_lower:
            recommendations.append("Install Git and ensure it is available in your PATH.")
        elif "docker" in name_lower:
            recommendations.append("Install Docker Engine and ensure the daemon is running.")
        elif "cursor" in name_lower:
            recommendations.append("Install Cursor desktop using the approved engineering-environment handler.")

        # Fallback for other failures
        else:
            details = check.details or "Unknown error"
            recommendations.append(f"Investigate failure: {details}")

        return recommendations

    @staticmethod
    def generate_for_all(checks: list[AuditCheck]) -> list[str]:
        """Generate a consolidated list of unique recommendations for all checks."""
        all_recommendations: list[str] = []
        seen: set[str] = set()

        for check in checks:
            recs = RecommendationEngine.generate(check)
            for rec in recs:
                if rec not in seen:
                    seen.add(rec)
                    all_recommendations.append(rec)

        return all_recommendations

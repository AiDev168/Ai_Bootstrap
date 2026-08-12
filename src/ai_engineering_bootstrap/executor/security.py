"""Fail-closed validation helpers for real execution inputs."""

from __future__ import annotations

import re
from pathlib import Path

_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_VERSION_TOKEN = r"[A-Za-z0-9][A-Za-z0-9+_.!*-]*"
_OPERATOR = r"(?:===|==|!=|~=|>=|<=|>|<)"
_SAFE_REQUIREMENT = re.compile(
    rf"^(?P<name>[A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[A-Za-z0-9_.-]+(?:,[A-Za-z0-9_.-]+)*\])?"
    rf"(?:\s*{_OPERATOR}\s*{_VERSION_TOKEN}"
    rf"(?:\s*,\s*{_OPERATOR}\s*{_VERSION_TOKEN})*)?$"
)
_SAFE_EXTRA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def validate_python_package_context(context: dict[str, object]) -> list[str]:
    """Validate a typed Python-package action without invoking external tools."""
    errors: list[str] = []
    package = str(context.get("package", "")).strip()
    requirement = str(context.get("requirement", package)).strip()

    if not package or not _PACKAGE_NAME.fullmatch(package):
        errors.append("Package name is invalid.")
        return errors

    match = _SAFE_REQUIREMENT.fullmatch(requirement)
    if match is None or match.group("name").lower() != package.lower():
        errors.append(
            "Package requirement must contain only the package name, optional extras, "
            "and version constraints."
        )

    lowered = requirement.lower()
    if any(token in requirement for token in ("\x00", "\r", "\n")):
        errors.append("Package requirement contains control characters.")
    if "@" in requirement or "/" in requirement or "\\" in requirement:
        errors.append("Direct URL or filesystem package requirements are not allowed.")
    if lowered.startswith("-"):
        errors.append("pip command options are not allowed in a package requirement.")

    return errors


def validate_project_dependency_context(context: dict[str, object]) -> list[str]:
    """Validate project dependency target metadata."""
    errors: list[str] = []
    project_root = (
        Path(str(context.get("project_root", Path.cwd()))).expanduser().resolve()
    )
    if not project_root.is_dir():
        errors.append(f"Project root does not exist: {project_root}")
    elif not (project_root / "pyproject.toml").is_file():
        errors.append(f"Project root has no pyproject.toml: {project_root}")

    extras = str(context.get("extras", "dev")).strip()
    if extras and not _SAFE_EXTRA.fullmatch(extras):
        errors.append("Project dependency extras contain unsafe characters.")

    return errors


def validate_virtualenv_context(context: dict[str, object]) -> list[str]:
    """Prevent virtual-environment creation outside the declared project root."""
    project_root = (
        Path(str(context.get("project_root", Path.cwd()))).expanduser().resolve()
    )
    target = Path(str(context.get("venv_path", ".venv"))).expanduser()
    resolved_target = (
        (project_root / target).resolve()
        if not target.is_absolute()
        else target.resolve()
    )

    try:
        resolved_target.relative_to(project_root)
    except ValueError:
        return ["Virtual environment path must remain inside the project root."]

    return []


__all__ = [
    "validate_project_dependency_context",
    "validate_python_package_context",
    "validate_virtualenv_context",
]

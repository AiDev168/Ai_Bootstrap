"""Typed domain models for audit and project generation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class AuditStatus(StrEnum):
    """Outcome reported by an individual audit probe."""

    AVAILABLE = "available"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class AuditCheck:
    """Normalized result produced by one environment probe."""

    name: str
    status: AuditStatus
    facts: dict[str, str] = field(default_factory=dict)
    diagnostic: str | None = None


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Complete ordered collection of environment audit checks."""

    checks: tuple[AuditCheck, ...]


class AuditProbe(Protocol):
    """Contract implemented by read-only environment probes."""

    def run(self) -> AuditCheck:
        """Inspect one environment capability and return its result."""
        ...


@dataclass(frozen=True, slots=True)
class TemplateInfo:
    """Metadata for a discovered project template."""

    template_id: str
    source: Path


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Inputs required to create a project."""

    project_name: str
    template_id: str
    destination: Path


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Result returned after successful project creation."""

    project_name: str
    template_id: str
    project_path: Path


class TemplateCatalog(Protocol):
    """Lookup boundary for available project templates."""

    def list_templates(self) -> Sequence[TemplateInfo]:
        """Return templates in deterministic order."""
        ...

    def get_template(self, template_id: str) -> TemplateInfo:
        """Return one template or raise a user-facing error."""
        ...


class ProjectGenerator(Protocol):
    """Boundary for deterministic project generation."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Create a project without overwriting existing content."""
        ...

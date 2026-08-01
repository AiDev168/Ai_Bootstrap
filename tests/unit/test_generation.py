"""Unit tests for template discovery and project generation."""

from pathlib import Path

import pytest

from ai_engineering_bootstrap.exceptions import DestinationConflictError
from ai_engineering_bootstrap.generation import (
    FileSystemProjectGenerator,
    FileSystemTemplateCatalog,
)
from ai_engineering_bootstrap.models import GenerationRequest


def _create_template(templates_root: Path) -> Path:
    template = templates_root / "ai-app-template-v1"
    (template / "src").mkdir(parents=True)
    (template / "README.md").write_text(
        "# {{ project_name }}\n",
        encoding="utf-8",
    )
    (template / "src" / "main.py").write_text(
        'PROJECT_NAME = "{{ project_name }}"\n',
        encoding="utf-8",
    )
    return template


def test_template_discovery_returns_sorted_directories(tmp_path: Path) -> None:
    (tmp_path / "ml-template-v1").mkdir()
    (tmp_path / "ai-app-template-v1").mkdir()
    (tmp_path / "not-a-template.txt").write_text("ignored", encoding="utf-8")

    templates = FileSystemTemplateCatalog(tmp_path).list_templates()

    assert [template.template_id for template in templates] == [
        "ai-app-template-v1",
        "ml-template-v1",
    ]


def test_project_creation_copies_structure_and_renders_name(tmp_path: Path) -> None:
    templates_root = tmp_path / "templates"
    _create_template(templates_root)
    destination = tmp_path / "projects"
    destination.mkdir()
    generator = FileSystemProjectGenerator(FileSystemTemplateCatalog(templates_root))

    result = generator.generate(
        GenerationRequest(
            project_name="sample-app",
            template_id="ai-app-template-v1",
            destination=destination,
        )
    )

    assert result.project_path == destination / "sample-app"
    assert (result.project_path / "README.md").read_text(encoding="utf-8") == (
        "# sample-app\n"
    )
    assert (result.project_path / "src" / "main.py").read_text(
        encoding="utf-8"
    ) == 'PROJECT_NAME = "sample-app"\n'


def test_project_creation_rejects_existing_destination(tmp_path: Path) -> None:
    templates_root = tmp_path / "templates"
    _create_template(templates_root)
    destination = tmp_path / "projects"
    existing_project = destination / "sample-app"
    existing_project.mkdir(parents=True)
    marker = existing_project / "keep.txt"
    marker.write_text("unchanged", encoding="utf-8")
    generator = FileSystemProjectGenerator(FileSystemTemplateCatalog(templates_root))

    with pytest.raises(DestinationConflictError, match="Destination already exists"):
        generator.generate(
            GenerationRequest(
                project_name="sample-app",
                template_id="ai-app-template-v1",
                destination=destination,
            )
        )

    assert marker.read_text(encoding="utf-8") == "unchanged"

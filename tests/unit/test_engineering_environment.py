"""Tests for milestone 29 engineering environment inspection."""

from pathlib import Path

from ai_engineering_bootstrap.engineering import EngineeringEnvironmentService


def test_engineering_environment_reports_cursor_rules(tmp_path: Path, monkeypatch: object) -> None:
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "project.mdc").write_text("rules", encoding="utf-8")

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tool")

    report = EngineeringEnvironmentService(tmp_path).run()

    assert report.cursor_rules_present is True
    assert report.required_tools_ready is True
    assert report.is_ready is True


def test_engineering_environment_missing_rules_is_not_ready(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/tool")

    report = EngineeringEnvironmentService(tmp_path).run()

    assert report.cursor_rules_present is False
    assert report.required_tools_ready is True
    assert report.is_ready is False

"""Tests for the LLM decision validation boundary."""

from ai_engineering_bootstrap.agent.decision_validator import StrategyDecisionValidator
from ai_engineering_bootstrap.agent.strategy_planner import StrategyDecision
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog


def validator() -> StrategyDecisionValidator:
    return StrategyDecisionValidator(ToolCatalog())


def test_unknown_strategy_is_rejected() -> None:
    result = validator().validate(
        StrategyDecision(tool_id="cursor", strategy_name="arbitrary_shell"),
        platform="linux",
        architecture="x86_64",
    )
    assert not result.is_valid
    assert "not registered" in result.errors[0]


def test_untrusted_artifact_domain_is_rejected() -> None:
    result = validator().validate(
        StrategyDecision(
            tool_id="cursor",
            strategy_name="cursor_deb_linux",
            artifact_url="https://evil.example/cursor.deb",
        ),
        platform="linux",
        architecture="x86_64",
    )
    assert not result.is_valid
    assert "not allowlisted" in result.errors[0]


def test_official_cursor_domain_is_accepted() -> None:
    result = validator().validate(
        StrategyDecision(
            tool_id="cursor",
            strategy_name="cursor_deb_linux",
            artifact_url="https://downloads.cursor.com/example/cursor.deb",
        ),
        platform="linux",
        architecture="x86_64",
    )
    assert result.is_valid


def test_architecture_mismatch_is_rejected() -> None:
    result = validator().validate(
        StrategyDecision(tool_id="cursor", strategy_name="cursor_deb_linux"),
        platform="linux",
        architecture="arm64",
    )
    assert not result.is_valid

"""Validation boundary for LLM-generated environment decisions."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from ai_engineering_bootstrap.environment.tool_catalog import (
    Architecture,
    Platform,
    ToolCatalog,
    ToolDefinition,
)


@dataclass(frozen=True)
class DecisionValidationResult:
    """Result of validating one agent strategy decision."""

    is_valid: bool
    errors: tuple[str, ...] = ()


class StrategyDecisionValidator:
    """Enforce catalog, platform, architecture, and source constraints."""

    def __init__(self, catalog: ToolCatalog) -> None:
        self.catalog = catalog

    def validate(
        self,
        decision: object,
        *,
        platform: str | None = None,
        architecture: str | None = None,
    ) -> DecisionValidationResult:
        errors: list[str] = []
        tool_id = str(getattr(decision, "tool_id", ""))
        strategy_name = str(getattr(decision, "strategy_name", ""))
        tool = self.catalog.get(tool_id)
        if tool is None:
            return DecisionValidationResult(False, (f"Unknown tool: {tool_id}",))

        strategy = self._find_strategy(tool, strategy_name)
        if strategy is None:
            return DecisionValidationResult(
                False,
                (f"Strategy '{strategy_name}' is not registered for '{tool_id}'.",),
            )

        requested_platform = self._parse_platform(platform)
        if requested_platform and strategy.platform != requested_platform:
            errors.append(
                f"Strategy '{strategy.strategy_id}' is for {strategy.platform.value}, "
                f"not {requested_platform.value}."
            )

        requested_arch = self._parse_architecture(architecture)
        if requested_arch and requested_arch not in strategy.architecture:
            errors.append(
                f"Strategy '{strategy.strategy_id}' does not support {requested_arch.value}."
            )

        strategy_args = getattr(decision, "strategy_args", {}) or {}
        artifact_url = getattr(decision, "artifact_url", None) or strategy_args.get("artifact_url")
        if artifact_url:
            errors.extend(self._validate_source(tool, artifact_url))

        source = strategy_args.get("source")
        if source not in (None, "", "official"):
            errors.append("LLM decision cannot introduce an untrusted source label.")

        return DecisionValidationResult(not errors, tuple(errors))

    @staticmethod
    def _find_strategy(tool: ToolDefinition, strategy_name: str):
        def public_name(strategy_id: str) -> str:
            if strategy_id.endswith("_pip"):
                return "pip_install"
            if "_deb" in strategy_id:
                return "deb_install"
            if "_apt" in strategy_id:
                return "apt_install"
            if "_binary" in strategy_id:
                return "binary_install"
            if "_tarball" in strategy_id:
                return "tarball_install"
            return strategy_id

        return next(
            (
                strategy
                for strategy in tool.installation_strategies
                if strategy.strategy_id == strategy_name
                or public_name(strategy.strategy_id) == strategy_name
            ),
            None,
        )

    @staticmethod
    def _validate_source(tool: ToolDefinition, url: str) -> list[str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return ["Artifact source must be an HTTPS URL with a hostname."]
        hostname = parsed.hostname.lower()
        allowed = {domain.lower() for domain in tool.allowed_domains}
        if not any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed):
            return [f"Artifact source domain '{hostname}' is not allowlisted for '{tool.tool_id}'."]
        return []

    @staticmethod
    def _parse_platform(value: str | None) -> Platform | None:
        if not value:
            return None
        normalized = value.lower().replace("darwin", "macos")
        try:
            return Platform(normalized)
        except ValueError:
            return None

    @staticmethod
    def _parse_architecture(value: str | None) -> Architecture | None:
        if not value:
            return None
        normalized = value.lower().replace("amd64", "x86_64")
        try:
            return Architecture(normalized)
        except ValueError:
            return None


__all__ = ["DecisionValidationResult", "StrategyDecisionValidator"]

"""Strategy planner for selecting optimal installation strategies."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ai_engineering_bootstrap.agent.provider import LLMProvider
from ai_engineering_bootstrap.environment.models import (
    DesiredEnvironmentState,
    EnvironmentDelta,
    ToolRequirement,
)
from ai_engineering_bootstrap.environment.tool_catalog import (
    ToolCatalog,
    ToolDefinition,
)
from ai_engineering_bootstrap.executor.capability import Capability


@dataclass
class StrategyDecision:
    """Decision about which installation strategy to use for each tool."""

    tool_id: str
    strategy_name: str
    strategy_args: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0
    artifact_url: str | None = None
    version: str | None = None
    source: str = ""
    risk_level: str = "unknown"
    privilege_level: str = "unknown"


@dataclass
class StrategyPlan:
    """Complete strategy plan for all tools in delta."""

    decisions: list[StrategyDecision] = field(default_factory=list)
    overall_confidence: float = 0.0
    reasoning_summary: str = ""
    requires_approval: bool = True

    def get_decisions_requiring_approval(self) -> list[StrategyDecision]:
        """Get decisions that require human approval."""
        return [d for d in self.decisions if d.risk_level in ("medium", "high")]


class StrategyPlanner:
    """Select optimal installation strategies using LLM + deterministic fallback."""

    def __init__(
        self,
        tool_catalog: ToolCatalog,
        provider: LLMProvider | None = None,
    ) -> None:
        self.tool_catalog = tool_catalog
        self.provider = provider

    def plan_strategies(
        self,
        delta: EnvironmentDelta,
        platform: str | None = None,
        architecture: str | None = None,
    ) -> StrategyPlan:
        """
        Generate strategy plan for environment delta.

        Args:
            delta: EnvironmentDelta with tool deltas
            platform: Target platform (linux, darwin, etc.)
            architecture: Target architecture (x86_64, arm64, etc.)

        Returns:
            StrategyPlan with selected strategies for each tool
        """
        if not delta.tool_deltas:
            return StrategyPlan(
                decisions=[],
                overall_confidence=1.0,
                reasoning_summary="No tool changes required.",
            )

        # Filter deltas that need installation
        install_deltas = [
            d
            for d in delta.tool_deltas
            if d.action.value in ("INSTALL", "UPGRADE")
        ]

        if not install_deltas:
            return StrategyPlan(
                decisions=[],
                overall_confidence=1.0,
                reasoning_summary="No installations required.",
            )

        if not self.provider:
            return self._deterministic_plan(install_deltas, platform, architecture)

        try:
            return self._llm_plan(install_deltas, platform, architecture)
        except Exception:
            # Fallback to deterministic on any LLM failure
            return self._deterministic_plan(install_deltas, platform, architecture)

    def _llm_plan(
        self,
        deltas: list,
        platform: str | None,
        architecture: str | None,
    ) -> StrategyPlan:
        """Use LLM to select strategies."""
        prompt = self._build_prompt(deltas, platform, architecture)

        # Get available capabilities for strategy selection
        capabilities = self._get_strategy_capabilities()

        decision = self.provider.decide(prompt, capabilities)

        # Parse strategy decisions from response
        try:
            content = decision.reasoning_summary.strip()
            if content.startswith("```json"):
                content = content[7:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()

            parsed = json.loads(content)
            decisions_data = parsed.get("strategies", [])

            decisions = []
            for dec_data in decisions_data:
                tool_id = dec_data.get("tool_id", "")
                tool_def = self.tool_catalog.get_tool(tool_id)

                decisions.append(
                    StrategyDecision(
                        tool_id=tool_id,
                        strategy_name=dec_data.get("strategy", ""),
                        strategy_args=dec_data.get("args", {}),
                        reasoning=dec_data.get("reasoning", ""),
                        confidence=dec_data.get("confidence", 0.5),
                        artifact_url=dec_data.get("artifact_url"),
                        version=dec_data.get("version"),
                        source=dec_data.get("source", ""),
                        risk_level=tool_def.risk_level if tool_def else "unknown",
                        privilege_level=tool_def.privilege_level
                        if tool_def
                        else "unknown",
                    )
                )

            return StrategyPlan(
                decisions=decisions,
                overall_confidence=decision.confidence,
                reasoning_summary="LLM-selected strategies based on platform and tool metadata.",
                requires_approval=True,
            )
        except (json.JSONDecodeError, KeyError):
            return self._deterministic_plan(deltas, platform, architecture)

    def _deterministic_plan(
        self,
        deltas: list,
        platform: str | None,
        architecture: str | None,
    ) -> StrategyPlan:
        """Deterministic strategy selection based on tool metadata."""
        decisions = []

        for delta_item in deltas:
            tool_id = delta_item.tool_id
            tool_def = self.tool_catalog.get_tool(tool_id)

            if not tool_def:
                continue

            # Select strategy based on platform and available strategies
            strategy_name, strategy_args, source = self._select_strategy_deterministic(
                tool_def, platform, architecture
            )

            if strategy_name:
                decisions.append(
                    StrategyDecision(
                        tool_id=tool_id,
                        strategy_name=strategy_name,
                        strategy_args=strategy_args,
                        reasoning=f"Selected {strategy_name} for {tool_id} on {platform or 'auto'}",
                        confidence=0.85,
                        artifact_url=strategy_args.get("artifact_url"),
                        version=strategy_args.get("version"),
                        source=source,
                        risk_level=tool_def.risk_level,
                        privilege_level=tool_def.privilege_level,
                    )
                )

        return StrategyPlan(
            decisions=decisions,
            overall_confidence=0.85,
            reasoning_summary="Deterministic strategy selection based on tool metadata and platform.",
            requires_approval=True,
        )

    def _select_strategy_deterministic(
        self,
        tool_def: ToolDefinition,
        platform: str | None,
        architecture: str | None,
    ) -> tuple[str | None, dict[str, Any], str]:
        """Select strategy deterministically based on tool definition."""
        # Get strategies for this platform
        platform_key = platform or "linux"
        arch_key = architecture or "x86_64"

        install_strategies = tool_def.installation_strategies.get(platform_key, {})
        arch_strategies = install_strategies.get(arch_key, {})

        if not arch_strategies:
            # Try without architecture specificity
            arch_strategies = install_strategies.get("any", {})

        if not arch_strategies:
            # No strategies found for this platform
            return None, {}, ""

        # Select first available strategy (could be improved with ranking)
        strategy_name = next(iter(arch_strategies.keys()), None)
        if not strategy_name:
            return None, {}, ""

        strategy_config = arch_strategies[strategy_name]
        source = strategy_config.get("source", "official")

        # Extract strategy args
        args = {}
        if "artifact_url" in strategy_config:
            args["artifact_url"] = strategy_config["artifact_url"]
        if "version" in strategy_config:
            args["version"] = strategy_config["version"]
        if "package_name" in strategy_config:
            args["package_name"] = strategy_config["package_name"]

        return strategy_name, args, source

    def _get_strategy_capabilities(self) -> list[Capability]:
        """Get capabilities related to strategy selection."""
        # This could be expanded to include actual strategy capabilities
        return []

    def _build_prompt(
        self,
        deltas: list,
        platform: str | None,
        architecture: str | None,
    ) -> str:
        """Build prompt for LLM strategy selection."""
        tools_info = "\n".join(
            f"- {d.tool_id}: {d.action.value} (desired: {d.desired_status}, actual: {d.actual_status})"
            for d in deltas
        )

        return f"""You are a strategy planner for tool installation.

Given the following tools that need to be installed:
{tools_info}

Platform: {platform or 'auto-detect'}
Architecture: {architecture or 'auto-detect'}

Select the best installation strategy for each tool from these options:
- deb_install: For Debian/Ubuntu .deb packages
- pip_install: For Python packages via pip
- binary_install: For standalone binaries
- apt_install: For APT repository packages
- official_installer: For vendor-provided installers

Respond with ONLY valid JSON in this exact format:
{{
    "strategies": [
        {{
            "tool_id": "cursor",
            "strategy": "deb_install",
            "args": {{"artifact_url": "...", "version": "..."}},
            "reasoning": "...",
            "confidence": 0.95,
            "artifact_url": "...",
            "version": "...",
            "source": "official"
        }}
    ]
}}

Consider:
- Official sources preferred over third-party
- Platform-specific packages when available
- Minimal privilege requirements when possible

/no_think"""


__all__ = ["StrategyPlanner", "StrategyDecision", "StrategyPlan"]

"""Strategy selection for environment reconciliation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ai_engineering_bootstrap.agent.decision_validator import StrategyDecisionValidator
from ai_engineering_bootstrap.agent.provider import LLMProvider
from ai_engineering_bootstrap.environment.models import EnvironmentDelta
from ai_engineering_bootstrap.environment.tool_catalog import (
    ToolCatalog,
    ToolDefinition,
)


@dataclass
class StrategyDecision:
    """Decision about which installation strategy to use for one tool."""

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
    """Validated strategy decisions for all installable deltas."""

    decisions: list[StrategyDecision] = field(default_factory=list)
    overall_confidence: float = 0.0
    reasoning_summary: str = ""
    requires_approval: bool = True

    def get_decisions_requiring_approval(self) -> list[StrategyDecision]:
        return [decision for decision in self.decisions if decision.risk_level in {"medium", "high"}]


class StrategyPlanner:
    """Select installation strategies with deterministic validation of LLM output."""

    def __init__(self, tool_catalog: ToolCatalog, provider: LLMProvider | None = None) -> None:
        self.tool_catalog = tool_catalog
        self.provider = provider
        self.validator = StrategyDecisionValidator(tool_catalog)

    def plan_strategies(
        self,
        delta: EnvironmentDelta,
        platform: str | None = None,
        architecture: str | None = None,
    ) -> StrategyPlan:
        install_deltas = [
            item
            for item in delta.tool_deltas
            if item.action.value in {"install", "upgrade", "INSTALL", "UPGRADE"}
        ]
        if not install_deltas:
            summary = "No tool changes required." if not delta.tool_deltas else "No installations required."
            return StrategyPlan(
                decisions=[],
                overall_confidence=1.0,
                reasoning_summary=summary,
            )
        if not self.provider:
            return self._deterministic_plan(install_deltas, platform, architecture)
        try:
            return self._llm_plan(install_deltas, platform, architecture)
        except Exception:
            return self._deterministic_plan(install_deltas, platform, architecture)

    def _llm_plan(self, deltas: list[Any], platform: str | None, architecture: str | None) -> StrategyPlan:
        decision = self.provider.decide(self._build_prompt(deltas, platform, architecture), [])
        content = decision.reasoning_summary.strip()
        if content.startswith("```json"):
            content = content[7:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        parsed = json.loads(content)
        decisions: list[StrategyDecision] = []
        for item in parsed.get("strategies", []):
            tool_id = str(item.get("tool_id", ""))
            tool_def = self.tool_catalog.get(tool_id)
            if tool_def is None:
                raise ValueError(f"LLM selected unknown tool: {tool_id}")
            strategy_name = str(item.get("strategy", ""))
            args = dict(item.get("args", {}))
            artifact_url = item.get("artifact_url") or args.get("artifact_url")
            strategy = next(
                (
                    candidate
                    for candidate in tool_def.installation_strategies
                    if candidate.strategy_id == strategy_name
                    or self._public_strategy_name(candidate.strategy_id) == strategy_name
                ),
                None,
            )
            if strategy is None:
                raise ValueError(f"LLM selected unregistered strategy '{strategy_name}' for '{tool_id}'")
            strategy_name = self._public_strategy_name(strategy.strategy_id)
            if not artifact_url:
                artifact_url = strategy.source_url
                if artifact_url:
                    args["artifact_url"] = artifact_url

            candidate = StrategyDecision(
                tool_id=tool_id,
                strategy_name=strategy_name,
                strategy_args=args,
                reasoning=str(item.get("reasoning", "")),
                confidence=float(item.get("confidence", decision.confidence)),
                artifact_url=artifact_url,
                version=item.get("version"),
                source=str(item.get("source", "official")),
                risk_level=str(tool_def.risk_level.value),
                privilege_level=str(tool_def.privilege_level.value),
            )
            validation = self.validator.validate(
                candidate,
                platform=platform or "linux",
                architecture=architecture or "x86_64",
            )
            if not validation.is_valid:
                raise ValueError("Invalid LLM strategy decision: " + "; ".join(validation.errors))
            decisions.append(candidate)

        if len(decisions) != len(deltas):
            raise ValueError("LLM did not provide exactly one validated strategy for every installation delta")

        return StrategyPlan(
            decisions=decisions,
            overall_confidence=decision.confidence,
            reasoning_summary="LLM-selected strategies passed catalog and source validation.",
            requires_approval=True,
        )

    def _deterministic_plan(
        self,
        deltas: list[Any],
        platform: str | None,
        architecture: str | None,
    ) -> StrategyPlan:
        decisions: list[StrategyDecision] = []
        for delta in deltas:
            tool_def = self.tool_catalog.get(delta.tool_id)
            if tool_def is None:
                continue
            strategy = self._select_strategy_deterministic(tool_def, platform, architecture)
            if strategy is None:
                continue
            args: dict[str, Any] = {}
            if strategy.source_url:
                args["artifact_url"] = strategy.source_url
            candidate = StrategyDecision(
                tool_id=tool_def.tool_id,
                strategy_name=self._public_strategy_name(strategy.strategy_id),
                strategy_args=args,
                reasoning=f"Selected {strategy.strategy_id} from catalog for {tool_def.tool_id}.",
                confidence=0.85,
                artifact_url=strategy.source_url,
                source="catalog",
                risk_level=tool_def.risk_level.value,
                privilege_level=tool_def.privilege_level.value,
            )
            validation = self.validator.validate(
                candidate,
                platform=platform or "linux",
                architecture=architecture or "x86_64",
            )
            if validation.is_valid:
                decisions.append(candidate)

        return StrategyPlan(
            decisions=decisions,
            overall_confidence=0.85 if decisions else 0.0,
            reasoning_summary="Deterministic strategy selection from catalog metadata.",
            requires_approval=True,
        )

    @staticmethod
    def _public_strategy_name(strategy_id: str) -> str:
        """Normalize catalog strategy IDs to stable semantic strategy names."""
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

    @staticmethod
    def _select_strategy_deterministic(
        tool_def: ToolDefinition,
        platform: str | None,
        architecture: str | None,
    ):
        selected_platform = (platform or "linux").lower().replace("darwin", "macos")
        selected_architecture = (architecture or "x86_64").lower().replace("amd64", "x86_64")
        for strategy in tool_def.installation_strategies:
            if strategy.platform.value != selected_platform:
                continue
            if selected_architecture not in {arch.value for arch in strategy.architecture}:
                continue
            return strategy
        return None

    @staticmethod
    def _build_prompt(deltas: list[Any], platform: str | None, architecture: str | None) -> str:
        tools_info = "\n".join(
            f"- {delta.tool_id}: {delta.action.value}" for delta in deltas
        )
        return f"""You are a strategy planner for tool installation.

Tools requiring installation:
{tools_info}

Platform: {platform or 'auto-detect'}
Architecture: {architecture or 'auto-detect'}

Use only strategies registered in the tool catalog. Never invent a shell command,
source domain, artifact URL, or strategy name. Prefer official sources.

Return ONLY valid JSON:
{{
  "strategies": [
    {{
      "tool_id": "cursor",
      "strategy": "cursor_deb_linux",
      "args": {{"artifact_url": "..."}},
      "reasoning": "...",
      "confidence": 0.95,
      "artifact_url": "...",
      "version": "...",
      "source": "official"
    }}
  ]
}}

/no_think"""


__all__ = ["StrategyDecision", "StrategyPlan", "StrategyPlanner"]

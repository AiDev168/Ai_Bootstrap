"""Runtime selection of deterministic or configured LLM strategy planning."""

from __future__ import annotations

from ai_engineering_bootstrap.agent.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from ai_engineering_bootstrap.agent.provider import build_provider
from ai_engineering_bootstrap.agent.strategy_llm_bridge import StrategyLLMProvider
from ai_engineering_bootstrap.agent.strategy_planner import (
    StrategyPlan,
    StrategyPlanner,
)
from ai_engineering_bootstrap.backend.llm_settings import LLMSettingsService
from ai_engineering_bootstrap.environment.models import EnvironmentDelta
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog


class RuntimeStrategyPlanner(StrategyPlanner):
    """Select the configured provider at plan time and fall back safely."""

    def __init__(
        self,
        catalog: ToolCatalog | None = None,
        settings_service: LLMSettingsService | None = None,
    ) -> None:
        catalog = catalog or ToolCatalog()
        super().__init__(catalog)
        self.settings_service = settings_service or LLMSettingsService()
        self.deterministic = StrategyPlanner(catalog)

    def plan_strategies(
        self,
        delta: EnvironmentDelta,
        platform: str | None = None,
        architecture: str | None = None,
    ) -> StrategyPlan:
        settings = self.settings_service.get()
        if not settings.enabled:
            return self.deterministic.plan_strategies(delta, platform, architecture)
        try:
            provider = StrategyLLMProvider(
                build_provider(self.settings_service.provider_config())
            )
            planner = StrategyPlanner(self.tool_catalog, provider=provider)
            return planner.plan_strategies(delta, platform, architecture)
        except (
            ProviderConnectionError,
            ProviderResponseError,
            ProviderTimeoutError,
            ValueError,
            RuntimeError,
        ):
            return self.deterministic.plan_strategies(delta, platform, architecture)


__all__ = ["RuntimeStrategyPlanner"]

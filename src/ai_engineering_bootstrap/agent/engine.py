"""Agent Decision Engine."""

from __future__ import annotations

from dataclasses import replace

from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.agent.provider import LLMProvider
from ai_engineering_bootstrap.executor.capability import CapabilityRegistry


class AgentDecisionEngine:
    """
    Orchestrates the decision-making process.

    1. Receives context.
    2. Fetches capability metadata from Registry.
    3. Calls LLMProvider to generate a decision.
    4. Validates the decision (Fail-Closed).
    5. Returns validated decision.

    DOES NOT execute actions or bypass SafetyGate.
    """

    def __init__(
        self,
        provider: LLMProvider,
        capability_registry: CapabilityRegistry,
    ) -> None:
        self._provider = provider
        self._registry = capability_registry

    def decide(self, context: str) -> AgentDecision:
        """Generate and validate a decision."""
        # 1. Get capability metadata (NO handlers)
        capabilities = self._registry.list_capabilities()

        # 2. Ask Provider
        decision = self._provider.decide(context, capabilities)

        # 3. Validate Decision (Fail-Closed)
        valid_ids = {c.capability_id for c in capabilities}
        for cap_id in decision.selected_capability_ids:
            if cap_id not in valid_ids:
                raise ValueError(
                    f"Invalid capability ID in decision: {cap_id}. "
                    "Unknown capabilities are rejected."
                )

        # 4. Return Validated Decision
        provider_metadata = self._provider.metadata()
        provider_config = getattr(self._provider, "config", None)
        if provider_config is not None:
            provider_metadata = {
                **provider_metadata,
                "model": getattr(provider_config, "model", None),
                "base_url": getattr(provider_config, "base_url", None),
            }
        metadata = dict(decision.metadata)
        metadata.setdefault("provider", provider_metadata)
        metadata.setdefault("llm_used", provider_metadata.get("provider_type") != "MockProvider")
        return replace(decision, metadata=metadata)


__all__ = ["AgentDecisionEngine"]

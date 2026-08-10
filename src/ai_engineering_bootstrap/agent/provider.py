"""LLM Provider abstraction supporting multiple deployment modes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.executor.capability import Capability


@dataclass
class ProviderConfig:
    """
    Provider-independent configuration.

    Supports:
    - Local Server (e.g., LM Studio, Ollama)
    - Remote API (e.g., OpenAI, OpenRouter)
    - In-Process Model (e.g., transformers, llama.cpp)
    """

    provider_type: str  # "local_server", "remote_api", "in_process"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None  # Injected via env, never hardcoded
    timeout: int = 30
    options: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract contract for LLM providers."""

    @abstractmethod
    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        """
        Generate a structured decision based on context and capabilities.

        Args:
            context: The audit/engineering context description.
            available_capabilities: List of available capability metadata.

        Returns:
            A structured AgentDecision object.
        """


class MockProvider(LLMProvider):
    """
    Deterministic mock provider for testing.

    Does not require network, API keys, or real models.
    Returns a fixed decision for reproducibility.
    """

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        # منطق ساده: اگر کانتکست شامل "fix" باشد، اولین قابلیت را انتخاب کن
        selected_ids = []
        if "fix" in context.lower() and available_capabilities:
            selected_ids = [available_capabilities[0].capability_id]

        return AgentDecision(
            reasoning_summary="Mock decision generated for testing.",
            selected_capability_ids=selected_ids,
            confidence=0.95,
            requires_human_approval=False,
        )


# کلاس‌های Placeholder برای تعریف قرارداد (پیاده‌سازی واقعی در فیچرهای بعدی)
class LocalServerProvider(LLMProvider):
    """Provider for local servers like LM Studio or Ollama."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        raise NotImplementedError(
            "Real LocalServerProvider implementation pending."
        )


class RemoteAPIProvider(LLMProvider):
    """Provider for remote APIs like OpenAI or OpenRouter."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        raise NotImplementedError(
            "Real RemoteAPIProvider implementation pending."
        )


class InProcessProvider(LLMProvider):
    """Provider for in-process models like transformers or llama.cpp."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        raise NotImplementedError(
            "Real InProcessProvider implementation pending."
        )


__all__ = [
    "InProcessProvider",
    "LLMProvider",
    "LocalServerProvider",
    "MockProvider",
    "ProviderConfig",
    "RemoteAPIProvider",
]

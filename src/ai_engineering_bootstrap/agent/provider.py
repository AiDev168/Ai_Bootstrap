#!/usr/bin/env python3
"""LLM Provider abstraction supporting multiple deployment modes."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ai_engineering_bootstrap.agent.exceptions import (
    ProviderConnectionError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.executor.capability import Capability


@dataclass
class ProviderConfig:
    """Provider-independent configuration."""

    provider_type: str
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
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
        pass


class MockProvider(LLMProvider):
    """Deterministic mock provider for testing."""

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        selected_ids = []
        if "fix" in context.lower() and available_capabilities:
            selected_ids = [available_capabilities[0].capability_id]

        return AgentDecision(
            reasoning_summary="Mock decision generated for testing.",
            selected_capability_ids=selected_ids,
            confidence=0.95,
            requires_human_approval=False,
        )


class LocalServerProvider(LLMProvider):
    """Provider for local servers like LM Studio or Ollama."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        if not self.config.base_url:
            raise ProviderConnectionError("base_url is required for LocalServerProvider.")

        prompt = self._build_prompt(context, available_capabilities)

        payload = {
            "model": self.config.model or "default",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.config.base_url}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return self._parse_response(result)
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except (UnicodeDecodeError, AttributeError, ValueError):
                error_body = "Could not read error body"
            raise ProviderConnectionError(f"HTTP Error {e.code}: {e.reason}. Details: {error_body}") from e
        except urllib.error.URLError as e:
            raise ProviderConnectionError(f"Failed to connect: {e.reason}") from e
        except TimeoutError as e:
            raise ProviderTimeoutError("Request timed out.") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise ProviderResponseError(f"Invalid response: {e}") from e

    def _build_prompt(self, context: str, capabilities: list[Capability]) -> str:
        cap_list = "\n".join([f"- ID: {c.capability_id}, Description: {c.description}" for c in capabilities])
        return (
            f"Context: {context}\n\n"
            f"Available capabilities:\n{cap_list}\n\n"
            f"Based on the context, select the most appropriate capabilities.\n"
            f"Respond with a JSON object in this EXACT format:\n"
            f'{{"reasoning_summary": "Brief explanation of why you chose these capabilities", '
            f'"selected_capability_ids": ["id1", "id2"], "confidence": 0.95}}\n\n'
            f"IMPORTANT: Return ONLY the JSON object, no other text, no markdown, no explanation outside JSON."
        )

    def _parse_response(self, data: dict) -> AgentDecision:
        content = ""
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")

        if not content:
            raise ProviderResponseError("No content in response.")

        # حذف احتمالی markdown یا متن اضافی
        content = content.strip()
        content = content.removeprefix("```json")
        content = content.removeprefix("```")
        content = content.removesuffix("```")
        content = content.strip()

        try:
            decision_data = json.loads(content)
            return AgentDecision(
                reasoning_summary=decision_data.get("reasoning_summary", ""),
                selected_capability_ids=decision_data.get("selected_capability_ids", []),
                confidence=float(decision_data.get("confidence", 0.5)),
            )
        except json.JSONDecodeError as e:
            raise ProviderResponseError(f"Could not parse JSON. Received: {content[:200]}...") from e


class RemoteAPIProvider(LLMProvider):
    """Provider for remote APIs."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        if not self.config.base_url or not self.config.api_key:
            raise ProviderConnectionError("base_url and api_key required.")

        prompt = self._build_prompt(context, available_capabilities)
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.config.base_url}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.config.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return self._parse_response(result)
        except urllib.error.HTTPError as e:
            raise ProviderResponseError(f"API Error: {e.code}") from e
        except urllib.error.URLError as e:
            raise ProviderConnectionError(f"Connection failed: {e.reason}") from e
        except TimeoutError as e:
            raise ProviderTimeoutError("Request timed out.") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise ProviderResponseError(f"Invalid response: {e}") from e

    def _build_prompt(self, context: str, capabilities: list[Capability]) -> str:
        cap_list = ", ".join([c.capability_id for c in capabilities])
        return f"Select IDs for: {context}. Available: [{cap_list}]. Output JSON."

    def _parse_response(self, data: dict) -> AgentDecision:
        content = ""
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")

        if not content:
            raise ProviderResponseError("No content in API response.")

        try:
            decision_data = json.loads(content)
            selected = decision_data.get("selected_capability_ids", [])
            if not selected and "capability_id" in decision_data:
                selected = [decision_data["capability_id"]]

            return AgentDecision(
                reasoning_summary=decision_data.get("reasoning_summary", ""),
                selected_capability_ids=selected,
                confidence=float(decision_data.get("confidence", 0.5)),
            )
        except json.JSONDecodeError as e:
            raise ProviderResponseError(f"Could not parse JSON: {content}") from e


class InProcessProvider(LLMProvider):
    """Provider for in-process models."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.model = config.options.get("model_instance")

    def decide(
        self,
        context: str,
        available_capabilities: list[Capability],
    ) -> AgentDecision:
        if self.model is None:
            raise ProviderConnectionError("No model instance provided.")

        try:
            prompt = self._build_prompt(context, available_capabilities)
            if hasattr(self.model, "generate"):
                output = self.model.generate(prompt)
            else:
                raise ProviderResponseError("Model has no 'generate' method.")

            decision_data = json.loads(output)
            selected = decision_data.get("selected_capability_ids", [])
            if not selected and "capability_id" in decision_data:
                selected = [decision_data["capability_id"]]

            return AgentDecision(
                reasoning_summary=decision_data.get("reasoning_summary", ""),
                selected_capability_ids=selected,
                confidence=float(decision_data.get("confidence", 0.5)),
            )
        except Exception as e:
            if isinstance(e, (ProviderConnectionError, ProviderResponseError)):
                raise
            raise ProviderResponseError(f"Model execution failed: {e}") from e

    def _build_prompt(self, context: str, capabilities: list[Capability]) -> str:
        return f"Context: {context}. Available: {[c.capability_id for c in capabilities]}. Output JSON."


__all__ = [
    "InProcessProvider",
    "LLMProvider",
    "LocalServerProvider",
    "MockProvider",
    "ProviderConfig",
    "RemoteAPIProvider",
]

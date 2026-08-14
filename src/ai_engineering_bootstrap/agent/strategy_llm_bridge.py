"""Structured JSON bridge for strategy-planning LLM providers."""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.agent.provider import (
    InProcessProvider,
    LLMProvider,
    MockProvider,
    RemoteAPIProvider,
)


_MOCK_STRATEGIES = {
    "cursor": "cursor_deb_linux",
    "git": "git_apt",
    "docker": "docker_apt",
    "python": "python_apt",
    "ruff": "ruff_pip",
    "pytest": "pytest_pip",
    "black": "black_pip",
    "gh": "gh_apt",
}


class StrategyLLMProvider(LLMProvider):
    """Adapt an existing LLM provider to the strategy-planning JSON contract."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def decide(self, context: str, available_capabilities: list[Any]) -> AgentDecision:
        payload = _complete_json(self.provider, context)
        return AgentDecision(
            reasoning_summary=json.dumps(payload, ensure_ascii=False),
            confidence=float(payload.get("confidence", 0.9)),
        )

    def metadata(self) -> dict[str, Any]:
        meta = dict(self.provider.metadata())
        config = getattr(self.provider, "config", None)
        if config is not None:
            meta["model"] = config.model or ""
            meta["base_url"] = config.base_url or ""
        return meta


def _complete_json(provider: LLMProvider, prompt: str) -> dict[str, Any]:
    if isinstance(provider, MockProvider):
        strategies = []
        for tool_id, action in re.findall(r"^- ([^:]+): ([^\n]+)$", prompt, re.MULTILINE):
            strategy_id = _MOCK_STRATEGIES.get(tool_id.strip())
            if strategy_id:
                strategies.append(
                    {
                        "tool_id": tool_id.strip(),
                        "strategy": strategy_id,
                        "args": {},
                        "reasoning": f"Mock provider selected catalog strategy {strategy_id}.",
                        "confidence": 1.0,
                        "source": "catalog",
                    }
                )
        return {
            "strategies": strategies,
            "confidence": 1.0,
        }

    if isinstance(provider, InProcessProvider):
        output = provider.model.generate(prompt)
        data = json.loads(output)
        if not isinstance(data, dict):
            raise ValueError("In-process strategy response must be a JSON object.")
        return data

    config = getattr(provider, "config", None)
    if config is None or not config.base_url:
        raise ValueError("Provider is missing a base URL.")

    system_prompt = (
        "You are an engineering environment strategy planner. "
        "Return ONLY valid JSON matching the requested schema. "
        "Use only strategies present in the tool catalog."
    )
    payload = {
        "model": config.model or "default",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(config.options.get("temperature", 0.1)),
        "max_tokens": int(config.options.get("max_tokens", 900)),
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if isinstance(provider, RemoteAPIProvider) and config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    request = urllib.request.Request(
        f"{config.base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=config.timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Provider returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Provider returned empty strategy content.")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("Provider strategy response must be a JSON object.")
    return parsed


__all__ = ["StrategyLLMProvider"]

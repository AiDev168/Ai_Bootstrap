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
    """Adapt an LLM provider to a structured JSON contract."""

    def __init__(self, provider: LLMProvider, system_prompt: str | None = None) -> None:
        self.provider = provider
        self.system_prompt = system_prompt or (
            "You are an engineering environment decision engine. "
            "Return ONLY valid JSON matching the requested schema. "
            "Use only strategies present in the supplied catalog."
        )

    def decide(self, context: str, available_capabilities: list[Any]) -> AgentDecision:
        payload = _complete_json(self.provider, context, self.system_prompt)
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


def _decode_http_json(raw: bytes) -> dict[str, Any]:
    """Decode an OpenAI-compatible response with a narrow legacy recovery path."""
    text = raw.decode("utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        marker = '"content":"'
        start = text.find(marker)
        end = text.rfind('"}]}')
        if start < 0 or end <= start + len(marker):
            raise
        inner = text[start + len(marker) : end]
        parsed = json.loads(inner)
        if not isinstance(parsed, dict):
            raise TypeError("Recovered provider JSON content must be an object.")
        return {"choices": [{"message": {"content": json.dumps(parsed)}}]}
    if not isinstance(data, dict):
        raise TypeError("Provider HTTP response must be a JSON object.")
    return data


def _complete_json(provider: LLMProvider, prompt: str, system_prompt: str) -> dict[str, Any]:
    if isinstance(provider, MockProvider):
        strategies = []
        for tool_id, _action in re.findall(r"^- ([^:]+): ([^\n]+)$", prompt, re.MULTILINE):
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
        if "intent parser" in system_prompt.lower():
            return {
                "natural_language_goal": prompt.split("User goal:", 1)[-1].split("/no_think", 1)[0].strip(),
                "required_tools": [],
                "optional_tools": [],
                "excluded_tools": [],
                "languages": [],
                "frameworks": [],
                "project_dependencies": [],
                "excluded_packages": [],
                "constraints": [],
                "platform_preferences": [],
                "confidence": 0.0,
            }
        return {"strategies": strategies, "confidence": 1.0}

    if isinstance(provider, InProcessProvider):
        output = provider.model.generate(prompt)
        data = json.loads(output)
        if not isinstance(data, dict):
            raise TypeError("In-process JSON response must be an object.")
        return data

    config = getattr(provider, "config", None)
    if config is None or not config.base_url:
        raise ValueError("Provider is missing a base URL.")

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
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    base_url = config.base_url.rstrip("/")
    endpoint = (
        f"{base_url}/chat/completions"
        if base_url.endswith("/v1")
        else f"{base_url}/v1/chat/completions"
    )
    request = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers
    )
    with urllib.request.urlopen(request, timeout=config.timeout) as response:
        data = _decode_http_json(response.read())
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Provider returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        content = message.get("reasoning_content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Provider returned empty JSON content.")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise TypeError("Provider JSON response must be an object.")
    return parsed


__all__ = ["StrategyLLMProvider"]

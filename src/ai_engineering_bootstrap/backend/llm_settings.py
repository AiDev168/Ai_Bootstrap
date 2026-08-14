"""LLM configuration shared by GUI and application services."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ai_engineering_bootstrap.agent.provider import ProviderConfig


SUPPORTED_PROVIDERS = frozenset({"local_server", "remote_api", "in_process", "mock"})


@dataclass(frozen=True)
class LLMSettings:
    """Safe-to-display LLM configuration."""

    provider: str = "local_server"
    model: str = ""
    base_url: str = "http://127.0.0.1:1234/v1"
    api_key_configured: bool = False
    enabled: bool = False


class LLMSettingsService:
    """Manage process-local provider settings without exposing secrets."""

    ENV_PROVIDER = "AI_BOOTSTRAP_AGENT_PROVIDER"
    ENV_MODEL = "AI_BOOTSTRAP_AGENT_MODEL"
    ENV_BASE_URL = "AI_BOOTSTRAP_AGENT_BASE_URL"
    ENV_API_KEY = "AI_BOOTSTRAP_AGENT_API_KEY"

    def get(self) -> LLMSettings:
        provider = os.getenv(self.ENV_PROVIDER, "local_server").strip() or "local_server"
        model = os.getenv(self.ENV_MODEL, "").strip()
        base_url = os.getenv(self.ENV_BASE_URL, "http://127.0.0.1:1234/v1").strip()
        api_key = os.getenv(self.ENV_API_KEY, "").strip()
        enabled = provider == "mock" or (provider != "in_process" and bool(model and base_url))
        return LLMSettings(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key_configured=bool(api_key),
            enabled=enabled,
        )

    def provider_config(self) -> ProviderConfig:
        """Return the runtime provider configuration, including the secret only in memory."""
        settings = self.get()
        return ProviderConfig(
            provider_type=settings.provider,
            model=settings.model or None,
            base_url=settings.base_url or None,
            api_key=os.getenv(self.ENV_API_KEY, "").strip() or None,
            timeout=30,
            options={"temperature": 0.1, "max_tokens": 900},
        )

    def update(self, payload: dict[str, Any]) -> LLMSettings:
        provider = str(payload.get("provider", "local_server")).strip() or "local_server"
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        model = str(payload.get("model", "")).strip()
        base_url = str(payload.get("base_url", "")).strip()
        if provider == "local_server" and not base_url:
            base_url = "http://127.0.0.1:1234/v1"
        api_key = str(payload.get("api_key", "")).strip()
        os.environ[self.ENV_PROVIDER] = provider
        os.environ[self.ENV_MODEL] = model
        os.environ[self.ENV_BASE_URL] = base_url
        if api_key:
            os.environ[self.ENV_API_KEY] = api_key
        elif self.ENV_API_KEY in os.environ:
            del os.environ[self.ENV_API_KEY]
        return self.get()

    def test_connection(self) -> dict[str, Any]:
        settings = self.get()
        if settings.provider == "mock":
            return {"ok": True, "provider": "mock", "message": "Mock provider is available."}
        if settings.provider == "in_process":
            return {
                "ok": False,
                "provider": "in_process",
                "message": "In-process provider requires a host model instance and cannot be tested from the GUI.",
            }
        if not settings.base_url:
            return {"ok": False, "provider": settings.provider, "message": "LLM base URL is not configured."}
        url = settings.base_url.rstrip("/") + "/models"
        headers = {"Accept": "application/json"}
        api_key = os.getenv(self.ENV_API_KEY, "").strip()
        if settings.provider == "remote_api" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return {"ok": True, "provider": settings.provider, "status": response.status, "url": url}
        except urllib.error.HTTPError as error:
            return {"ok": False, "provider": settings.provider, "status": error.code, "message": f"HTTP {error.code}: {error.reason}", "url": url}
        except (urllib.error.URLError, TimeoutError) as error:
            return {"ok": False, "provider": settings.provider, "message": str(error), "url": url}


__all__ = ["LLMSettings", "LLMSettingsService", "SUPPORTED_PROVIDERS"]

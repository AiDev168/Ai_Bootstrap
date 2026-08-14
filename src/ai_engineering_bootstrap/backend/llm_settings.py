"""Local LLM configuration for the GUI and application services."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMSettings:
    """Safe-to-display local LLM configuration."""

    provider: str = "local_server"
    model: str = ""
    base_url: str = "http://127.0.0.1:1234/v1"
    api_key_configured: bool = False
    enabled: bool = False


class LLMSettingsService:
    """Manage GUI-visible LLM settings without exposing secrets."""

    ENV_PROVIDER = "AI_BOOTSTRAP_AGENT_PROVIDER"
    ENV_MODEL = "AI_BOOTSTRAP_AGENT_MODEL"
    ENV_BASE_URL = "AI_BOOTSTRAP_AGENT_BASE_URL"
    ENV_API_KEY = "AI_BOOTSTRAP_AGENT_API_KEY"

    def get(self) -> LLMSettings:
        provider = os.getenv(self.ENV_PROVIDER, "local_server").strip() or "local_server"
        model = os.getenv(self.ENV_MODEL, "").strip()
        base_url = os.getenv(self.ENV_BASE_URL, "http://127.0.0.1:1234/v1").strip()
        api_key = os.getenv(self.ENV_API_KEY, "").strip()
        return LLMSettings(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key_configured=bool(api_key),
            enabled=bool(model and base_url),
        )

    def update(self, payload: dict[str, Any]) -> LLMSettings:
        provider = str(payload.get("provider", "local_server")).strip() or "local_server"
        model = str(payload.get("model", "")).strip()
        base_url = str(payload.get("base_url", "http://127.0.0.1:1234/v1")).strip()
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
        if not settings.base_url:
            return {"ok": False, "message": "LLM base URL is not configured."}
        url = settings.base_url.rstrip("/") + "/models"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return {"ok": True, "status": response.status, "url": url}
        except urllib.error.HTTPError as error:
            return {"ok": False, "status": error.code, "message": f"HTTP {error.code}: {error.reason}", "url": url}
        except (urllib.error.URLError, TimeoutError) as error:
            return {"ok": False, "message": str(error), "url": url}


__all__ = ["LLMSettings", "LLMSettingsService"]

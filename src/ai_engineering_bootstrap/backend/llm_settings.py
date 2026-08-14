"""Persistent LLM configuration shared by GUI and application services."""

from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_engineering_bootstrap.agent.provider import ProviderConfig

SUPPORTED_PROVIDERS = frozenset({"local_server", "remote_api", "in_process", "mock"})
DEFAULT_PROVIDER = "mock"
DEFAULT_SETTINGS_FILE = Path.home() / ".config" / "ai-engineering-bootstrap" / "llm-settings.json"


@dataclass(frozen=True)
class LLMSettings:
    """Safe-to-display LLM configuration."""

    provider: str = DEFAULT_PROVIDER
    model: str = ""
    base_url: str = ""
    api_key_configured: bool = False
    enabled: bool = True


class LLMSettingsStore:
    """Persist provider settings locally with restrictive file permissions."""

    ENV_FILE = "AI_BOOTSTRAP_LLM_SETTINGS_FILE"
    ENV_PROVIDER = "AI_BOOTSTRAP_AGENT_PROVIDER"
    ENV_MODEL = "AI_BOOTSTRAP_AGENT_MODEL"
    ENV_BASE_URL = "AI_BOOTSTRAP_AGENT_BASE_URL"
    ENV_API_KEY = "AI_BOOTSTRAP_AGENT_API_KEY"

    def __init__(self, path: Path | None = None) -> None:
        configured = os.getenv(self.ENV_FILE, "").strip()
        self.path = path or Path(configured) if configured else path or DEFAULT_SETTINGS_FILE

    def load(self) -> dict[str, str]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
            if isinstance(data, dict):
                return {str(key): str(value) for key, value in data.items() if value is not None}
        return self._load_legacy_environment()

    def save(self, values: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".llm-settings-", dir=self.path.parent)
        try:
            os.chmod(temp_name, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(values, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_name, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _load_legacy_environment(self) -> dict[str, str]:
        provider = os.getenv(self.ENV_PROVIDER, "").strip()
        model = os.getenv(self.ENV_MODEL, "").strip()
        base_url = os.getenv(self.ENV_BASE_URL, "").strip()
        api_key = os.getenv(self.ENV_API_KEY, "").strip()
        if not any((provider, model, base_url, api_key)):
            return {"provider": DEFAULT_PROVIDER, "model": "", "base_url": "", "api_key": ""}
        return {"provider": provider or DEFAULT_PROVIDER, "model": model, "base_url": base_url, "api_key": api_key}


class LLMSettingsService:
    """Manage persistent provider settings without exposing secrets."""

    ENV_PROVIDER = LLMSettingsStore.ENV_PROVIDER
    ENV_MODEL = LLMSettingsStore.ENV_MODEL
    ENV_BASE_URL = LLMSettingsStore.ENV_BASE_URL
    ENV_API_KEY = LLMSettingsStore.ENV_API_KEY

    def __init__(self, store: LLMSettingsStore | None = None) -> None:
        self.store = store or LLMSettingsStore()

    @staticmethod
    def _normalize_values(payload: dict[str, Any], current: dict[str, str] | None = None) -> dict[str, str]:
        current = current or {}
        provider = str(payload.get("provider", DEFAULT_PROVIDER)).strip() or DEFAULT_PROVIDER
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        model = str(payload.get("model", "")).strip()
        base_url = str(payload.get("base_url", "")).strip()
        api_key = str(payload.get("api_key", "")).strip()
        if not api_key and current.get("api_key") and payload.get("preserve_api_key", True):
            api_key = current["api_key"]
        return {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
        }

    @staticmethod
    def _settings_from_values(values: dict[str, str]) -> LLMSettings:
        provider = values.get("provider", DEFAULT_PROVIDER).strip() or DEFAULT_PROVIDER
        if provider not in SUPPORTED_PROVIDERS:
            provider = DEFAULT_PROVIDER
        model = values.get("model", "").strip()
        base_url = values.get("base_url", "").strip()
        api_key = values.get("api_key", "").strip()
        enabled = provider == "mock" or (provider != "in_process" and bool(model and base_url))
        return LLMSettings(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key_configured=bool(api_key),
            enabled=enabled,
        )

    def get(self) -> LLMSettings:
        return self._settings_from_values(self.store.load())

    def provider_config(self) -> ProviderConfig:
        """Return runtime provider configuration with secret available only in memory."""
        values = self.store.load()
        settings = self._settings_from_values(values)
        return ProviderConfig(
            provider_type=settings.provider,
            model=settings.model or None,
            base_url=settings.base_url or None,
            api_key=values.get("api_key") or None,
            timeout=30,
            options={"temperature": 0.1, "max_tokens": 900},
        )

    def update(self, payload: dict[str, Any]) -> LLMSettings:
        values = self._normalize_values(payload, self.store.load())
        self.store.save(values)
        return self._settings_from_values(values)

    def _effective_values(self, payload: dict[str, Any] | None) -> dict[str, str]:
        if payload is None:
            return self.store.load()
        return self._normalize_values(payload, self.store.load())

    def models(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return model IDs for persisted settings or an unsaved form configuration."""
        values = self._effective_values(payload)
        settings = self._settings_from_values(values)
        if settings.provider == "mock":
            return {"ok": True, "provider": "mock", "models": ["mock"]}
        if settings.provider == "in_process":
            return {"ok": False, "provider": "in_process", "models": [], "message": "In-process provider has no HTTP model catalog."}
        if not settings.base_url:
            return {"ok": False, "provider": settings.provider, "models": [], "message": "LLM base URL is not configured."}
        headers = {"Accept": "application/json"}
        if settings.provider == "remote_api" and values.get("api_key"):
            headers["Authorization"] = f"Bearer {values['api_key']}"
        url = settings.base_url.rstrip("/") + "/models"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                payload_data = json.loads(response.read().decode("utf-8"))
            entries = payload_data.get("data", []) if isinstance(payload_data, dict) else []
            models = [str(item.get("id")) for item in entries if isinstance(item, dict) and item.get("id")]
            return {"ok": True, "provider": settings.provider, "models": models, "url": url}
        except urllib.error.HTTPError as error:
            return {"ok": False, "provider": settings.provider, "models": [], "status": error.code, "message": f"HTTP {error.code}: {error.reason}", "url": url}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            return {"ok": False, "provider": settings.provider, "models": [], "message": str(error), "url": url}

    def test_connection(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Probe persisted settings or unsaved form values without mutating storage."""
        values = self._effective_values(payload)
        settings = self._settings_from_values(values)
        if settings.provider == "mock":
            return {"ok": True, "provider": "mock", "model": settings.model, "message": "Mock provider is available."}
        if settings.provider == "in_process":
            return {"ok": False, "provider": "in_process", "message": "In-process provider requires a host model instance and cannot be tested from the GUI."}
        if not settings.base_url:
            return {"ok": False, "provider": settings.provider, "message": "LLM base URL is not configured."}
        headers = {"Accept": "application/json"}
        if settings.provider == "remote_api" and values.get("api_key"):
            headers["Authorization"] = f"Bearer {values['api_key']}"
        url = settings.base_url.rstrip("/") + "/models"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return {"ok": True, "provider": settings.provider, "model": settings.model, "status": response.status, "url": url}
        except urllib.error.HTTPError as error:
            return {"ok": False, "provider": settings.provider, "status": error.code, "message": f"HTTP {error.code}: {error.reason}", "url": url}
        except (urllib.error.URLError, TimeoutError) as error:
            return {"ok": False, "provider": settings.provider, "message": str(error), "url": url}


__all__ = ["DEFAULT_PROVIDER", "LLMSettings", "LLMSettingsService", "LLMSettingsStore", "SUPPORTED_PROVIDERS"]

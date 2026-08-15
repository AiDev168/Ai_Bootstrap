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
    enabled: bool = False
    connection_ok: bool | None = None
    connection_message: str = "Not tested yet."


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
                return {
                    str(key): str(value)
                    for key, value in data.items()
                    if value is not None
                }
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
            return {
                "provider": DEFAULT_PROVIDER,
                "model": "",
                "base_url": "",
                "api_key": "",
                "enabled": "true" if DEFAULT_PROVIDER == "mock" else "false",
            }
        return {
            "provider": provider or DEFAULT_PROVIDER,
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "enabled": "true",
        }


class LLMSettingsService:
    """Manage persistent provider settings without exposing secrets."""

    ENV_PROVIDER = LLMSettingsStore.ENV_PROVIDER
    ENV_MODEL = LLMSettingsStore.ENV_MODEL
    ENV_BASE_URL = LLMSettingsStore.ENV_BASE_URL
    ENV_API_KEY = LLMSettingsStore.ENV_API_KEY

    def __init__(self, store: LLMSettingsStore | None = None) -> None:
        self.store = store or LLMSettingsStore()
        self._last_probe: dict[str, Any] | None = None

    @staticmethod
    def _normalize_values(payload: dict[str, Any], current: dict[str, str] | None = None) -> dict[str, str]:
        current = current or {}
        provider = str(payload.get("provider", current.get("provider", DEFAULT_PROVIDER))).strip() or current.get("provider", DEFAULT_PROVIDER)
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        model = str(payload.get("model", current.get("model", ""))).strip()
        base_url = str(payload.get("base_url", current.get("base_url", ""))).strip()
        api_key = str(payload.get("api_key", "")).strip() or current.get("api_key", "")
        enabled = bool(model or base_url) and provider != "mock"
        if provider == "in_process":
            enabled = bool(model)
        if provider == "remote_api":
            enabled = bool(api_key and base_url)
        return {"provider": provider, "model": model, "base_url": base_url, "api_key": api_key, "enabled": str(enabled).lower()}

    @staticmethod
    def _fingerprint(values: dict[str, str]) -> tuple[str, str, str, bool]:
        return (values.get("provider", DEFAULT_PROVIDER), values.get("model", ""), values.get("base_url", ""), bool(values.get("api_key", "")))

    def _record_probe(self, values: dict[str, str], result: dict[str, Any]) -> dict[str, Any]:
        self._last_probe = {
            "fingerprint": self._fingerprint(values),
            "ok": bool(result.get("ok")),
            "message": str(result.get("message", "")),
        }
        return result

    def get(self) -> LLMSettings:
        values = self.store.load()
        provider = values.get("provider", DEFAULT_PROVIDER)
        model = values.get("model", "")
        base_url = values.get("base_url", "")
        api_key = values.get("api_key", "")
        enabled = values.get("enabled", "false").lower() == "true"
        probe = self._last_probe
        connection_ok = None
        connection_message = "Not tested yet."
        if probe and probe.get("fingerprint") == self._fingerprint(values):
            connection_ok = bool(probe.get("ok"))
            connection_message = str(probe.get("message", ""))
        return LLMSettings(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key_configured=bool(api_key),
            enabled=enabled,
            connection_ok=connection_ok,
            connection_message=connection_message,
        )

    def update(self, payload: dict[str, Any]) -> LLMSettings:
        current = self.store.load()
        values = self._normalize_values(payload, current)
        self.store.save(values)
        self._last_probe = None
        return self.get()

    def provider_config(self) -> ProviderConfig:
        values = self.store.load()
        return ProviderConfig(
            provider_type=values.get("provider", DEFAULT_PROVIDER),
            model=values.get("model") or None,
            base_url=values.get("base_url") or None,
            api_key=values.get("api_key") or None,
            options={
                "temperature": float(values.get("temperature", "0.1")),
                "max_tokens": int(values.get("max_tokens", "900")),
                "enable_thinking": values.get("enable_thinking", "false").lower() == "true",
            },
        )

    def test_connection(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        values = self._normalize_values(payload or {}, self.store.load())
        provider = values["provider"]
        if provider == "mock":
            return self._record_probe(
                values,
                {
                    "ok": False,
                    "provider": provider,
                    "message": "Mock provider is test-only and has no live LLM connection.",
                },
            )
        config = ProviderConfig(
            provider_type=provider,
            model=values.get("model") or None,
            base_url=values.get("base_url") or None,
            api_key=values.get("api_key") or None,
            options={},
        )
        if provider in {"local_server", "remote_api"}:
            if not config.base_url:
                raise ValueError(f"Base URL is required for {provider}")
            base_url = config.base_url.rstrip("/")
            endpoint = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"
            headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}
            request = urllib.request.Request(endpoint, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    ok = 200 <= response.status < 300
                return self._record_probe(values, {"ok": ok, "provider": provider, "url": endpoint, "message": "LLM server is reachable." if ok else "LLM server returned a non-success status."})
            except (urllib.error.URLError, urllib.error.HTTPError) as error:
                return self._record_probe(values, {"ok": False, "provider": provider, "url": endpoint, "message": f"Connection failed: {error}"})
        ok = bool(config.model)
        return self._record_probe(values, {"ok": ok, "provider": provider, "message": "Provider configuration accepted." if ok else "Model is not configured."})

    def models(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        values = self._normalize_values(payload or {}, self.store.load())
        provider = values["provider"]
        config = ProviderConfig(provider_type=provider, model=values.get("model") or None, base_url=values.get("base_url") or None, api_key=values.get("api_key") or None, options={})
        if provider == "mock":
            return {"ok": True, "provider": provider, "models": ["mock"]}
        if provider == "local_server":
            if not config.base_url:
                raise ValueError("Base URL is required for local_server")
            base_url = config.base_url.rstrip("/")
            endpoint = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"
            headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}
            request = urllib.request.Request(endpoint, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return {"ok": True, "provider": provider, "models": [item.get("id") for item in data.get("data", []) if isinstance(item, dict) and item.get("id")]}
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
                return {"ok": False, "provider": provider, "models": [], "message": f"Model discovery failed: {error}"}
        return {"ok": True, "provider": provider, "models": [config.model] if config.model else []}


__all__ = ["DEFAULT_PROVIDER", "SUPPORTED_PROVIDERS", "LLMSettings", "LLMSettingsService", "LLMSettingsStore"]

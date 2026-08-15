import json
from pathlib import Path
from urllib.request import Request

from ai_engineering_bootstrap.backend.llm_settings import (
    LLMSettingsService,
    LLMSettingsStore,
)


def test_settings_persist_across_service_instances(tmp_path: Path) -> None:
    path = tmp_path / "config" / "llm.json"
    first = LLMSettingsService(LLMSettingsStore(path))
    first.update(
        {
            "provider": "local_server",
            "model": "qwen-test",
            "base_url": "http://192.168.1.50:1234/v1",
            "api_key": "secret",
        }
    )
    second = LLMSettingsService(LLMSettingsStore(path))
    settings = second.get()
    assert settings.provider == "local_server"
    assert settings.model == "qwen-test"
    assert settings.base_url == "http://192.168.1.50:1234/v1"
    assert settings.api_key_configured is True
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["api_key"] == "secret"
    assert path.stat().st_mode & 0o077 == 0


def test_mock_is_offline(tmp_path: Path) -> None:
    service = LLMSettingsService(LLMSettingsStore(tmp_path / "llm.json"))
    service.update({"provider": "mock", "model": "", "base_url": "", "api_key": ""})
    assert service.test_connection()["ok"] is False
    assert "test-only" in service.test_connection()["message"]
    assert service.models()["models"] == ["mock"]


def test_network_provider_uses_configured_base_url(tmp_path: Path, monkeypatch) -> None:
    service = LLMSettingsService(LLMSettingsStore(tmp_path / "llm.json"))
    service.update(
        {
            "provider": "local_server",
            "model": "remote-qwen",
            "base_url": "http://192.168.10.20:1234/v1",
            "api_key": "",
        }
    )
    calls: list[str] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"data":[{"id":"remote-qwen"}]}'

    def fake_urlopen(request: Request, timeout: int):
        calls.append(request.full_url)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = service.test_connection()
    models = service.models()
    assert result["ok"] is True
    assert result["url"] == "http://192.168.10.20:1234/v1/models"
    assert models["models"] == ["remote-qwen"]
    assert calls == [
        "http://192.168.10.20:1234/v1/models",
        "http://192.168.10.20:1234/v1/models",
    ]

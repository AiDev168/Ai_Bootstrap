"""Backend contracts exercised by the GUI."""

from ai_engineering_bootstrap.backend.llm_settings import LLMSettingsService
from ai_engineering_bootstrap.backend.service import ApplicationBackend
from ai_engineering_bootstrap.environment.models import EnvironmentRequest


def test_session_endpoints_return_serializable_data() -> None:
    backend = ApplicationBackend()
    created = backend.create_session(EnvironmentRequest(natural_language_goal="prepare python ai"))
    session_id = created.data["session_id"]

    session = backend.get_session(session_id)
    state = backend.get_session_state(session_id)
    plan = backend.get_session_plan(session_id)

    assert session.data["session_id"] == session_id
    assert "request" in session.data
    assert "approval_states" in session.data
    assert state.data["session_id"] == session_id
    assert isinstance(state.data["actual"], dict)
    assert isinstance(state.data["desired"], dict)
    assert isinstance(state.data["delta"], dict)
    assert plan.data["session_id"] == session_id
    assert plan.data["status"] in {"ready", "blocked"}


def test_llm_settings_round_trip_is_secret_safe(monkeypatch) -> None:
    for name in (
        LLMSettingsService.ENV_PROVIDER,
        LLMSettingsService.ENV_MODEL,
        LLMSettingsService.ENV_BASE_URL,
        LLMSettingsService.ENV_API_KEY,
    ):
        monkeypatch.delenv(name, raising=False)
    backend = ApplicationBackend()
    result = backend.update_llm_settings(
        {
            "provider": "remote_api",
            "model": "test-model",
            "base_url": "https://example.invalid/v1",
            "api_key": "secret-value",
        }
    )

    assert result.data["provider"] == "remote_api"
    assert result.data["model"] == "test-model"
    assert result.data["api_key_configured"] is True
    assert "secret-value" not in str(result.data)
    assert backend.get_llm_settings().data["base_url"] == "https://example.invalid/v1"


def test_supported_llm_provider_modes_are_exposed(monkeypatch) -> None:
    for name in (
        LLMSettingsService.ENV_PROVIDER,
        LLMSettingsService.ENV_MODEL,
        LLMSettingsService.ENV_BASE_URL,
        LLMSettingsService.ENV_API_KEY,
    ):
        monkeypatch.delenv(name, raising=False)
    backend = ApplicationBackend()
    for provider in ("local_server", "remote_api", "mock", "in_process"):
        result = backend.update_llm_settings({"provider": provider, "model": "test-model", "base_url": "http://127.0.0.1:1234/v1"})
        assert result.data["provider"] == provider

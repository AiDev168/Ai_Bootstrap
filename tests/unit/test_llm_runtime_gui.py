from pathlib import Path

from ai_engineering_bootstrap.backend.llm_settings import LLMSettingsService
from ai_engineering_bootstrap.backend.service import ApplicationBackend
from ai_engineering_bootstrap.backend.strategy_planner_runtime import RuntimeStrategyPlanner

HTML_PATH = Path(__file__).resolve().parents[2] / "src/ai_engineering_bootstrap/gui/static/index.html"


def test_mock_provider_connection_is_offline() -> None:
    service = LLMSettingsService()
    service.update({"provider": "mock", "model": "", "base_url": "", "api_key": ""})
    result = service.test_connection()
    assert result["ok"] is True
    assert result["provider"] == "mock"


def test_application_backend_uses_runtime_strategy_planner() -> None:
    backend = ApplicationBackend()
    assert isinstance(backend._session_service._strategy_planner, RuntimeStrategyPlanner)


def test_gui_exposes_provider_choices_and_operational_session_controls() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    for text in (
        'value="mock"',
        'value="local_server"',
        'value="remote_api"',
        'value="in_process"',
        "data-open",
        "viewSession",
        "logRequest",
        "startPolling",
    ):
        assert text in html

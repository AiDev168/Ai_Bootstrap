from pathlib import Path

from ai_engineering_bootstrap.backend.llm_settings import LLMSettingsService
from ai_engineering_bootstrap.backend.service import ApplicationBackend
from ai_engineering_bootstrap.backend.strategy_planner_runtime import RuntimeStrategyPlanner
from ai_engineering_bootstrap.environment.models import DeltaAction, EnvironmentDelta, ToolDelta, ToolRequirement, ToolStatus

HTML_PATH = Path(__file__).resolve().parents[2] / "src/ai_engineering_bootstrap/gui/static/index.html"


def test_mock_provider_connection_is_offline() -> None:
    service = LLMSettingsService()
    service.update({"provider": "mock", "model": "", "base_url": "", "api_key": ""})
    result = service.test_connection()
    assert result["ok"] is True
    assert result["provider"] == "mock"


def test_mock_provider_drives_strategy_planning() -> None:
    service = LLMSettingsService()
    service.update({"provider": "mock", "model": "", "base_url": "", "api_key": ""})
    planner = RuntimeStrategyPlanner(settings_service=service)
    delta = EnvironmentDelta(
        tool_deltas=[
            ToolDelta(
                tool_id="cursor",
                action=DeltaAction.INSTALL,
                desired_requirement=ToolRequirement(tool_id="cursor"),
                actual_status=ToolStatus(tool_id="cursor", status="missing"),
            )
        ]
    )
    plan = planner.plan_strategies(delta, platform="linux", architecture="x86_64")
    assert plan.reasoning_summary.startswith("LLM-selected")
    assert plan.decisions[0].tool_id == "cursor"
    assert plan.decisions[0].strategy_name == "deb_install"


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

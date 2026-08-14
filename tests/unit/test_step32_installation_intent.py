import json
from pathlib import Path
from urllib.request import Request

from ai_engineering_bootstrap.agent.intent_parser import IntentParser
from ai_engineering_bootstrap.agent.provider import LocalServerProvider, ProviderConfig
from ai_engineering_bootstrap.agent.strategy_llm_bridge import StrategyLLMProvider
from ai_engineering_bootstrap.backend.llm_settings import (
    LLMSettingsService,
    LLMSettingsStore,
)
from ai_engineering_bootstrap.environment.models import (
    ActualEnvironmentState,
    DeltaAction,
    EnvironmentRequest,
    ToolStatus,
)
from ai_engineering_bootstrap.environment.reconciler import EnvironmentReconciler
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog

HTML_PATH = (
    Path(__file__).resolve().parents[1]
    / "../src/ai_engineering_bootstrap/gui/static/index.html"
)
RUNTIME_PATH = (
    Path(__file__).resolve().parents[1]
    / "../src/ai_engineering_bootstrap/gui/static/app-runtime.js"
)


def test_force_install_is_encoded_in_desired_state() -> None:
    request = EnvironmentRequest(
        required_tools=["ruff"], constraints={"force_install": True}
    )
    desired = request.to_desired_state()
    assert desired.tools["ruff"].configuration["force_install"] is True


def test_reconciler_creates_install_delta_for_explicit_repair() -> None:
    request = EnvironmentRequest(
        required_tools=["ruff"], constraints={"force_install": True}
    )
    desired = request.to_desired_state()
    actual = ActualEnvironmentState(
        tools={
            "ruff": ToolStatus(
                tool_id="ruff", status="installed", version="0.12.0", health="healthy"
            )
        }
    )
    delta = EnvironmentReconciler().reconcile(actual, desired)
    assert len(delta.tool_deltas) == 1
    assert delta.tool_deltas[0].action == DeltaAction.INSTALL
    assert delta.tool_deltas[0].tool_id == "ruff"


def test_local_server_api_key_is_accepted(tmp_path, monkeypatch) -> None:
    service = LLMSettingsService(LLMSettingsStore(tmp_path / "llm.json"))
    calls: list[Request] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request: Request, timeout: int):
        calls.append(request)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = service.test_connection(
        {
            "provider": "local_server",
            "model": "qwen-test",
            "base_url": "http://192.168.1.50:1234/v1",
            "api_key": "lm-secret",
        }
    )
    assert result["ok"] is True
    assert calls[0].full_url == "http://192.168.1.50:1234/v1/models"
    assert calls[0].headers["Authorization"] == "Bearer lm-secret"


def test_local_server_strategy_passes_api_key(monkeypatch) -> None:
    calls: list[Request] = []
    response_payload = {
        "choices": [
            {"message": {"content": json.dumps({"strategies": [], "confidence": 0.9})}}
        ]
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(response_payload).encode()

    def fake_urlopen(request: Request, timeout: int):
        calls.append(request)
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = LocalServerProvider(
        ProviderConfig(
            provider_type="local_server",
            model="qwen-test",
            base_url="http://192.168.1.50:1234/v1",
            api_key="lm-secret",
        )
    )
    result = StrategyLLMProvider(provider).decide("- ruff: install", [])
    assert result.confidence == 0.9
    assert calls[0].full_url == "http://192.168.1.50:1234/v1/chat/completions"
    assert calls[0].headers["Authorization"] == "Bearer lm-secret"


def test_deterministic_parser_handles_english_exclusion_and_multiple_targets() -> None:
    parsed = IntentParser(tool_catalog=ToolCatalog()).parse(
        "install Ruff, pytest and Cursor but don't install Docker"
    )

    assert {"ruff", "pytest", "cursor"}.issubset(set(parsed.required_tools))
    assert "docker" in parsed.excluded_tools
    assert "docker" not in parsed.required_tools


def test_deterministic_parser_handles_persian_install_request() -> None:
    parsed = IntentParser(tool_catalog=ToolCatalog()).parse(
        "روف و پای‌تست را نصب کن و داکر را نصب نکن"
    )

    assert {"ruff", "pytest"}.issubset(set(parsed.required_tools))
    assert "docker" in parsed.excluded_tools
    assert "docker" not in parsed.required_tools


def test_gui_supports_install_intent_and_editable_api_key() -> None:
    html = HTML_PATH.resolve().read_text(encoding="utf-8")
    runtime = RUNTIME_PATH.resolve().read_text(encoding="utf-8")
    assert 'id="api-key"' in html
    assert 'id="force-install"' not in html
    assert "apiKeyInput.disabled = false" in runtime
    assert "Install / repair selected tools" in runtime
    assert "constraints: forceInstall ? { force_install: true } : {}" in runtime
    assert '.filter(input => input.id !== "force-install")' in runtime

from types import SimpleNamespace

from ai_engineering_bootstrap.agent.intent_parser import IntentParser
from ai_engineering_bootstrap.backend.runtime_session_service import RuntimeSessionService
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.session_repository import InMemorySessionRepository
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog


def test_natural_language_goal_populates_required_tools() -> None:
    service = RuntimeSessionService(
        repository=InMemorySessionRepository(),
        audit_factory=lambda: SimpleNamespace(checks=[]),
        intent_parser_factory=lambda: IntentParser(tool_catalog=ToolCatalog()),
    )
    result = service.create(EnvironmentRequest(natural_language_goal="install Cursor and Ruff"))
    session = service.get(result.data["session_id"])

    assert set(session.request.required_tools) == {"cursor", "ruff"}
    assert any(decision.decision_type == "intent_parsing" for decision in session.agent_decisions)
    assert any(event.event_type == "intent_parsed" for event in session.events)


def test_force_install_goal_produces_install_delta() -> None:
    service = RuntimeSessionService(
        repository=InMemorySessionRepository(),
        audit_factory=lambda: SimpleNamespace(checks=[]),
        intent_parser_factory=lambda: IntentParser(tool_catalog=ToolCatalog()),
    )
    request = EnvironmentRequest(
        natural_language_goal="reinstall Ruff",
        required_tools=["ruff"],
        constraints={"force_install": True},
    )
    result = service.create(request)
    session = service.get(result.data["session_id"])

    assert session.delta.tool_deltas[0].tool_id == "ruff"
    assert session.delta.tool_deltas[0].action.value == "install"

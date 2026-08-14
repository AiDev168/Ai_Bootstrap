import json
from types import SimpleNamespace

from ai_engineering_bootstrap.agent.intent_parser import IntentParser
from ai_engineering_bootstrap.agent.provider import InProcessProvider, ProviderConfig
from ai_engineering_bootstrap.backend.runtime_session_service import (
    RuntimeSessionService,
)
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.session_repository import (
    InMemorySessionRepository,
)
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog
from ai_engineering_bootstrap.executor.mode import ExecutionMode


class FakeModel:
    def generate(self, prompt: str) -> str:
        return json.dumps(
            {
                "natural_language_goal": "install pytest and colorama and ruff",
                "required_tools": ["ruff", "pytest"],
                "optional_tools": [],
                "languages": [],
                "frameworks": [],
                "project_dependencies": ["colorama"],
                "constraints": [],
                "platform_preferences": [],
            }
        )


def _audit_factory():
    return SimpleNamespace(run=lambda: SimpleNamespace(checks=[]))


def _intent_parser() -> IntentParser:
    provider = InProcessProvider(
        ProviderConfig(
            provider_type="in_process", options={"model_instance": FakeModel()}
        )
    )
    return IntentParser(provider=provider, tool_catalog=ToolCatalog())


def test_natural_language_install_goal_builds_tool_and_package_actions() -> None:
    service = RuntimeSessionService(
        repository=InMemorySessionRepository(),
        audit_factory=_audit_factory,
        intent_parser_factory=_intent_parser,
    )
    result = service.create(
        EnvironmentRequest(natural_language_goal="install pytest and colorama and ruff")
    )
    session_id = result.data["session_id"]
    plan = service.plan(session_id).data["plan"]
    action_ids = [action["action_id"] for action in plan["actions"]]

    assert action_ids == [
        "install_python_package:ruff",
        "install_python_package:pytest",
        "install_python_package:colorama",
    ]
    session = service.get(session_id)
    assert any(decision.provider == "llm" for decision in session.agent_decisions)
    assert all(
        action_id.startswith("install_python_package:") for action_id in action_ids
    )


def test_real_start_waits_for_each_action_instance_approval() -> None:
    service = RuntimeSessionService(
        repository=InMemorySessionRepository(),
        audit_factory=_audit_factory,
        intent_parser_factory=lambda: IntentParser(tool_catalog=ToolCatalog()),
    )
    result = service.create(
        EnvironmentRequest(
            required_tools=["ruff", "pytest"], constraints={"force_install": True}
        )
    )
    session_id = result.data["session_id"]
    actions = service.plan(session_id).data["plan"]["actions"]

    service.approve(session_id, actions[0]["action_id"])
    try:
        service.start(session_id, ExecutionMode.REAL)
    except ValueError as error:
        assert actions[1]["action_id"] in str(error)
        assert actions[0]["action_id"] not in str(error)
    else:
        raise AssertionError(
            "REAL execution should wait for unapproved action instances"
        )

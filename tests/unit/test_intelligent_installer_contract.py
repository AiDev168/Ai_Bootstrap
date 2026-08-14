from types import SimpleNamespace

from ai_engineering_bootstrap.agent.intent_parser import IntentParser
from ai_engineering_bootstrap.backend.runtime_session_service import (
    RuntimeSessionService,
)
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.session_repository import (
    InMemorySessionRepository,
)
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.policy import SafetyGate
from ai_engineering_bootstrap.executor.registry import ActionRegistry


def _audit_factory():
    return SimpleNamespace(run=lambda: SimpleNamespace(checks=[]))


def _session_for_goal(goal: str):
    service = RuntimeSessionService(
        repository=InMemorySessionRepository(),
        audit_factory=_audit_factory,
        intent_parser_factory=lambda: IntentParser(tool_catalog=ToolCatalog()),
    )
    result = service.create(EnvironmentRequest(natural_language_goal=goal))
    return service.get(result.data["session_id"])


def test_negative_english_package_is_excluded() -> None:
    session = _session_for_goal("don't install colorama, but install ruff and pytest")

    assert "ruff" in session.request.required_tools
    assert "pytest" in session.request.required_tools
    assert "colorama" in session.request.excluded_packages
    assert "colorama" not in [item.name for item in session.request.project_dependencies]


def test_negative_persian_package_is_excluded() -> None:
    session = _session_for_goal("روف و پایتست را نصب کن ولی colorama را نصب نکن")

    assert "ruff" in session.request.required_tools
    assert "pytest" in session.request.required_tools
    assert "colorama" in session.request.excluded_packages
    assert "colorama" not in [item.name for item in session.request.project_dependencies]


def test_multiple_install_targets_are_preserved() -> None:
    session = _session_for_goal("install ruff, pytest, black and colorama")

    assert {"ruff", "pytest", "black"}.issubset(set(session.request.required_tools))
    assert "colorama" in [item.name for item in session.request.project_dependencies]


def test_instance_action_ids_resolve_to_distinct_canonical_handlers() -> None:
    registry = ActionRegistry()
    ruff_handler = registry.get_handler(
        "install_python_package:ruff", ExecutionMode.SAFE
    )
    pytest_handler = registry.get_handler(
        "install_python_package:pytest", ExecutionMode.SAFE
    )

    assert ruff_handler is pytest_handler
    assert (
        registry.canonical_action_id("install_python_package:ruff")
        == "install_python_package"
    )
    assert (
        registry.canonical_action_id("install_python_package:pytest")
        == "install_python_package"
    )


def test_instance_action_policies_are_independently_addressable() -> None:
    gate = SafetyGate()

    denied_ruff, _ = gate.evaluate(
        "install_python_package:ruff", ExecutionMode.REAL, is_approved=False
    )
    allowed_ruff, _ = gate.evaluate(
        "install_python_package:ruff", ExecutionMode.REAL, is_approved=True
    )
    denied_pytest, _ = gate.evaluate(
        "install_python_package:pytest", ExecutionMode.REAL, is_approved=False
    )

    assert denied_ruff is False
    assert allowed_ruff is True
    assert denied_pytest is False

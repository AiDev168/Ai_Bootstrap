from types import SimpleNamespace

from ai_engineering_bootstrap.backend.runtime_session_service import RuntimeSessionService
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.session_repository import InMemorySessionRepository


def _audit_factory():
    return SimpleNamespace(run=lambda: SimpleNamespace(checks=[]))


def test_package_actions_have_unique_ids_and_independent_approval() -> None:
    service = RuntimeSessionService(
        repository=InMemorySessionRepository(),
        audit_factory=_audit_factory,
    )
    result = service.create(
        EnvironmentRequest(
            required_tools=["ruff", "pytest"],
            constraints={"force_install": True},
        )
    )
    session_id = result.data["session_id"]
    plan = service.plan(session_id).data["plan"]
    action_ids = [action["action_id"] for action in plan["actions"]]

    assert action_ids == ["install_python_package:ruff", "install_python_package:pytest"]

    service.approve(session_id, action_ids[0])
    service.skip(session_id, action_ids[1])
    session = service.get(session_id)

    assert session.approval_states[action_ids[0]].status == "approved"
    assert session.approval_states[action_ids[1]].status == "skipped"


def test_real_start_executes_only_approved_action_instances() -> None:
    captured: dict[str, object] = {}

    class FakeBootstrap:
        def run(self, **kwargs):
            captured["actions"] = [action.action_id for action in kwargs["plan_override"].actions]
            return SimpleNamespace(
                is_success=True,
                environment_ready=True,
                rejected_actions=[],
                action_results=[],
            )

    service = RuntimeSessionService(
        repository=InMemorySessionRepository(),
        audit_factory=_audit_factory,
        bootstrap_factory=lambda: FakeBootstrap(),
    )
    result = service.create(
        EnvironmentRequest(
            required_tools=["ruff", "pytest"],
            constraints={"force_install": True},
        )
    )
    session_id = result.data["session_id"]
    actions = service.plan(session_id).data["plan"]["actions"]
    service.approve(session_id, actions[0]["action_id"])
    service.skip(session_id, actions[1]["action_id"])

    result = service.start(session_id, mode=__import__("ai_engineering_bootstrap.executor.mode", fromlist=["ExecutionMode"]).ExecutionMode.REAL)

    assert result.data["status"] == "completed"
    assert captured["actions"] == ["install_python_package:ruff"]

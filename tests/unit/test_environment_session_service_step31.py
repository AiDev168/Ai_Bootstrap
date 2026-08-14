"""Step 31 environment session orchestration tests."""

from types import SimpleNamespace

from ai_engineering_bootstrap.backend.session_service import EnvironmentSessionService
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.session_repository import (
    InMemorySessionRepository,
)


class FakeAuditService:
    def run(self):
        return SimpleNamespace(
            checks=[],
            readiness=SimpleNamespace(
                development_ready=True,
                production_ready=True,
                passed_count=0,
                failed_count=0,
                warning_count=0,
                health_score=100,
            ),
        )


def test_create_session_persists_desired_and_actual_state() -> None:
    repository = InMemorySessionRepository()
    service = EnvironmentSessionService(
        repository=repository,
        audit_factory=FakeAuditService,
    )
    request = EnvironmentRequest(
        project_path=".",
        natural_language_goal="Prepare Python tooling",
        required_tools=["ruff"],
    )

    result = service.create(request)
    session_id = result.data["session_id"]
    session = repository.get(session_id)

    assert session is not None
    assert session.request is request
    assert session.desired_state is not None
    assert session.actual_state is not None
    assert session.delta is not None
    assert session.events[0].event_type == "session_created"


def test_approval_targets_only_existing_plan_action() -> None:
    repository = InMemorySessionRepository()
    service = EnvironmentSessionService(
        repository=repository,
        audit_factory=FakeAuditService,
    )
    request = EnvironmentRequest(project_path=".", required_tools=[])
    session = service.create(request).data["session_id"]

    service.get(session)

    try:
        service.approve(session, "install_cursor")
    except ValueError as exc:
        assert "no execution plan" in str(exc)
    else:
        raise AssertionError("approval must fail closed before a plan exists")

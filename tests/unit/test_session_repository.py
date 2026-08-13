"""Tests for the session repository boundary."""

from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.session_models import EnvironmentSession
from ai_engineering_bootstrap.environment.session_repository import (
    InMemorySessionRepository,
)


def test_round_trip_preserves_identity() -> None:
    repo = InMemorySessionRepository()
    session = EnvironmentSession(request=EnvironmentRequest(natural_language_goal="install cursor"))
    created = repo.create(session)
    loaded = repo.get(session.session_id)
    assert loaded is created
    assert loaded is not None


def test_list_is_newest_first() -> None:
    repo = InMemorySessionRepository()
    first = repo.create(EnvironmentSession(request=EnvironmentRequest(natural_language_goal="first")))
    second = repo.create(EnvironmentSession(request=EnvironmentRequest(natural_language_goal="second")))
    assert [item.session_id for item in repo.list()] == [second.session_id, first.session_id]


def test_duplicate_creation_is_rejected() -> None:
    repo = InMemorySessionRepository()
    session = EnvironmentSession()
    repo.create(session)
    try:
        repo.create(session)
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("duplicate session creation unexpectedly succeeded")

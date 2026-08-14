"""Thread-safe session repository boundary for API services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock

from ai_engineering_bootstrap.environment.session_models import (
    EnvironmentSession,
    SessionStatus,
)


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class SessionRepository:
    """Repository contract for environment sessions."""

    def create(self, session: EnvironmentSession) -> EnvironmentSession:
        raise NotImplementedError

    def get(self, session_id: str) -> EnvironmentSession | None:
        raise NotImplementedError

    def update(self, session: EnvironmentSession) -> EnvironmentSession:
        raise NotImplementedError

    def list(self, status: SessionStatus | None = None) -> list[EnvironmentSession]:
        raise NotImplementedError

    def delete(self, session_id: str) -> bool:
        raise NotImplementedError


@dataclass
class InMemorySessionRepository(SessionRepository):
    """Thread-safe in-memory repository suitable for the API MVP and tests."""

    _sessions: dict[str, EnvironmentSession] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def create(self, session: EnvironmentSession) -> EnvironmentSession:
        with self._lock:
            if session.session_id in self._sessions:
                raise ValueError(f"Session {session.session_id} already exists")
            session.updated_at = utcnow()
            self._sessions[session.session_id] = session
            return session

    def get(self, session_id: str) -> EnvironmentSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def update(self, session: EnvironmentSession) -> EnvironmentSession:
        with self._lock:
            if session.session_id not in self._sessions:
                raise ValueError(f"Session {session.session_id} does not exist")
            session.updated_at = utcnow()
            self._sessions[session.session_id] = session
            return session

    def list(self, status: SessionStatus | None = None) -> list[EnvironmentSession]:
        with self._lock:
            sessions = list(self._sessions.values())
            if status is not None:
                sessions = [session for session in sessions if session.status == status]
            return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


__all__ = ["InMemorySessionRepository", "SessionRepository", "utcnow"]

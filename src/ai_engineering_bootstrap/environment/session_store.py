"""
Session store abstraction for environment sessions.

Provides a simple in-memory store with optional JSON persistence for MVP.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from .session_models import EnvironmentSession, SessionStatus


class SessionStore:
    """
    Abstract base class for session storage.
    
    Implementations can be in-memory, file-based, or database-backed.
    """
    
    def create(self, session: EnvironmentSession) -> EnvironmentSession:
        """Create a new session."""
        raise NotImplementedError
    
    def get(self, session_id: str) -> EnvironmentSession | None:
        """Get a session by ID."""
        raise NotImplementedError
    
    def update(self, session: EnvironmentSession) -> EnvironmentSession:
        """Update an existing session."""
        raise NotImplementedError
    
    def append_event(self, session_id: str, event_data: dict) -> EnvironmentSession:
        """Append an event to a session's timeline."""
        raise NotImplementedError
    
    def list_sessions(self, status_filter: SessionStatus | None = None) -> list[EnvironmentSession]:
        """List all sessions, optionally filtered by status."""
        raise NotImplementedError
    
    def list_all(self) -> list[EnvironmentSession]:
        """List all sessions (alias for list_sessions)."""
        return self.list_sessions()
    
    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """Simple in-memory session store for development and testing."""
    
    def __init__(self):
        self._sessions: dict[str, EnvironmentSession] = {}
    
    def create(self, session: EnvironmentSession) -> EnvironmentSession:
        if session.session_id in self._sessions:
            raise ValueError(f"Session {session.session_id} already exists")
        self._sessions[session.session_id] = session
        return session
    
    def get(self, session_id: str) -> EnvironmentSession | None:
        return self._sessions.get(session_id)
    
    def update(self, session: EnvironmentSession) -> EnvironmentSession:
        if session.session_id not in self._sessions:
            raise ValueError(f"Session {session.session_id} does not exist")
        session.updated_at = datetime.now(UTC)
        self._sessions[session.session_id] = session
        return session
    
    def append_event(self, session_id: str, event_data: dict) -> EnvironmentSession:
        session = self.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist")
        
        from .session_models import SessionEvent
        
        event = SessionEvent(
            event_type=event_data.get("event_type", ""),
            message=event_data.get("message", ""),
            details=event_data.get("details", {}),
        )
        session.events.append(event)
        session.updated_at = datetime.now(UTC)
        self.update(session)
        return session
    
    def list_sessions(self, status_filter: SessionStatus | None = None) -> list[EnvironmentSession]:
        sessions = list(self._sessions.values())
        if status_filter:
            sessions = [s for s in sessions if s.status == status_filter]
        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions
    
    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


class JSONSessionStore(SessionStore):
    """File-based session store with JSON persistence."""
    
    def __init__(self, storage_path: str | Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, str] = {}  # session_id -> filename mapping
        self._load_index()
    
    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.storage_path / f"{session_id}.json"
    
    def _load_index(self) -> None:
        """Load the session index from disk."""
        index_file = self.storage_path / "index.json"
        if index_file.exists():
            with open(index_file, "r") as f:
                data = json.load(f)
                self._index = data.get("sessions", {})
    
    def _save_index(self) -> None:
        """Save the session index to disk."""
        index_file = self.storage_path / "index.json"
        with open(index_file, "w") as f:
            json.dump({"sessions": self._index}, f, indent=2)
    
    def create(self, session: EnvironmentSession) -> EnvironmentSession:
        if session.session_id in self._index:
            raise ValueError(f"Session {session.session_id} already exists")
        
        file_path = self._get_session_file(session.session_id)
        with open(file_path, "w") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
        
        self._index[session.session_id] = file_path.name
        self._save_index()
        return session
    
    def get(self, session_id: str) -> EnvironmentSession | None:
        if session_id not in self._index:
            return None
        
        file_path = self._get_session_file(session_id)
        if not file_path.exists():
            return None
        
        with open(file_path, "r") as f:
            data = json.load(f)
        
        return self._dict_to_session(data)
    
    def _dict_to_session(self, data: dict) -> EnvironmentSession:
        """Convert a dictionary back to an EnvironmentSession."""
        from .models import (
            EnvironmentRequest,
        )
        
        session = EnvironmentSession(
            session_id=data["session_id"],
            status=SessionStatus(data["status"]),
            current_action=data.get("current_action"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(UTC),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(UTC),
        )
        
        if data.get("completed_at"):
            session.completed_at = datetime.fromisoformat(data["completed_at"])
        
        # Reconstruct nested objects (simplified - full reconstruction would need more logic)
        if data.get("request"):
            session.request = EnvironmentRequest(**data["request"])
        
        if data.get("approval_states"):
            from .session_models import ActionApprovalState
            for action_id, state_data in data["approval_states"].items():
                session.approval_states[action_id] = ActionApprovalState(**state_data)
        
        if data.get("events"):
            from .session_models import SessionEvent
            for event_data in data["events"]:
                session.events.append(SessionEvent(**event_data))
        
        if data.get("agent_decisions"):
            from .session_models import AgentDecision
            for decision_data in data["agent_decisions"]:
                session.agent_decisions.append(AgentDecision(**decision_data))
        
        return session
    
    def update(self, session: EnvironmentSession) -> EnvironmentSession:
        if session.session_id not in self._index:
            raise ValueError(f"Session {session.session_id} does not exist")
        
        session.updated_at = datetime.now(UTC)
        file_path = self._get_session_file(session.session_id)
        with open(file_path, "w") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
        
        return session
    
    def append_event(self, session_id: str, event_data: dict) -> EnvironmentSession:
        session = self.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist")
        
        from .session_models import SessionEvent
        
        event = SessionEvent(
            event_type=event_data.get("event_type", ""),
            message=event_data.get("message", ""),
            details=event_data.get("details", {}),
        )
        session.events.append(event)
        return self.update(session)
    
    def list_sessions(self, status_filter: SessionStatus | None = None) -> list[EnvironmentSession]:
        sessions = []
        for session_id in self._index:
            session = self.get(session_id)
            if session and (status_filter is None or session.status == status_filter):
                    sessions.append(session)
        
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions
    
    def delete(self, session_id: str) -> bool:
        if session_id not in self._index:
            return False
        
        file_path = self._get_session_file(session_id)
        if file_path.exists():
            file_path.unlink()
        
        del self._index[session_id]
        self._save_index()
        return True


# Global default store instance (in-memory for MVP)
_default_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get the default session store instance."""
    global _default_store
    if _default_store is None:
        _default_store = InMemorySessionStore()
    return _default_store


def set_session_store(store: SessionStore) -> None:
    """Set the default session store instance."""
    global _default_store
    _default_store = store


class SessionStore:
    """
    Concrete session store class that uses the default store.
    
    This is a convenience wrapper around get_session_store() for easier use in service code.
    """
    
    def __init__(self):
        self._store = get_session_store()
    
    def create(self, request) -> EnvironmentSession:
        """Create a new session from a request."""
        from .session_models import EnvironmentSession
        session = EnvironmentSession(request=request)
        return self._store.create(session)
    
    def get(self, session_id: str) -> EnvironmentSession | None:
        """Get a session by ID."""
        return self._store.get(session_id)
    
    def update(self, session_id: str, updates: dict) -> EnvironmentSession:
        """Update an existing session with the given fields."""
        session = self._store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist")
        
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        return self._store.update(session)
    
    def append_event(self, session_id: str, event_data: dict) -> EnvironmentSession:
        """Append an event to a session's timeline."""
        return self._store.append_event(session_id, event_data)
    
    def list_all(self) -> list[EnvironmentSession]:
        """List all sessions."""
        return self._store.list_sessions()
    
    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        return self._store.delete(session_id)

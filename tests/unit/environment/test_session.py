"""Tests for session models and session store."""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

from ai_engineering_bootstrap.environment import (
    EnvironmentSession,
    SessionStatus,
    AgentDecision,
    SessionEvent,
    ActionApprovalState,
    ExecutionEvidence,
    RecoveryRecord,
    EnvironmentRequest,
    InMemorySessionStore,
    JSONSessionStore,
    get_session_store,
    set_session_store,
)


class TestEnvironmentSession:
    """Test EnvironmentSession model."""
    
    def test_create_session(self):
        """Test creating a basic session."""
        session = EnvironmentSession()
        
        assert session.session_id is not None
        assert session.status == SessionStatus.CREATED
        assert session.request is None
        assert session.plan is None
        assert len(session.events) == 0
        assert len(session.agent_decisions) == 0
    
    def test_session_with_request(self):
        """Test creating a session with an environment request."""
        request = EnvironmentRequest(
            project_path="/tmp/test-project",
            natural_language_goal="Set up Python AI environment",
            required_tools=["python", "git"],
            optional_tools=["docker"],
        )
        
        session = EnvironmentSession(request=request)
        
        assert session.request is not None
        assert session.request.project_path == "/tmp/test-project"
        assert session.request.natural_language_goal == "Set up Python AI environment"
    
    def test_add_event(self):
        """Test adding events to session timeline."""
        session = EnvironmentSession()
        
        event = session.add_event("audit_started", "Starting audit process")
        
        assert len(session.events) == 1
        assert event.event_type == "audit_started"
        assert event.message == "Starting audit process"
        assert event.timestamp is not None
    
    def test_add_event_with_details(self):
        """Test adding event with details."""
        session = EnvironmentSession()
        
        event = session.add_event(
            "plan_created",
            "Execution plan created",
            {"action_count": 5, "estimated_duration": "10m"}
        )
        
        assert len(session.events) == 1
        assert event.details["action_count"] == 5
        assert event.details["estimated_duration"] == "10m"
    
    def test_add_agent_decision(self):
        """Test recording agent decisions."""
        session = EnvironmentSession()
        
        decision = AgentDecision(
            provider="LM Studio",
            model="qwen-2.5-7b",
            decision_type="strategy_selection",
            reasoning_summary="Official DEB artifact available",
            confidence=0.94,
            selected_capabilities=["install_cursor"],
        )
        
        session.add_agent_decision(decision)
        
        assert len(session.agent_decisions) == 1
        assert session.agent_decisions[0].provider == "LM Studio"
        assert session.agent_decisions[0].session_id == session.session_id
    
    def test_approval_states(self):
        """Test action approval state management."""
        session = EnvironmentSession()
        
        # Initially no approval states
        assert session.get_approval_state("action1") is None
        
        # Set approval state
        session.set_approval_state("action1", "approved")
        state = session.get_approval_state("action1")
        
        assert state is not None
        assert state.status == "approved"
        assert state.approved_at is not None
        assert state.approved_by == "user"
    
    def test_reject_action_with_reason(self):
        """Test rejecting an action with a reason."""
        session = EnvironmentSession()
        
        session.set_approval_state("action1", "rejected", rejection_reason="Security concern")
        state = session.get_approval_state("action1")
        
        assert state.status == "rejected"
        assert state.rejection_reason == "Security concern"
    
    def test_skip_action(self):
        """Test skipping an action."""
        session = EnvironmentSession()
        
        session.set_approval_state("action1", "skipped")
        state = session.get_approval_state("action1")
        
        assert state.status == "skipped"
    
    def test_add_execution_evidence(self):
        """Test adding execution evidence."""
        session = EnvironmentSession()
        
        evidence = ExecutionEvidence(
            action_id="install_cursor",
            success=True,
            output="Cursor installed successfully",
            verification_result={"version": "3.15.6"},
        )
        
        session.add_execution_evidence(evidence)
        
        assert len(session.execution_history) == 1
        assert session.execution_history[0].success is True
    
    def test_add_recovery_record(self):
        """Test adding recovery records."""
        session = EnvironmentSession()
        
        record = RecoveryRecord(
            failure_action_id="install_docker",
            diagnosis="Docker repository key missing",
            recovery_strategy="Add official Docker GPG key",
            approved=False,
        )
        
        session.add_recovery_record(record)
        
        assert len(session.recovery_history) == 1
        assert session.recovery_history[0].diagnosis == "Docker repository key missing"
    
    def test_session_to_dict(self):
        """Test serializing session to dictionary."""
        request = EnvironmentRequest(
            project_path="/tmp/test",
            natural_language_goal="Test",
            required_tools=["python"],
        )
        
        session = EnvironmentSession(request=request)
        session.add_event("test_event", "Test message")
        
        data = session.to_dict()
        
        assert data["session_id"] == session.session_id
        assert data["status"] == "created"
        assert data["request"] is not None
        assert len(data["events"]) == 1


class TestInMemorySessionStore:
    """Test InMemorySessionStore implementation."""
    
    def test_create_session(self):
        """Test creating a session in the store."""
        store = InMemorySessionStore()
        session = EnvironmentSession()
        
        result = store.create(session)
        
        assert result.session_id == session.session_id
        assert store.get(session.session_id) is not None
    
    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        store = InMemorySessionStore()
        
        result = store.get("nonexistent-id")
        
        assert result is None
    
    def test_update_session(self):
        """Test updating a session."""
        store = InMemorySessionStore()
        session = EnvironmentSession()
        store.create(session)
        
        session.add_event("test", "Test event")
        result = store.update(session)
        
        assert len(result.events) == 1
    
    def test_list_sessions(self):
        """Test listing all sessions."""
        store = InMemorySessionStore()
        
        session1 = EnvironmentSession()
        session2 = EnvironmentSession()
        session3 = EnvironmentSession()
        
        store.create(session1)
        store.create(session2)
        store.create(session3)
        
        sessions = store.list_sessions()
        
        assert len(sessions) == 3
    
    def test_list_sessions_with_status_filter(self):
        """Test listing sessions filtered by status."""
        store = InMemorySessionStore()
        
        session1 = EnvironmentSession()
        session2 = EnvironmentSession()
        session2.status = SessionStatus.COMPLETED
        
        store.create(session1)
        store.create(session2)
        
        all_sessions = store.list_sessions()
        completed_sessions = store.list_sessions(SessionStatus.COMPLETED)
        
        assert len(all_sessions) == 2
        assert len(completed_sessions) == 1
    
    def test_delete_session(self):
        """Test deleting a session."""
        store = InMemorySessionStore()
        session = EnvironmentSession()
        store.create(session)
        
        result = store.delete(session.session_id)
        
        assert result is True
        assert store.get(session.session_id) is None
    
    def test_delete_nonexistent_session(self):
        """Test deleting a session that doesn't exist."""
        store = InMemorySessionStore()
        
        result = store.delete("nonexistent-id")
        
        assert result is False
    
    def test_append_event(self):
        """Test appending an event to a session."""
        store = InMemorySessionStore()
        session = EnvironmentSession()
        store.create(session)
        
        store.append_event(
            session.session_id,
            {
                "event_type": "test_event",
                "message": "Test message",
                "details": {"key": "value"},
            }
        )
        
        updated_session = store.get(session.session_id)
        assert len(updated_session.events) == 1
        assert updated_session.events[0].event_type == "test_event"


class TestJSONSessionStore:
    """Test JSONSessionStore implementation."""
    
    def test_create_and_persist_session(self):
        """Test creating a session with JSON persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONSessionStore(tmpdir)
            session = EnvironmentSession()
            
            store.create(session)
            
            # Verify file exists
            session_file = Path(tmpdir) / f"{session.session_id}.json"
            assert session_file.exists()
            
            # Verify index exists
            index_file = Path(tmpdir) / "index.json"
            assert index_file.exists()
    
    def test_get_session_from_disk(self):
        """Test retrieving a session from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONSessionStore(tmpdir)
            session = EnvironmentSession()
            session.add_event("test", "Test event")
            
            store.create(session)
            
            # Retrieve from disk
            retrieved = store.get(session.session_id)
            
            assert retrieved is not None
            assert retrieved.session_id == session.session_id
            assert len(retrieved.events) == 1
    
    def test_update_session_on_disk(self):
        """Test updating a session persisted on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONSessionStore(tmpdir)
            session = EnvironmentSession()
            store.create(session)
            
            session.add_event("update", "Update event")
            store.update(session)
            
            # Retrieve and verify
            retrieved = store.get(session.session_id)
            assert len(retrieved.events) == 1
    
    def test_list_sessions_from_disk(self):
        """Test listing sessions from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONSessionStore(tmpdir)
            
            session1 = EnvironmentSession()
            session2 = EnvironmentSession()
            
            store.create(session1)
            store.create(session2)
            
            sessions = store.list_sessions()
            
            assert len(sessions) == 2
    
    def test_delete_session_from_disk(self):
        """Test deleting a session from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONSessionStore(tmpdir)
            session = EnvironmentSession()
            store.create(session)
            
            session_file = Path(tmpdir) / f"{session.session_id}.json"
            assert session_file.exists()
            
            result = store.delete(session.session_id)
            
            assert result is True
            assert not session_file.exists()
    
    def test_session_with_complex_data(self):
        """Test persisting a session with complex nested data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JSONSessionStore(tmpdir)
            
            request = EnvironmentRequest(
                project_path="/tmp/test",
                natural_language_goal="Test goal",
                required_tools=["python", "git"],
                optional_tools=["docker"],
            )
            
            session = EnvironmentSession(request=request)
            session.add_event("created", "Session created")
            
            decision = AgentDecision(
                provider="Test Provider",
                model="test-model",
                decision_type="intent_parsing",
                reasoning_summary="Parsed intent",
                confidence=0.9,
            )
            session.add_agent_decision(decision)
            
            store.create(session)
            
            # Retrieve and verify
            retrieved = store.get(session.session_id)
            assert retrieved is not None
            assert retrieved.request is not None
            assert retrieved.request.project_path == "/tmp/test"
            assert len(retrieved.agent_decisions) == 1


class TestSessionStoreGlobalFunctions:
    """Test global session store functions."""
    
    def test_get_default_store(self):
        """Test getting the default store."""
        # Reset to ensure clean state
        set_session_store(None)
        
        store = get_session_store()
        
        assert store is not None
        assert isinstance(store, InMemorySessionStore)
    
    def test_set_custom_store(self):
        """Test setting a custom store."""
        custom_store = InMemorySessionStore()
        set_session_store(custom_store)
        
        retrieved = get_session_store()
        
        assert retrieved is custom_store
    
    def test_set_json_store(self):
        """Test setting a JSON-based store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_store = JSONSessionStore(tmpdir)
            set_session_store(json_store)
            
            retrieved = get_session_store()
            
            assert retrieved is json_store
            assert isinstance(retrieved, JSONSessionStore)


class TestAgentDecision:
    """Test AgentDecision model."""
    
    def test_create_decision(self):
        """Test creating an agent decision."""
        decision = AgentDecision(
            provider="LM Studio",
            model="qwen-2.5-7b",
            decision_type="strategy_selection",
            reasoning_summary="Selected optimal strategy",
            confidence=0.85,
        )
        
        assert decision.decision_id is not None
        assert decision.provider == "LM Studio"
        assert decision.confidence == 0.85
    
    def test_decision_to_dict(self):
        """Test serializing agent decision to dict."""
        decision = AgentDecision(
            provider="Test",
            model="test-model",
            decision_type="test_type",
            reasoning_summary="Test reasoning",
        )
        
        data = decision.to_dict()
        
        assert data["provider"] == "Test"
        assert data["reasoning_summary"] == "Test reasoning"
        assert "created_at" in data


class TestSessionEvent:
    """Test SessionEvent model."""
    
    def test_create_event(self):
        """Test creating a session event."""
        event = SessionEvent(
            event_type="test_event",
            message="Test message",
            details={"key": "value"},
        )
        
        assert event.event_id is not None
        assert event.event_type == "test_event"
        assert event.details["key"] == "value"
    
    def test_event_to_dict(self):
        """Test serializing event to dict."""
        event = SessionEvent(
            event_type="test",
            message="Test",
        )
        
        data = event.to_dict()
        
        assert data["event_type"] == "test"
        assert "timestamp" in data


class TestRecoveryRecord:
    """Test RecoveryRecord model."""
    
    def test_create_recovery_record(self):
        """Test creating a recovery record."""
        record = RecoveryRecord(
            failure_action_id="action123",
            diagnosis="Network timeout",
            recovery_strategy="Retry with backoff",
        )
        
        assert record.recovery_id is not None
        assert record.failure_action_id == "action123"
        assert record.approved is False
        assert record.executed is False
    
    def test_recovery_record_to_dict(self):
        """Test serializing recovery record to dict."""
        record = RecoveryRecord(
            failure_action_id="action123",
            diagnosis="Test diagnosis",
            recovery_strategy="Test strategy",
        )
        
        data = record.to_dict()
        
        assert data["failure_action_id"] == "action123"
        assert data["diagnosis"] == "Test diagnosis"
        assert "recovery_id" in data

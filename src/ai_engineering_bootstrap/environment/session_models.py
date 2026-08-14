from datetime import UTC, datetime

"""
Session models for environment orchestration.

This module defines the core session data structures that track
the complete lifecycle of an environment bootstrap operation.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..planner.models import ExecutionPlan
from .models import (
    ActualEnvironmentState,
    DesiredEnvironmentState,
    EnvironmentDelta,
    EnvironmentRequest,
)


class SessionStatus(str, Enum):
    """Status values for environment sessions."""
    
    CREATED = "created"
    AUDITING = "auditing"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentDecision:
    """Records an LLM/Agent decision made during a session."""
    
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    request_id: str = ""
    provider: str = ""
    model: str = ""
    decision_type: str = ""  # intent_parsing, strategy_selection, failure_diagnosis, recovery_recommendation
    reasoning_summary: str = ""
    confidence: float = 0.0
    selected_capabilities: list[str] = field(default_factory=list)
    selected_strategy: dict[str, Any] = field(default_factory=dict)
    input_evidence_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "provider": self.provider,
            "model": self.model,
            "decision_type": self.decision_type,
            "reasoning_summary": self.reasoning_summary,
            "confidence": self.confidence,
            "selected_capabilities": self.selected_capabilities,
            "selected_strategy": self.selected_strategy,
            "input_evidence_ids": self.input_evidence_ids,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SessionEvent:
    """Represents an event in the session timeline."""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: str = ""  # audit_started, plan_created, approval_requested, action_executed, etc.
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ActionApprovalState:
    """Tracks the approval state of a single action."""
    
    action_id: str = ""
    status: str = "pending"  # pending, approved, rejected, skipped
    approved_at: datetime | None = None
    approved_by: str = "user"  # For MVP, always "user"
    rejection_reason: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action_id": self.action_id,
            "status": self.status,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class ExecutionEvidence:
    """Records evidence from action execution."""
    
    action_id: str = ""
    success: bool = False
    output: str = ""
    error: str | None = None
    verification_result: dict[str, Any] | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action_id": self.action_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "verification_result": self.verification_result,
            "artifacts": self.artifacts,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RecoveryRecord:
    """Records a recovery attempt."""
    
    recovery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    failure_action_id: str = ""
    diagnosis: str = ""
    recovery_strategy: str = ""
    recovery_plan: ExecutionPlan | None = None
    approved: bool = False
    executed: bool = False
    success: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "recovery_id": self.recovery_id,
            "failure_action_id": self.failure_action_id,
            "diagnosis": self.diagnosis,
            "recovery_strategy": self.recovery_strategy,
            "recovery_plan": self.recovery_plan.to_dict() if self.recovery_plan else None,
            "approved": self.approved,
            "executed": self.executed,
            "success": self.success,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EnvironmentSession:
    """
    Main session object that tracks the complete lifecycle of an
    environment bootstrap operation.
    """
    
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request: EnvironmentRequest | None = None
    actual_state: ActualEnvironmentState | None = None
    desired_state: DesiredEnvironmentState | None = None
    delta: EnvironmentDelta | None = None
    plan: ExecutionPlan | None = None
    status: SessionStatus = SessionStatus.CREATED
    current_action: str | None = None
    approval_states: dict[str, ActionApprovalState] = field(default_factory=dict)
    execution_history: list[ExecutionEvidence] = field(default_factory=list)
    verification_results: dict[str, Any] = field(default_factory=dict)
    recovery_history: list[RecoveryRecord] = field(default_factory=list)
    events: list[SessionEvent] = field(default_factory=list)
    agent_decisions: list[AgentDecision] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    
    def add_event(self, event_type: str, message: str, details: dict[str, Any] | None = None) -> SessionEvent:
        """Add an event to the session timeline."""
        event = SessionEvent(
            event_type=event_type,
            message=message,
            details=details or {},
        )
        self.events.append(event)
        self.updated_at = datetime.now(UTC)
        return event
    
    def add_agent_decision(self, decision: AgentDecision) -> None:
        """Record an agent decision."""
        decision.session_id = self.session_id
        if self.request:
            decision.request_id = self.request.request_id
        self.agent_decisions.append(decision)
        self.updated_at = datetime.now(UTC)
    
    def get_approval_state(self, action_id: str) -> ActionApprovalState | None:
        """Get the approval state for an action."""
        return self.approval_states.get(action_id)
    
    def set_approval_state(self, action_id: str, status: str, rejection_reason: str | None = None) -> None:
        """Set the approval state for an action."""
        if action_id not in self.approval_states:
            self.approval_states[action_id] = ActionApprovalState(action_id=action_id)
        
        state = self.approval_states[action_id]
        state.status = status
        if status == "approved":
            state.approved_at = datetime.now(UTC)
        elif status == "rejected":
            state.rejection_reason = rejection_reason
        
        self.updated_at = datetime.now(UTC)
    
    def add_execution_evidence(self, evidence: ExecutionEvidence) -> None:
        """Add execution evidence."""
        self.execution_history.append(evidence)
        self.updated_at = datetime.now(UTC)
    
    def add_recovery_record(self, record: RecoveryRecord) -> None:
        """Add a recovery record."""
        self.recovery_history.append(record)
        self.updated_at = datetime.now(UTC)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "request": self.request.to_dict() if self.request else None,
            "actual_state": self.actual_state.to_dict() if self.actual_state else None,
            "desired_state": self.desired_state.to_dict() if self.desired_state else None,
            "delta": self.delta.to_dict() if self.delta else None,
            "plan": self.plan.to_dict() if self.plan else None,
            "status": self.status.value,
            "current_action": self.current_action,
            "approval_states": {k: v.to_dict() for k, v in self.approval_states.items()},
            "execution_history": [e.to_dict() for e in self.execution_history],
            "verification_results": self.verification_results,
            "recovery_history": [r.to_dict() for r in self.recovery_history],
            "events": [e.to_dict() for e in self.events],
            "agent_decisions": [d.to_dict() for d in self.agent_decisions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

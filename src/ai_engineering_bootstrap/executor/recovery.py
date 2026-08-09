"""Recovery logic for failure classification and retry decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus


class FailureType(str, Enum):
    """Categorization of execution failures."""

    NONE = "none"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    POLICY_DENIED = "policy_denied"
    UNKNOWN_ACTION = "unknown_action"
    HANDLER_UNAVAILABLE = "handler_unavailable"
    VERIFICATION_FAILED = "verification_failed"
    UNSAFE_TO_RETRY = "unsafe_to_retry"


class RecoveryDecision(str, Enum):
    """Decision on how to proceed after a failure."""

    RETRY = "retry"
    REPLAN = "replan"
    STOP = "stop"


@dataclass(frozen=True)
class FailureRecord:
    """Structured record of a failure."""

    action_id: str
    failure_type: FailureType
    message: str
    is_retryable: bool
    requires_replan: bool


class RetryPolicy:
    """Deterministic policy for retry decisions."""

    def __init__(self, max_attempts: int = 1) -> None:
        self.max_attempts = max_attempts

    def classify_failure(self, result: ActionResult) -> FailureRecord:
        """Classify an ActionResult into a FailureType."""
        if result.status != ExecutionStatus.FAILED:
            return FailureRecord(
                action_id=result.action_id,
                failure_type=FailureType.NONE,
                message="",
                is_retryable=False,
                requires_replan=False,
            )

        msg = result.message.lower()

        if "policy" in msg or "denied" in msg:
            f_type = FailureType.POLICY_DENIED
            retryable = False
            replan = False
        elif "not supported" in msg or "unknown" in msg:
            f_type = FailureType.UNKNOWN_ACTION
            retryable = False
            replan = True
        elif "no real handler" in msg or "unavailable" in msg:
            f_type = FailureType.HANDLER_UNAVAILABLE
            retryable = False
            replan = True
        elif "verification" in msg:
            f_type = FailureType.VERIFICATION_FAILED
            retryable = False
            replan = True
        elif "timeout" in msg or "transient" in msg:
            f_type = FailureType.TRANSIENT
            retryable = True
            replan = False
        else:
            f_type = FailureType.PERMANENT
            retryable = False
            replan = False

        return FailureRecord(
            action_id=result.action_id,
            failure_type=f_type,
            message=result.message,
            is_retryable=retryable,
            requires_replan=replan,
        )

    def decide(self, failure: FailureRecord, current_attempt: int) -> RecoveryDecision:
        """Decide whether to RETRY, REPLAN, or STOP."""
        if failure.failure_type == FailureType.NONE:
            return RecoveryDecision.STOP

        if not failure.is_retryable:
            if failure.requires_replan:
                return RecoveryDecision.REPLAN
            return RecoveryDecision.STOP

        if current_attempt >= self.max_attempts:
            if failure.requires_replan:
                return RecoveryDecision.REPLAN
            return RecoveryDecision.STOP

        return RecoveryDecision.RETRY


__all__ = [
    "FailureRecord",
    "FailureType",
    "RecoveryDecision",
    "RetryPolicy",
]

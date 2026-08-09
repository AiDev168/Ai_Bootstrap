"""Unit tests for Recovery and Retry Logic."""

from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.executor.recovery import (
    FailureRecord,
    FailureType,
    RecoveryDecision,
    RetryPolicy,
)


def test_classify_policy_denial() -> None:
    """Policy denial must be classified as non-retryable."""
    res = ActionResult(
        action_id="bad_action",
        status=ExecutionStatus.FAILED,
        message="Safety Gate Denied: Policy violation",
        details={}
    )
    policy = RetryPolicy()
    record = policy.classify_failure(res)
    
    assert record.failure_type == FailureType.POLICY_DENIED
    assert record.is_retryable is False
    assert record.requires_replan is False

def test_classify_unknown_action() -> None:
    """Unknown action must require re-plan."""
    res = ActionResult(
        action_id="unknown_xyz",
        status=ExecutionStatus.FAILED,
        message="Action 'unknown_xyz' is not supported",
        details={}
    )
    policy = RetryPolicy()
    record = policy.classify_failure(res)
    
    assert record.failure_type == FailureType.UNKNOWN_ACTION
    assert record.is_retryable is False
    assert record.requires_replan is True

def test_classify_transient_failure() -> None:
    """Transient failure should be retryable."""
    res = ActionResult(
        action_id="temp_fail",
        status=ExecutionStatus.FAILED,
        message="Transient error occurred",
        details={}
    )
    policy = RetryPolicy()
    record = policy.classify_failure(res)
    
    assert record.failure_type == FailureType.TRANSIENT
    assert record.is_retryable is True

def test_decide_stop_on_policy_denial() -> None:
    """Decision must be STOP for policy denial."""
    record = FailureRecord(
        action_id="bad",
        failure_type=FailureType.POLICY_DENIED,
        message="Denied",
        is_retryable=False,
        requires_replan=False
    )
    policy = RetryPolicy(max_attempts=3)
    decision = policy.decide(record, current_attempt=1)
    
    assert decision == RecoveryDecision.STOP

def test_decide_replan_on_unknown() -> None:
    """Decision must be REPLAN for unknown action."""
    record = FailureRecord(
        action_id="unk",
        failure_type=FailureType.UNKNOWN_ACTION,
        message="Unknown",
        is_retryable=False,
        requires_replan=True
    )
    policy = RetryPolicy()
    decision = policy.decide(record, current_attempt=1)
    
    assert decision == RecoveryDecision.REPLAN

def test_decide_retry_on_transient() -> None:
    """Decision must be RETRY for transient failure if attempts remain."""
    record = FailureRecord(
        action_id="temp",
        failure_type=FailureType.TRANSIENT,
        message="Timeout",
        is_retryable=True,
        requires_replan=False
    )
    policy = RetryPolicy(max_attempts=3)
    
    # تلاش اول
    d1 = policy.decide(record, current_attempt=1)
    assert d1 == RecoveryDecision.RETRY
    
    # تلاش آخر (رسیدن به سقف)
    d2 = policy.decide(record, current_attempt=3)
    assert d2 == RecoveryDecision.STOP

def test_no_failure_record_on_success() -> None:
    """Success should yield NONE failure type."""
    res = ActionResult(
        action_id="ok",
        status=ExecutionStatus.SUCCESS,
        message="OK",
        details={}
    )
    policy = RetryPolicy()
    record = policy.classify_failure(res)
    
    assert record.failure_type == FailureType.NONE

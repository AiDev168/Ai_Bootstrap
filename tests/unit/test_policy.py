"""Unit tests for Action Policy and Safety Gate."""

from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.policy import (
    ActionPolicy,
    ActionRisk,
    ApprovalRequirement,
    SafetyGate,
)


def test_default_deny_unknown_action() -> None:
    """Unknown actions must be denied by default."""
    gate = SafetyGate()
    allowed, reason = gate.evaluate("sudo_rm_rf_root", ExecutionMode.REAL)

    assert allowed is False
    assert "Default Deny" in reason


def test_explicit_allow_low_risk() -> None:
    """Explicitly allowed LOW risk action should pass."""
    gate = SafetyGate()
    allowed, reason = gate.evaluate("check_python_version_real", ExecutionMode.REAL)

    assert allowed is True
    assert reason == "Allowed"


def test_mode_restriction() -> None:
    """Mock actions should be denied in REAL mode."""
    gate = SafetyGate()
    allowed, reason = gate.evaluate("install_git", ExecutionMode.REAL)

    assert allowed is False
    assert "not allowed in real mode" in reason


def test_approval_requirement() -> None:
    """Actions requiring approval must be denied without it."""
    gate = SafetyGate()
    gate.register_policy(
        ActionPolicy(
            action_id="test_approval_action",
            allowed=True,
            risk=ActionRisk.HIGH,
            allowed_modes=[ExecutionMode.REAL],
            approval_required=ApprovalRequirement.HUMAN,
        )
    )

    allowed, reason = gate.evaluate(
        "test_approval_action", ExecutionMode.REAL, is_approved=False
    )
    assert allowed is False
    assert "requires human approval" in reason

    # با تأیید باید بگذرد
    allowed, reason = gate.evaluate(
        "test_approval_action", ExecutionMode.REAL, is_approved=True
    )
    assert allowed is True


def test_human_approval_is_only_required_for_real_execution() -> None:
    gate = SafetyGate()
    gate.register_policy(
        ActionPolicy(
            action_id="test_mutation",
            allowed=True,
            risk=ActionRisk.MEDIUM,
            allowed_modes=[ExecutionMode.SAFE, ExecutionMode.REAL],
            approval_required=ApprovalRequirement.HUMAN,
        )
    )
    allowed, _ = gate.evaluate("test_mutation", ExecutionMode.SAFE)
    assert allowed is True
    allowed, reason = gate.evaluate("test_mutation", ExecutionMode.REAL)
    assert allowed is False
    assert "requires human approval" in reason

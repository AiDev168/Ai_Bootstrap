"""Tests for failure diagnosis and recovery agent."""

import pytest

from ai_engineering_bootstrap.agent.recovery_agent import (
    FailureDiagnoser,
    FailureDiagnosis,
    RecoveryAgent,
    RecoveryProposal,
)
from ai_engineering_bootstrap.executor.models import ActionExecution
from ai_engineering_bootstrap.agent.provider import MockProvider


class TestFailureDiagnosis:
    """Test FailureDiagnosis dataclass."""

    def test_create_diagnosis(self) -> None:
        """Test creating failure diagnosis."""
        diagnosis = FailureDiagnosis(
            action_id="action-123",
            failure_type="permission_denied",
            root_cause="Missing sudo privileges",
            suggested_recovery="Run with elevated privileges",
            confidence=0.85,
        )
        assert diagnosis.action_id == "action-123"
        assert diagnosis.failure_type == "permission_denied"
        assert diagnosis.confidence == 0.85
        assert diagnosis.can_retry is True

    def test_diagnosis_requires_user_action(self) -> None:
        """Test diagnosis requiring user action."""
        diagnosis = FailureDiagnosis(
            action_id="action-456",
            failure_type="permission_denied",
            root_cause="Admin access required",
            suggested_recovery="Provide admin credentials",
            requires_user_action=True,
            user_action_description="Please enter administrator password",
        )
        assert diagnosis.requires_user_action is True
        assert "password" in diagnosis.user_action_description.lower()


class TestRecoveryProposal:
    """Test RecoveryProposal dataclass."""

    def test_create_proposal(self) -> None:
        """Test creating recovery proposal."""
        diagnosis = FailureDiagnosis(
            action_id="action-789",
            failure_type="network_timeout",
            root_cause="Download timed out",
            suggested_recovery="Retry with increased timeout",
        )
        proposal = RecoveryProposal(
            diagnosis=diagnosis,
            recovery_actions=["Check network", "Retry download"],
            estimated_success_probability=0.75,
        )
        assert len(proposal.recovery_actions) == 2
        assert proposal.estimated_success_probability == 0.75
        assert proposal.requires_approval is True

    def test_proposal_new_plan_required(self) -> None:
        """Test proposal requiring new plan."""
        diagnosis = FailureDiagnosis(
            action_id="action-999",
            failure_type="platform_unsupported",
            root_cause="Tool not available for this OS",
            suggested_recovery="Find alternative",
        )
        proposal = RecoveryProposal(
            diagnosis=diagnosis,
            recovery_actions=["Search alternatives"],
            new_plan_required=True,
        )
        assert proposal.new_plan_required is True


class TestFailureDiagnoserDeterministic:
    """Test deterministic failure diagnosis."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.diagnoser = FailureDiagnoser(provider=None)

    def test_diagnose_permission_denied(self) -> None:
        """Test diagnosing permission denied error."""
        execution = ActionExecution(
            action_id="install-cursor",
            action_type="install_tool",
            status="failed",
        )
        error = "Permission denied: cannot write to /usr/bin"

        diagnosis = self.diagnoser.diagnose(execution, error)

        assert diagnosis.failure_type == "permission_denied"
        assert diagnosis.requires_user_action is True
        assert diagnosis.can_retry is True

    def test_diagnose_network_timeout(self) -> None:
        """Test diagnosing network timeout."""
        execution = ActionExecution(
            action_id="download-ruff",
            action_type="download",
            status="failed",
        )
        error = "Network timeout during download"

        diagnosis = self.diagnoser.diagnose(execution, error)

        assert diagnosis.failure_type == "network_timeout"
        assert diagnosis.can_retry is True

    def test_diagnose_checksum_mismatch(self) -> None:
        """Test diagnosing checksum mismatch."""
        execution = ActionExecution(
            action_id="verify-docker",
            action_type="verify",
            status="failed",
        )
        error = "Checksum mismatch: expected abc123, got def456"

        diagnosis = self.diagnoser.diagnose(execution, error)

        assert diagnosis.failure_type == "checksum_mismatch"
        assert diagnosis.can_retry is True

    def test_diagnose_dependency_missing(self) -> None:
        """Test diagnosing missing dependency."""
        execution = ActionExecution(
            action_id="install-pytorch",
            action_type="install",
            status="failed",
        )
        error = "Dependency missing: numpy not found"

        diagnosis = self.diagnoser.diagnose(execution, error)

        assert diagnosis.failure_type == "dependency_missing"

    def test_diagnose_version_conflict(self) -> None:
        """Test diagnosing version conflict."""
        execution = ActionExecution(
            action_id="install-package",
            action_type="install",
            status="failed",
        )
        error = "Version conflict: requires python>=3.9"

        diagnosis = self.diagnoser.diagnose(execution, error)

        assert diagnosis.failure_type == "version_conflict"

    def test_diagnose_platform_unsupported(self) -> None:
        """Test diagnosing unsupported platform."""
        execution = ActionExecution(
            action_id="install-tool",
            action_type="install",
            status="failed",
        )
        error = "Platform unsupported: not available for windows"

        diagnosis = self.diagnoser.diagnose(execution, error)

        assert diagnosis.failure_type == "platform_unsupported"
        assert diagnosis.can_retry is False

    def test_diagnose_unknown_error(self) -> None:
        """Test diagnosing unknown error."""
        execution = ActionExecution(
            action_id="unknown-action",
            action_type="unknown",
            status="failed",
        )
        error = "Some weird error happened"

        diagnosis = self.diagnoser.diagnose(execution, error)

        assert diagnosis.failure_type == "unknown_error"
        assert diagnosis.confidence == 0.5


class TestFailureDiagnoserWithLLM:
    """Test failure diagnosis with LLM provider."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        provider = MockProvider()
        self.diagnoser = FailureDiagnoser(provider=provider)

    def test_diagnose_with_mock_provider(self) -> None:
        """Test diagnosis with mock LLM provider."""
        execution = ActionExecution(
            action_id="test-action",
            action_type="install",
            status="failed",
        )
        error = "Test error message"

        diagnosis = self.diagnoser.diagnose(execution, error)

        # Should return valid diagnosis (may fallback to deterministic)
        assert isinstance(diagnosis, FailureDiagnosis)
        assert diagnosis.action_id == "test-action"

    def test_fallback_on_llm_failure(self) -> None:
        """Test fallback to deterministic on LLM failure."""
        execution = ActionExecution(
            action_id="fallback-test",
            action_type="install",
            status="failed",
        )
        error = "Error that LLM cannot handle"

        diagnosis = self.diagnoser.diagnose(execution, error)

        # Should still return valid diagnosis via fallback
        assert isinstance(diagnosis, FailureDiagnosis)


class TestRecoveryAgent:
    """Test recovery agent."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.agent = RecoveryAgent()

    def test_propose_recovery_permission_denied(self) -> None:
        """Test proposing recovery for permission denied."""
        execution = ActionExecution(
            action_id="install-cursor",
            action_type="install_tool",
            status="failed",
        )
        error = "Permission denied"

        proposal = self.agent.propose_recovery(execution, error)

        assert isinstance(proposal, RecoveryProposal)
        assert len(proposal.recovery_actions) > 0
        assert "elevated privileges" in str(proposal.recovery_actions).lower()

    def test_propose_recovery_network_timeout(self) -> None:
        """Test proposing recovery for network timeout."""
        execution = ActionExecution(
            action_id="download",
            action_type="download",
            status="failed",
        )
        error = "Network timeout"

        proposal = self.agent.propose_recovery(execution, error)

        assert "network" in str(proposal.recovery_actions).lower() or "retry" in str(
            proposal.recovery_actions
        ).lower()

    def test_propose_recovery_success_probability(self) -> None:
        """Test success probability estimation."""
        execution = ActionExecution(
            action_id="test",
            action_type="install",
            status="failed",
        )

        # First retry
        proposal1 = self.agent.propose_recovery(execution, "error", retry_count=0)
        # Third retry
        proposal2 = self.agent.propose_recovery(execution, "error", retry_count=3)

        # Success probability should decrease with retries
        assert proposal1.estimated_success_probability >= proposal2.estimated_success_probability

    def test_propose_recovery_platform_unsupported(self) -> None:
        """Test proposing recovery for unsupported platform."""
        execution = ActionExecution(
            action_id="install",
            action_type="install",
            status="failed",
        )
        error = "Platform unsupported"

        proposal = self.agent.propose_recovery(execution, error)

        assert proposal.new_plan_required is True


class TestRecoveryAgentEdgeCases:
    """Test edge cases in recovery agent."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.agent = RecoveryAgent()

    def test_empty_error_message(self) -> None:
        """Test handling empty error message."""
        execution = ActionExecution(
            action_id="test",
            action_type="install",
            status="failed",
        )

        proposal = self.agent.propose_recovery(execution, "")

        assert isinstance(proposal, RecoveryProposal)
        assert proposal.diagnosis.failure_type == "unknown_error"

    def test_very_long_error_message(self) -> None:
        """Test handling very long error message."""
        execution = ActionExecution(
            action_id="test",
            action_type="install",
            status="failed",
        )
        error = "Error: " + "details " * 1000

        proposal = self.agent.propose_recovery(execution, error)

        assert isinstance(proposal, RecoveryProposal)
        # Root cause should be truncated
        assert len(proposal.diagnosis.root_cause) < 300

    def test_multiple_retries(self) -> None:
        """Test handling multiple retries."""
        execution = ActionExecution(
            action_id="retry-test",
            action_type="install",
            status="failed",
        )

        for i in range(5):
            proposal = self.agent.propose_recovery(
                execution, "persistent error", retry_count=i
            )
            assert isinstance(proposal, RecoveryProposal)

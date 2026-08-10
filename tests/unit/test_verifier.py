from ai_engineering_bootstrap.executor.handlers.verifiers import PythonVersionVerifier
from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.executor.verifier import (
    VerificationStatus,
    VerifierRegistry,
)
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


def _action(action_id: str = "check_python_version_real") -> ExecutionPlanAction:
    return ExecutionPlanAction(
        action_id=action_id,
        description="Check Python version",
        priority=1,
    )


def test_python_verifier_independently_verifies_success() -> None:
    result = PythonVersionVerifier().verify(
        _action(),
        ActionResult(
            action_id="check_python_version_real",
            status=ExecutionStatus.SUCCESS,
            message="untrusted executor message",
        ),
        context=None,
    )
    assert result.status == VerificationStatus.VERIFIED
    assert result.observed
    assert result.details["source"] == "sys.version_info"


def test_python_verifier_skips_failed_execution() -> None:
    result = PythonVersionVerifier().verify(
        _action(),
        ActionResult(
            action_id="check_python_version_real",
            status=ExecutionStatus.FAILED,
            message="failed",
        ),
        context=None,
    )
    assert result.status == VerificationStatus.SKIPPED


def test_registry_contains_python_verifier() -> None:
    registry = VerifierRegistry()
    assert registry.get_verifier("check_python_version_real") is not None


def test_registry_returns_none_for_unknown_action() -> None:
    registry = VerifierRegistry()
    assert registry.get_verifier("unknown-action") is None

"""Concrete implementations of Action Verifiers."""

from __future__ import annotations

import sys

from ai_engineering_bootstrap.executor.models import ActionResult, ExecutionStatus
from ai_engineering_bootstrap.executor.verifier import (
    ActionVerifier,
    VerificationResult,
    VerificationStatus,
)
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


class PythonVersionVerifier(ActionVerifier):
    """
    Independently verifies that the Python version meets requirements.
    
    Does NOT trust the ExecutionResult message.
    Reads sys.version_info directly.
    """

    def verify(
        self, 
        action: ExecutionPlanAction, 
        execution_result: ActionResult, 
        context: any
    ) -> VerificationResult:
        # اگر خودِ اکشن خطا داده باشد، وریفیکیشن معنی ندارد
        if execution_result.status != ExecutionStatus.SUCCESS:
            return VerificationResult(
                action_id=action.action_id,
                status=VerificationStatus.SKIPPED,
                message="Execution failed; nothing to verify.",
                details={"execution_status": execution_result.status.value}
            )

        # مشاهده مستقل محیط
        current = sys.version_info[:2]
        required = (3, 8) # فرض بر این است که شرط حداقل 3.8 است
        
        is_valid = current >= required
        observed_str = f"{current[0]}.{current[1]}"

        if is_valid:
            return VerificationResult(
                action_id=action.action_id,
                status=VerificationStatus.VERIFIED,
                message=f"Independently verified: Python {observed_str} meets requirement >= {'.'.join(map(str, required))}.",
                expected=f">={'.'.join(map(str, required))}",
                observed=observed_str,
                details={"source": "sys.version_info"}
            )
        else:
            return VerificationResult(
                action_id=action.action_id,
                status=VerificationStatus.FAILED,
                message=f"Verification failed: Python {observed_str} does not meet requirement.",
                expected=f">={'.'.join(map(str, required))}",
                observed=observed_str,
                details={"source": "sys.version_info"}
            )


DEFAULT_VERIFIERS = {
    "check_python_version_real": PythonVersionVerifier(),
}

__all__ = ["DEFAULT_VERIFIERS", "PythonVersionVerifier"]

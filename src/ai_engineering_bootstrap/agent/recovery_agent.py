"""Failure diagnosis and recovery agent using LLM."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ai_engineering_bootstrap.agent.provider import LLMProvider
from ai_engineering_bootstrap.executor.models import ActionExecution


@dataclass
class FailureDiagnosis:
    """Diagnosis of a failed action."""

    action_id: str
    failure_type: (
        str  # e.g., "download_failed", "installation_error", "verification_failed"
    )
    root_cause: str
    suggested_recovery: str
    confidence: float = 0.0
    requires_user_action: bool = False
    user_action_description: str = ""
    can_retry: bool = True
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class RecoveryProposal:
    """Proposed recovery plan for failed actions."""

    diagnosis: FailureDiagnosis
    recovery_actions: list[str] = field(default_factory=list)
    new_plan_required: bool = False
    estimated_success_probability: float = 0.0
    reasoning: str = ""
    requires_approval: bool = True


class FailureDiagnoser:
    """Diagnose failures using LLM + deterministic heuristics."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider
        self._failure_patterns = {
            "permission_denied": (
                "Permission denied during installation",
                "Requires elevated privileges or different installation path",
            ),
            "network_timeout": (
                "Network timeout during download",
                "Retry with increased timeout or check network connectivity",
            ),
            "checksum_mismatch": (
                "Artifact checksum does not match expected value",
                "Re-download artifact or verify source integrity",
            ),
            "dependency_missing": (
                "Required dependency not found",
                "Install missing dependency first",
            ),
            "version_conflict": (
                "Version conflict with existing installation",
                "Upgrade or downgrade conflicting package",
            ),
            "platform_unsupported": (
                "Tool not supported on this platform",
                "Use alternative installation method or tool",
            ),
        }

    def diagnose(
        self,
        execution: ActionExecution,
        error_message: str,
        retry_count: int = 0,
    ) -> FailureDiagnosis:
        """
        Diagnose a failed action execution.

        Args:
            execution: The failed ActionExecution
            error_message: Error message from execution
            retry_count: Number of previous retry attempts

        Returns:
            FailureDiagnosis with root cause and recovery suggestions
        """
        if not self.provider:
            return self._deterministic_diagnose(execution, error_message, retry_count)

        try:
            return self._llm_diagnose(execution, error_message, retry_count)
        except Exception:  # noqa: BLE001 - intentional LLM fallback boundary
            # Fallback to deterministic on any LLM failure
            return self._deterministic_diagnose(execution, error_message, retry_count)

    def _llm_diagnose(
        self,
        execution: ActionExecution,
        error_message: str,
        retry_count: int,
    ) -> FailureDiagnosis:
        """Use LLM to diagnose failure."""
        prompt = self._build_diagnosis_prompt(execution, error_message, retry_count)

        decision = self.provider.decide(prompt, [])

        try:
            content = decision.reasoning_summary.strip()
            if content.startswith("```json"):
                content = content[7:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()

            parsed = json.loads(content)

            return FailureDiagnosis(
                action_id=execution.action_id,
                failure_type=parsed.get("failure_type", "unknown"),
                root_cause=parsed.get("root_cause", ""),
                suggested_recovery=parsed.get("suggested_recovery", ""),
                confidence=parsed.get("confidence", decision.confidence),
                requires_user_action=parsed.get("requires_user_action", False),
                user_action_description=parsed.get("user_action_description", ""),
                can_retry=parsed.get("can_retry", True),
                retry_count=retry_count,
                max_retries=parsed.get("max_retries", 3),
            )
        except (json.JSONDecodeError, KeyError):
            return self._deterministic_diagnose(execution, error_message, retry_count)

    def _deterministic_diagnose(
        self,
        execution: ActionExecution,
        error_message: str,
        retry_count: int,
    ) -> FailureDiagnosis:
        """Deterministic diagnosis using pattern matching."""
        error_lower = error_message.lower()

        # Match against known patterns
        for pattern_key, (
            pattern_desc,
            recovery_desc,
        ) in self._failure_patterns.items():
            if (
                pattern_key.replace("_", " ") in error_lower
                or pattern_key in error_lower
            ):
                return FailureDiagnosis(
                    action_id=execution.action_id,
                    failure_type=pattern_key,
                    root_cause=pattern_desc,
                    suggested_recovery=recovery_desc,
                    confidence=0.75,
                    requires_user_action=pattern_key in ("permission_denied",),
                    user_action_description=(
                        "Please provide administrator credentials"
                        if pattern_key == "permission_denied"
                        else ""
                    ),
                    can_retry=pattern_key not in ("platform_unsupported",),
                    retry_count=retry_count,
                    max_retries=3,
                )

        # Generic fallback
        return FailureDiagnosis(
            action_id=execution.action_id,
            failure_type="unknown_error",
            root_cause=f"Execution failed: {error_message[:200]}",
            suggested_recovery="Review error logs and retry with adjusted parameters",
            confidence=0.5,
            requires_user_action=True,
            user_action_description="Manual intervention may be required",
            can_retry=True,
            retry_count=retry_count,
            max_retries=3,
        )

    def _build_diagnosis_prompt(
        self,
        execution: ActionExecution,
        error_message: str,
        retry_count: int,
    ) -> str:
        """Build prompt for LLM failure diagnosis."""
        return f"""You are a failure diagnosis agent for engineering environment setup.

Analyze the following failed action and diagnose the root cause:

Action ID: {execution.action_id}
Action Type: {execution.action_type}
Tool: {getattr(execution, "tool_id", "unknown")}
Strategy: {getattr(execution, "strategy", "unknown")}
Retry Count: {retry_count}

Error Message:
{error_message}

Common failure types:
- permission_denied: Requires elevated privileges
- network_timeout: Download or connection timed out
- checksum_mismatch: Artifact integrity check failed
- dependency_missing: Required dependency not installed
- version_conflict: Incompatible versions detected
- platform_unsupported: Tool not available for this platform

Respond with ONLY valid JSON in this exact format:
{{
    "failure_type": "...",
    "root_cause": "...",
    "suggested_recovery": "...",
    "confidence": 0.85,
    "requires_user_action": true/false,
    "user_action_description": "...",
    "can_retry": true/false,
    "max_retries": 3
}}

Be specific about the root cause and provide actionable recovery steps.

/no_think"""


class RecoveryAgent:
    """Generate and execute recovery plans."""

    def __init__(
        self,
        diagnoser: FailureDiagnoser | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self.diagnoser = diagnoser or FailureDiagnoser(provider)
        self.provider = provider

    def propose_recovery(
        self,
        execution: ActionExecution,
        error_message: str,
        retry_count: int = 0,
    ) -> RecoveryProposal:
        """
        Propose a recovery plan for a failed action.

        Args:
            execution: Failed ActionExecution
            error_message: Error from execution
            retry_count: Number of previous retries

        Returns:
            RecoveryProposal with recovery actions
        """
        diagnosis = self.diagnoser.diagnose(execution, error_message, retry_count)

        # Generate recovery actions based on diagnosis
        recovery_actions = self._generate_recovery_actions(diagnosis)

        # Determine if new plan is needed
        new_plan_required = diagnosis.failure_type in (
            "platform_unsupported",
            "version_conflict",
        )

        # Estimate success probability
        success_prob = self._estimate_success_probability(diagnosis, retry_count)

        return RecoveryProposal(
            diagnosis=diagnosis,
            recovery_actions=recovery_actions,
            new_plan_required=new_plan_required,
            estimated_success_probability=success_prob,
            reasoning=f"Recovery proposed based on {diagnosis.failure_type} diagnosis",
            requires_approval=diagnosis.requires_user_action or new_plan_required,
        )

    def _generate_recovery_actions(self, diagnosis: FailureDiagnosis) -> list[str]:
        """Generate specific recovery actions based on diagnosis."""
        actions = []

        failure_type = diagnosis.failure_type

        if failure_type == "permission_denied":
            actions.append("Request elevated privileges")
            actions.append("Retry installation with sudo/admin access")

        elif failure_type == "network_timeout":
            actions.append("Check network connectivity")
            actions.append("Increase timeout settings")
            actions.append("Retry download")

        elif failure_type == "checksum_mismatch":
            actions.append("Clear cached artifacts")
            actions.append("Re-download from official source")
            actions.append("Verify source integrity")

        elif failure_type == "dependency_missing":
            actions.append("Identify missing dependency")
            actions.append("Install dependency first")
            actions.append("Retry original installation")

        elif failure_type == "version_conflict":
            actions.append("Check installed versions")
            actions.append("Resolve version conflicts")
            actions.append("Consider re-planning with different versions")

        elif failure_type == "platform_unsupported":
            actions.append("Search for alternative installation method")
            actions.append("Consider compatible alternative tool")

        else:
            # Generic recovery
            actions.append("Review detailed error logs")
            actions.append("Retry with default parameters")

        return actions

    def _estimate_success_probability(
        self,
        diagnosis: FailureDiagnosis,
        retry_count: int,
    ) -> float:
        """Estimate probability of successful recovery."""
        base_prob = diagnosis.confidence

        # Reduce probability with each retry
        retry_penalty = min(retry_count * 0.1, 0.3)

        # Adjust based on failure type
        type_adjustments = {
            "permission_denied": 0.1,  # Usually easy to fix
            "network_timeout": 0.0,  # Moderate success rate
            "checksum_mismatch": -0.1,  # May indicate deeper issues
            "dependency_missing": 0.15,  # Usually straightforward
            "version_conflict": -0.2,  # Can be complex
            "platform_unsupported": -0.5,  # Often requires re-planning
        }

        type_adj = type_adjustments.get(diagnosis.failure_type, 0.0)

        return max(0.0, min(1.0, base_prob - retry_penalty + type_adj))

    def _build_recovery_prompt(
        self,
        diagnosis: FailureDiagnosis,
        execution: ActionExecution,
    ) -> str:
        """Build prompt for LLM recovery planning (if needed)."""
        return f"""You are a recovery planning agent.

Given this diagnosis:
- Failure Type: {diagnosis.failure_type}
- Root Cause: {diagnosis.root_cause}
- Suggested Recovery: {diagnosis.suggested_recovery}

Generate a step-by-step recovery plan with specific actions.

Respond with JSON array of actions:
["action1", "action2", ...]

/no_think"""


__all__ = [
    "FailureDiagnoser",
    "FailureDiagnosis",
    "RecoveryAgent",
    "RecoveryProposal",
]

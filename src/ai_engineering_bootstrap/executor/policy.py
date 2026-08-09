"""Action Policy and Safety Gate definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_engineering_bootstrap.executor.mode import ExecutionMode


class ActionRisk(str, Enum):
    """Risk levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalRequirement(str, Enum):
    """Approval requirements for actions."""
    NONE = "none"
    HUMAN = "human"


@dataclass(frozen=True)
class ActionPolicy:
    """Policy definition for a specific action."""
    action_id: str
    allowed: bool
    risk: ActionRisk
    allowed_modes: list[ExecutionMode]
    approval_required: ApprovalRequirement = ApprovalRequirement.NONE


class SafetyGate:
    """
    Enforces action policies before execution.
    Default behavior: DENY.
    """

    def __init__(self) -> None:
        self._policies: dict[str, ActionPolicy] = {}
        self._load_default_policies()

    def _load_default_policies(self) -> None:
        """Load default security policies."""
        # اکشن واقعی و ایمن پایتون
        self._policies["check_python_version_real"] = ActionPolicy(
            action_id="check_python_version_real",
            allowed=True,
            risk=ActionRisk.LOW,
            allowed_modes=[ExecutionMode.SAFE, ExecutionMode.REAL],
            approval_required=ApprovalRequirement.NONE
        )
        
        # اکشن‌های MOCK (فقط در حالت SAFE مجازند)
        mock_actions = ["install_git", "install_docker", "fix_venv", "fix_editable", "upgrade_python"]
        for action_id in mock_actions:
            self._policies[action_id] = ActionPolicy(
                action_id=action_id,
                allowed=True,
                risk=ActionRisk.LOW,
                allowed_modes=[ExecutionMode.SAFE], # در حالت REAL مجاز نیستند
                approval_required=ApprovalRequirement.NONE
            )

    def register_policy(self, policy: ActionPolicy) -> None:
        """Register or update a policy."""
        self._policies[policy.action_id] = policy

    def evaluate(self, action_id: str, mode: ExecutionMode, is_approved: bool = False) -> tuple[bool, str]:
        """
        Evaluate whether an action is allowed.
        Returns (allowed, reason).
        Default: DENY.
        """
        policy = self._policies.get(action_id)
        
        if policy is None:
            return False, f"Safety Gate Denied: Action '{action_id}' has no explicit policy (Default Deny)."
        
        if not policy.allowed:
            return False, f"Safety Gate Denied: Action '{action_id}' is explicitly forbidden."
        
        if mode not in policy.allowed_modes:
            return False, f"Safety Gate Denied: Action '{action_id}' is not allowed in {mode.value} mode."
        
        if policy.approval_required == ApprovalRequirement.HUMAN and not is_approved:
            return False, f"Safety Gate Denied: Action '{action_id}' requires human approval."
        
        return True, "Allowed"

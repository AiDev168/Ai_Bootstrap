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
    """Policy definition for a specific canonical action."""

    action_id: str
    allowed: bool
    risk: ActionRisk
    allowed_modes: list[ExecutionMode]
    approval_required: ApprovalRequirement = ApprovalRequirement.NONE


class SafetyGate:
    """Enforce canonical action policies before execution."""

    def __init__(self) -> None:
        self._policies: dict[str, ActionPolicy] = {}
        self._load_default_policies()

    @staticmethod
    def canonical_action_id(action_id: str) -> str:
        """Map an instance action ID to its canonical policy ID."""
        if action_id.startswith("install_python_package:"):
            return "install_python_package"
        return action_id

    def _load_default_policies(self) -> None:
        """Load default security policies."""
        self._policies["check_python_version_real"] = ActionPolicy(
            action_id="check_python_version_real",
            allowed=True,
            risk=ActionRisk.LOW,
            allowed_modes=[ExecutionMode.SAFE, ExecutionMode.REAL],
            approval_required=ApprovalRequirement.NONE,
        )
        self._policies["create_virtualenv"] = ActionPolicy(
            "create_virtualenv",
            True,
            ActionRisk.MEDIUM,
            [ExecutionMode.SAFE, ExecutionMode.REAL],
            ApprovalRequirement.HUMAN,
        )
        self._policies["install_python_package"] = ActionPolicy(
            "install_python_package",
            True,
            ActionRisk.MEDIUM,
            [ExecutionMode.SAFE, ExecutionMode.REAL],
            ApprovalRequirement.HUMAN,
        )
        self._policies["install_project_dependencies"] = ActionPolicy(
            "install_project_dependencies",
            True,
            ActionRisk.MEDIUM,
            [ExecutionMode.SAFE, ExecutionMode.REAL],
            ApprovalRequirement.HUMAN,
        )
        self._policies["fix_editable"] = ActionPolicy(
            "fix_editable",
            True,
            ActionRisk.MEDIUM,
            [ExecutionMode.SAFE],
            ApprovalRequirement.HUMAN,
        )
        self._policies["install_git"] = ActionPolicy(
            action_id="install_git",
            allowed=True,
            risk=ActionRisk.MEDIUM,
            allowed_modes=[ExecutionMode.SAFE],
            approval_required=ApprovalRequirement.HUMAN,
        )
        for action_id, risk in (
            ("install_docker", ActionRisk.HIGH),
            ("install_cursor", ActionRisk.MEDIUM),
        ):
            self._policies[action_id] = ActionPolicy(
                action_id=action_id,
                allowed=True,
                risk=risk,
                allowed_modes=[ExecutionMode.SAFE, ExecutionMode.REAL],
                approval_required=ApprovalRequirement.HUMAN,
            )
        for action_id in ("fix_venv", "fix_editable", "upgrade_python"):
            self._policies[action_id] = ActionPolicy(
                action_id=action_id,
                allowed=True,
                risk=ActionRisk.LOW,
                allowed_modes=[ExecutionMode.SAFE],
                approval_required=ApprovalRequirement.NONE,
            )

    def register_policy(self, policy: ActionPolicy) -> None:
        """Register or update a policy."""
        self._policies[policy.action_id] = policy

    def get_policy(self, action_id: str) -> ActionPolicy | None:
        """Return the explicit policy for an action instance."""
        return self._policies.get(self.canonical_action_id(action_id))

    def requires_human_approval(self, action_id: str) -> bool:
        """Return whether the canonical action requires human approval."""
        policy = self.get_policy(action_id)
        return (
            policy is not None and policy.approval_required == ApprovalRequirement.HUMAN
        )

    def evaluate(
        self, action_id: str, mode: ExecutionMode, is_approved: bool = False
    ) -> tuple[bool, str]:
        """Evaluate whether an action instance is allowed."""
        canonical_id = self.canonical_action_id(action_id)
        policy = self._policies.get(canonical_id)
        if policy is None:
            return (
                False,
                f"Safety Gate Denied: Action '{action_id}' has no explicit policy (Default Deny).",
            )
        if not policy.allowed:
            return (
                False,
                f"Safety Gate Denied: Action '{action_id}' is explicitly forbidden.",
            )
        if mode not in policy.allowed_modes:
            return (
                False,
                f"Safety Gate Denied: Action '{action_id}' is not allowed in {mode.value} mode.",
            )
        if (
            mode == ExecutionMode.REAL
            and policy.approval_required == ApprovalRequirement.HUMAN
            and not is_approved
        ):
            return (
                False,
                f"Safety Gate Denied: Action '{action_id}' requires human approval.",
            )
        return True, "Allowed"

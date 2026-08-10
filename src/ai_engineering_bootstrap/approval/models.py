"""Models for Human Approval workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ApprovalStatus(Enum):
    """Status of an approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ApprovalRequest:
    """
    Immutable request for human approval.
    Bound to a specific action_id, plan_id, and run_id to prevent replay attacks.
    """

    approval_id: str
    action_id: str
    plan_id: str
    run_id: str
    reason: str
    risk_level: str
    status: ApprovalStatus = ApprovalStatus.PENDING

    def is_approved(self) -> bool:
        return self.status == ApprovalStatus.APPROVED

    def is_rejected(self) -> bool:
        return self.status == ApprovalStatus.REJECTED

    def is_pending(self) -> bool:
        return self.status == ApprovalStatus.PENDING


__all__ = ["ApprovalRequest", "ApprovalStatus"]

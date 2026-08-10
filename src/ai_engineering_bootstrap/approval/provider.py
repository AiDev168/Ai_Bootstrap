from abc import ABC, abstractmethod
from dataclasses import replace

from ai_engineering_bootstrap.approval.models import ApprovalRequest, ApprovalStatus


class ApprovalProvider(ABC):
    """Abstract interface for human approval integration."""

    @abstractmethod
    def request_approval(
        self, action_id: str, plan_id: str, run_id: str, reason: str, risk_level: str
    ) -> ApprovalRequest:
        pass

    @abstractmethod
    def approve(self, approval_id: str) -> ApprovalRequest | None:
        pass

    @abstractmethod
    def reject(self, approval_id: str) -> ApprovalRequest | None:
        pass

    @abstractmethod
    def get_status(self, approval_id: str) -> ApprovalStatus | None:
        pass

    @abstractmethod
    def get_request(self, approval_id: str) -> ApprovalRequest | None:
        pass


class InMemoryApprovalProvider(ApprovalProvider):
    """Deterministic in-memory approval provider for tests and local runs."""

    def __init__(self) -> None:
        self._store: dict[str, ApprovalRequest] = {}
        self._counter = 0

    def request_approval(
        self, action_id: str, plan_id: str, run_id: str, reason: str, risk_level: str
    ) -> ApprovalRequest:
        self._counter += 1
        approval_id = f"appr-{self._counter}"
        req = ApprovalRequest(
            approval_id=approval_id,
            action_id=action_id,
            plan_id=plan_id,
            run_id=run_id,
            reason=reason,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING,
        )
        self._store[approval_id] = req
        return req

    def approve(self, approval_id: str) -> ApprovalRequest | None:
        if approval_id in self._store:
            req = self._store[approval_id]
            if req.status == ApprovalStatus.PENDING:
                # استفاده از replace برای حفظ ماهیت immutable دیتاکلاس
                updated_req = replace(req, status=ApprovalStatus.APPROVED)
                self._store[approval_id] = updated_req
            return self._store[approval_id]
        return None

    def reject(self, approval_id: str) -> ApprovalRequest | None:
        if approval_id in self._store:
            req = self._store[approval_id]
            if req.status == ApprovalStatus.PENDING:
                updated_req = replace(req, status=ApprovalStatus.REJECTED)
                self._store[approval_id] = updated_req
            return self._store[approval_id]
        return None

    def get_status(self, approval_id: str) -> ApprovalStatus | None:
        if approval_id in self._store:
            return self._store[approval_id].status
        return None

    def get_request(self, approval_id: str) -> ApprovalRequest | None:
        return self._store.get(approval_id)

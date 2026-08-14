#!/usr/bin/env python3
"""Central Action Registry supporting dual handler types."""

from __future__ import annotations

from ai_engineering_bootstrap.executor.handlers.base import ActionHandler
from ai_engineering_bootstrap.executor.handlers.real_handlers import REAL_HANDLERS
from ai_engineering_bootstrap.executor.handlers.safe_handlers import DEFAULT_SAFE_HANDLERS
from ai_engineering_bootstrap.executor.mode import ExecutionMode


class ActionRegistry:
    """Thread-safe registry mapping canonical action IDs to handlers.

    Execution plans may expose instance-specific action IDs such as
    ``install_python_package:ruff`` so that approval and evidence are independent.
    The registry resolves those IDs back to the canonical executor action.
    """

    def __init__(self) -> None:
        self._safe_handlers: dict[str, ActionHandler] = {}
        self._real_handlers: dict[str, ActionHandler] = {}
        self._load_defaults()

    @staticmethod
    def canonical_action_id(action_id: str) -> str:
        """Map an instance action ID to the registered executor action ID."""
        if action_id.startswith("install_python_package:"):
            return "install_python_package"
        return action_id

    def _load_defaults(self) -> None:
        """Load default safe/mock and approved real handlers."""
        self._safe_handlers.update(DEFAULT_SAFE_HANDLERS)
        self._real_handlers.update(REAL_HANDLERS)

    def get_handler(self, action_id: str, mode: ExecutionMode) -> ActionHandler:
        """Retrieve the handler for an action instance and execution mode."""
        canonical_id = self.canonical_action_id(action_id)
        if mode == ExecutionMode.REAL:
            if canonical_id in self._real_handlers:
                return self._real_handlers[canonical_id]
            if canonical_id in self._safe_handlers:
                raise KeyError(
                    f"Action '{action_id}' is not approved for REAL execution (No real handler)."
                )
            raise KeyError(f"Action '{action_id}' is not supported.")

        if canonical_id in self._safe_handlers:
            return self._safe_handlers[canonical_id]
        raise KeyError(f"Action '{action_id}' is not supported.")

    def is_supported(self, action_id: str, mode: ExecutionMode) -> bool:
        """Check support status for an action instance."""
        try:
            self.get_handler(action_id, mode)
            return True
        except KeyError:
            return False

    @property
    def supported_actions(self) -> list[str]:
        """Return sorted list of canonical supported action IDs."""
        return sorted(set(self._safe_handlers) | set(self._real_handlers))


__all__ = ["ActionRegistry"]

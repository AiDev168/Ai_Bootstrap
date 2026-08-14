#!/usr/bin/env python3
"""Central Action Registry supporting dual handler types."""

from __future__ import annotations

from ai_engineering_bootstrap.executor.handlers.base import ActionHandler
from ai_engineering_bootstrap.executor.handlers.real_handlers import REAL_HANDLERS
from ai_engineering_bootstrap.executor.handlers.safe_handlers import (
    DEFAULT_SAFE_HANDLERS,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode


class ActionRegistry:
    """
    Thread-safe registry mapping action IDs to Safe and Real handlers.
    Enforces allowlist principle: only registered actions can execute.
    """

    def __init__(self) -> None:
        self._safe_handlers: dict[str, ActionHandler] = {}
        self._real_handlers: dict[str, ActionHandler] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default safe/mock and approved real handlers."""
        for action_id, handler in DEFAULT_SAFE_HANDLERS.items():
            self._safe_handlers[action_id] = handler
        for action_id, handler in REAL_HANDLERS.items():
            self._real_handlers[action_id] = handler

    def get_handler(self, action_id: str, mode: ExecutionMode) -> ActionHandler | None:
        """
        Retrieve handler based on execution mode.
        - SAFE mode: returns safe handler.
        - REAL mode: returns real handler if exists; otherwise raises KeyError.
        """
        if mode == ExecutionMode.REAL:
            if action_id in self._real_handlers:
                return self._real_handlers[action_id]
            # در مود واقعی، اگر هندلر واقعی نباشد، خطا می‌دهیم (حتی اگر سیف باشد)
            # مگر اینکه سیاست دیگری تعریف شود. اینجا سخت‌گیرانه عمل می‌کنیم.
            if action_id in self._safe_handlers:
                raise KeyError(
                    f"Action '{action_id}' is not approved for REAL execution (No real handler)."
                )
            raise KeyError(f"Action '{action_id}' is not supported.")
        # SAFE MODE
        if action_id in self._safe_handlers:
            return self._safe_handlers[action_id]
        raise KeyError(f"Action '{action_id}' is not supported.")

    def is_supported(self, action_id: str, mode: ExecutionMode) -> bool:
        """Check support status."""
        try:
            self.get_handler(action_id, mode)
            return True
        except KeyError:
            return False

    @property
    def supported_actions(self) -> list[str]:
        """Return sorted list of all supported action IDs."""
        return sorted(
            set(list(self._safe_handlers.keys()) + list(self._real_handlers.keys()))
        )


__all__ = ["ActionRegistry"]

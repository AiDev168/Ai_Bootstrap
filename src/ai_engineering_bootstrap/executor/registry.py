"""Central Action Registry for mapping action IDs to handlers."""

from __future__ import annotations

from ai_engineering_bootstrap.executor.handlers import ActionHandler
from ai_engineering_bootstrap.executor.handlers.real_handlers import REAL_HANDLERS
from ai_engineering_bootstrap.executor.handlers.safe_handlers import DEFAULT_HANDLERS
from ai_engineering_bootstrap.executor.mode import ExecutionMode


class ActionRegistry:
    """
    Thread-safe, deterministic registry for action handlers.
    Enforces the allowlist principle: only registered actions can execute.
    Separates Safe/Mock handlers from Real (but safe) handlers.
    """

    def __init__(self) -> None:
        self._safe_handlers: dict[str, ActionHandler] = {}
        self._real_handlers: dict[str, ActionHandler] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default safe/mock handlers and approved real handlers."""
        for action_id, handler in DEFAULT_HANDLERS.items():
            self._safe_handlers[action_id] = handler
        for action_id, handler in REAL_HANDLERS.items():
            self._real_handlers[action_id] = handler

    def get_handler(self, action_id: str, mode: ExecutionMode) -> ActionHandler | None:
        """
        Retrieve the handler for a given action ID based on execution mode.
        - In SAFE mode: returns safe/mock handler if exists.
        - In REAL mode: returns real handler if explicitly approved; otherwise falls back
          to safe handler or None if unknown.
        Raises KeyError if the action is not supported in the requested mode.
        """
        if mode == ExecutionMode.REAL:
            if action_id in self._real_handlers:
                return self._real_handlers[action_id]
            # اگر هندلر واقعی نداشت، ولی هندلر سیف داشت، هنوز می‌توانیم سیف را برگردانیم
            # اما برای امنیت بیشتر، در مود واقعی فقط چیزهای تایید شده را برمی‌گردانیم
            # مگر اینکه بخواهیم fallback داشته باشیم. اینجا سخت‌گیرانه عمل می‌کنیم:
            if action_id in self._safe_handlers:
                # اکشن شناخته شده است اما نسخه واقعی ندارد -> در مود واقعی خطا می‌دهیم
                raise KeyError(f"Action '{action_id}' is not approved for REAL execution.")
            raise KeyError(f"Action '{action_id}' is not supported.")
        # SAFE MODE
        if action_id in self._safe_handlers:
            return self._safe_handlers[action_id]
        raise KeyError(f"Action '{action_id}' is not supported.")

    def is_supported(self, action_id: str, mode: ExecutionMode) -> bool:
        """Check if an action ID has a registered handler for the given mode."""
        try:
            self.get_handler(action_id, mode)
            return True
        except KeyError:
            return False

    @property
    def supported_actions(self) -> list[str]:
        """Return a sorted list of all supported action IDs."""
        return sorted(set(list(self._safe_handlers.keys()) + list(self._real_handlers.keys())))


__all__ = ["ActionRegistry"]

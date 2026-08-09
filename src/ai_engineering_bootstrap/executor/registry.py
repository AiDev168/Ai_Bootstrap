"""Central Action Registry for mapping action IDs to handlers."""

from __future__ import annotations

from ai_engineering_bootstrap.executor.handlers import ActionHandler
from ai_engineering_bootstrap.executor.handlers.safe_handlers import DEFAULT_HANDLERS


class ActionRegistry:
    """
    Thread-safe, deterministic registry for action handlers.
    Enforces the allowlist principle: only registered actions can execute.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, ActionHandler] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default safe/mock handlers."""
        for action_id, handler in DEFAULT_HANDLERS.items():
            self.register(action_id, handler)

    def register(self, action_id: str, handler: ActionHandler) -> None:
        """
        Register a handler for a specific action ID.
        Raises ValueError if attempting to overwrite an existing registration.
        """
        if action_id in self._handlers:
            raise ValueError(f"Action '{action_id}' is already registered.")
        self._handlers[action_id] = handler

    def get_handler(self, action_id: str) -> ActionHandler:
        """
        Retrieve the handler for a given action ID.
        Raises KeyError if the action is not supported.
        """
        if action_id not in self._handlers:
            raise KeyError(f"Action '{action_id}' is not supported/registered.")
        return self._handlers[action_id]

    def is_supported(self, action_id: str) -> bool:
        """Check if an action ID has a registered handler."""
        return action_id in self._handlers

    @property
    def supported_actions(self) -> list[str]:
        """Return a sorted list of supported action IDs."""
        return sorted(self._handlers.keys())


__all__ = ["ActionRegistry"]

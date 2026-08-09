"""Execution Mode definitions."""

from enum import Enum


class ExecutionMode(str, Enum):
    """
    Defines the execution authority level.
    
    SAFE: Default mode. All actions are simulated/mocked. No system changes.
    REAL: Explicit opt-in mode. Only pre-approved, low-risk, read-only actions 
          are allowed to execute real logic. Destructive actions remain forbidden.
    """
    SAFE = "safe"
    REAL = "real"


__all__ = ["ExecutionMode"]

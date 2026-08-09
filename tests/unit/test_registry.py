"""Unit tests for Action Registry."""

import pytest

from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.registry import ActionRegistry


def test_registry_loads_defaults() -> None:
    reg = ActionRegistry()
    # در مود SAFE باید پشتیبانی شود
    assert reg.is_supported("install_git", ExecutionMode.SAFE) is True
    # در مود REAL پشتیبانی نمی‌شود (چون هندلر واقعی ندارد)
    assert reg.is_supported("install_git", ExecutionMode.REAL) is False

def test_get_handler_safe_mode() -> None:
    reg = ActionRegistry()
    handler = reg.get_handler("install_git", ExecutionMode.SAFE)
    assert handler is not None

def test_get_handler_unknown() -> None:
    reg = ActionRegistry()
    with pytest.raises(KeyError):
        reg.get_handler("unknown_action_xyz", ExecutionMode.SAFE)

def test_get_handler_real_mode_rejection() -> None:
    reg = ActionRegistry()
    # اکشن‌هایی که فقط سیف هستند در مود واقعی رد می‌شوند
    with pytest.raises(KeyError):
        reg.get_handler("install_git", ExecutionMode.REAL)

def test_real_handler_approval() -> None:
    reg = ActionRegistry()
    # اکشن واقعی تایید شده باید در مود واقعی کار کند
    assert reg.is_supported("check_python_version_real", ExecutionMode.REAL) is True

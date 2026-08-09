"""Unit tests for Action Registry."""

import pytest

from ai_engineering_bootstrap.executor.handlers.safe_handlers import (
    InstallGitHandler,
)
from ai_engineering_bootstrap.executor.registry import ActionRegistry


def test_registry_loads_defaults() -> None:
    reg = ActionRegistry()
    assert reg.is_supported("install_git")
    assert reg.is_supported("fix_venv")

def test_register_new_handler() -> None:
    reg = ActionRegistry()
    #if try for double register an action is Error
    with pytest.raises(ValueError):
        reg.register("install_git", InstallGitHandler()) # تکراری

def test_get_handler_unknown() -> None:
    reg = ActionRegistry()
    with pytest.raises(KeyError):
        reg.get_handler("unknown_action_xyz")

def test_supported_actions_list() -> None:
    reg = ActionRegistry()
    actions = reg.supported_actions
    assert isinstance(actions, list)
    assert len(actions) > 0
    assert actions == sorted(actions) # باید مرتب باشد

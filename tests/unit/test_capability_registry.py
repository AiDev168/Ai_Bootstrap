"""Unit tests for Capability Registry."""

import inspect
from enum import Enum

import pytest

from ai_engineering_bootstrap.executor.capability import (
    Capability,
    CapabilityRegistry,
    CapabilityRisk,
    DuplicateCapabilityError,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode


def test_register_valid_capability() -> None:
    """Should successfully register a valid capability."""
    registry = CapabilityRegistry()
    cap = Capability(
        capability_id="check_python",
        name="Check Python Version",
        description="Verifies the installed Python version.",
        action_id="check_python_version_real",
        risk=CapabilityRisk.LOW,
        supported_modes=[ExecutionMode.SAFE, ExecutionMode.REAL],
    )
    registry.register(cap)
    retrieved = registry.get("check_python")
    assert retrieved is not None
    assert retrieved.name == "Check Python Version"
    assert retrieved.supports_mode(ExecutionMode.REAL) is True


def test_duplicate_capability_rejected() -> None:
    """Registering a duplicate capability_id must raise an error."""
    registry = CapabilityRegistry()
    cap = Capability(
        capability_id="dup_test",
        name="Test",
        description="Desc",
        action_id="test_action",
    )
    registry.register(cap)
    with pytest.raises(DuplicateCapabilityError):
        registry.register(cap)


def test_unknown_capability_returns_none() -> None:
    """Getting an unknown capability should return None safely."""
    registry = CapabilityRegistry()
    result = registry.get("unknown_xyz")
    assert result is None


def test_list_capabilities_deterministic() -> None:
    """Listing capabilities should return a sorted list."""
    registry = CapabilityRegistry()
    c1 = Capability("b_cap", "B", "Desc", "act_b")
    c2 = Capability("a_cap", "A", "Desc", "act_a")
    registry.register(c1)
    registry.register(c2)
    caps = registry.list_capabilities()
    assert len(caps) == 2
    assert caps[0].capability_id == "a_cap"
    assert caps[1].capability_id == "b_cap"


def test_find_by_action() -> None:
    """Should find capabilities by action_id."""
    registry = CapabilityRegistry()
    c1 = Capability("cap1", "One", "Desc", "shared_action")
    c2 = Capability("cap2", "Two", "Desc", "shared_action")
    c3 = Capability("cap3", "Three", "Desc", "other_action")
    registry.register(c1)
    registry.register(c2)
    registry.register(c3)
    results = registry.find_by_action("shared_action")
    assert len(results) == 2
    ids = {c.capability_id for c in results}
    assert ids == {"cap1", "cap2"}


def test_invalid_capability_empty_id() -> None:
    """Registering with empty capability_id should fail."""
    registry = CapabilityRegistry()
    cap = Capability("", "Name", "Desc", "action")
    with pytest.raises(ValueError):
        registry.register(cap)


def test_invalid_capability_empty_action() -> None:
    """Registering with empty action_id should fail."""
    registry = CapabilityRegistry()
    cap = Capability("id", "Name", "Desc", "")
    with pytest.raises(ValueError):
        registry.register(cap)


def test_capability_contains_no_callables() -> None:
    """Capability fields should not contain executable objects."""
    cap = Capability(
        capability_id="test",
        name="Test",
        description="Desc",
        action_id="action",
        risk=CapabilityRisk.LOW,
    )

    assert isinstance(cap.capability_id, str)
    assert isinstance(cap.name, str)
    assert isinstance(cap.description, str)
    assert isinstance(cap.action_id, str)
    assert cap.risk == CapabilityRisk.LOW
    assert isinstance(cap.risk, CapabilityRisk)
    assert isinstance(cap.supported_modes, list)
    assert isinstance(cap.metadata, dict)

    for field_name in cap.__dataclass_fields__:
        value = getattr(cap, field_name)
        if (
            callable(value)
            and not isinstance(value, (str, Enum, list, dict, bool))
            and (
                inspect.isfunction(value)
                or inspect.ismethod(value)
                or inspect.isbuiltin(value)
            )
        ):
            pytest.fail(f"Field {field_name} contains a callable function/method!")


def test_real_capable_does_not_authorize() -> None:
    """Marking a capability as REAL_CAPABLE does not bypass SafetyGate."""
    registry = CapabilityRegistry()
    cap = Capability(
        "real_cap",
        "Real Cap",
        "Desc",
        "dangerous_action",
        supported_modes=[ExecutionMode.REAL],
    )
    registry.register(cap)
    retrieved = registry.get("real_cap")
    assert retrieved is not None
    assert retrieved.supports_mode(ExecutionMode.REAL) is True
    assert not hasattr(retrieved, "execute")


def test_registry_does_not_bypass_safety_gate() -> None:
    """Registry is independent and cannot bypass SafetyGate."""
    registry = CapabilityRegistry()
    cap = Capability("test", "Test", "Desc", "action")
    registry.register(cap)
    assert registry.is_registered("test") is True
    assert registry.get("test") is not None


def test_security_negative_no_shell_injection() -> None:
    """Attempting to inject shell commands into metadata should be safe."""
    registry = CapabilityRegistry()
    malicious_metadata = {"cmd": "rm -rf /", "shell": "bash -c '...'"}
    cap = Capability(
        "malicious",
        "Malicious",
        "Desc",
        "action",
        metadata=malicious_metadata,
    )
    registry.register(cap)
    retrieved = registry.get("malicious")
    assert retrieved is not None
    assert retrieved.metadata["cmd"] == "rm -rf /"

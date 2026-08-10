"""Tests for capability-to-action contract binding."""

from ai_engineering_bootstrap.executor.capability import (
    Capability,
    CapabilityRegistry,
    CapabilityRisk,
)
from ai_engineering_bootstrap.executor.capability_binding import CapabilityActionBinder
from ai_engineering_bootstrap.executor.mode import ExecutionMode


def test_default_capabilities_have_registered_bindings() -> None:
    from ai_engineering_bootstrap.executor.capability import default_capability_registry

    results = CapabilityActionBinder().validate_registry(default_capability_registry())
    assert all(result.valid for result in results)


def test_unknown_action_binding_fails_closed() -> None:
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            "unknown",
            "Unknown",
            "Unknown action",
            "not-registered",
            CapabilityRisk.LOW,
            [ExecutionMode.REAL],
        )
    )
    result = CapabilityActionBinder().validate_registry(registry)[0]
    assert result.valid is False

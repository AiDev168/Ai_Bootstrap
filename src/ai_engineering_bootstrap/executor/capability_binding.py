"""Deterministic binding between capability metadata and executable contracts."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering_bootstrap.executor.capability import Capability, CapabilityRegistry
from ai_engineering_bootstrap.executor.policy import SafetyGate
from ai_engineering_bootstrap.executor.registry import ActionRegistry


@dataclass(frozen=True)
class CapabilityBindingResult:
    """Result of validating one capability's action binding."""

    capability_id: str
    action_id: str
    valid: bool
    reason: str


class CapabilityActionBinder:
    """Validate capability metadata against ActionRegistry and SafetyGate."""

    def __init__(
        self,
        action_registry: ActionRegistry | None = None,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        self._actions = action_registry or ActionRegistry()
        self._safety = safety_gate or SafetyGate()

    def validate(self, capability: Capability) -> CapabilityBindingResult:
        """Return a fail-closed binding result for a capability."""
        for mode in capability.supported_modes:
            if not self._actions.is_supported(capability.action_id, mode):
                return CapabilityBindingResult(
                    capability.capability_id,
                    capability.action_id,
                    False,
                    f"No handler supports action '{capability.action_id}' in {mode.value} mode.",
                )
            allowed, reason = self._safety.evaluate(
                capability.action_id,
                mode,
                is_approved=capability.requires_human_approval,
            )
            if not allowed and "requires human approval" not in reason:
                return CapabilityBindingResult(
                    capability.capability_id,
                    capability.action_id,
                    False,
                    reason,
                )
        return CapabilityBindingResult(
            capability.capability_id,
            capability.action_id,
            True,
            "Capability is bound to a registered action and policy.",
        )

    def validate_registry(
        self, registry: CapabilityRegistry
    ) -> list[CapabilityBindingResult]:
        """Validate every capability in deterministic order."""
        return [self.validate(capability) for capability in registry.list_capabilities()]


__all__ = ["CapabilityActionBinder", "CapabilityBindingResult"]

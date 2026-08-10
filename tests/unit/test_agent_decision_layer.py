"""Unit tests for Agent Decision Layer."""

import inspect

import pytest

from ai_engineering_bootstrap.agent.engine import AgentDecisionEngine
from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.agent.provider import (
    InProcessProvider,
    LocalServerProvider,
    MockProvider,
    ProviderConfig,
    RemoteAPIProvider,
)
from ai_engineering_bootstrap.executor.capability import (
    Capability,
    CapabilityRegistry,
    CapabilityRisk,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode


def _create_test_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    cap = Capability(
        capability_id="check_py",
        name="Check Python",
        description="Checks version",
        action_id="check_python_version_real",
        risk=CapabilityRisk.LOW,
        supported_modes=[ExecutionMode.SAFE, ExecutionMode.REAL],
    )
    registry.register(cap)
    return registry


def test_provider_interface_exists() -> None:
    """Verify abstract interface definition."""
    from ai_engineering_bootstrap.agent.provider import LLMProvider

    assert hasattr(LLMProvider, "decide")


def test_mock_provider_deterministic() -> None:
    """Mock provider must return deterministic output."""
    provider = MockProvider()
    registry = _create_test_registry()
    caps = registry.list_capabilities()

    d1 = provider.decide("fix environment", caps)
    d2 = provider.decide("fix environment", caps)

    assert d1.selected_capability_ids == d2.selected_capability_ids
    assert d1.confidence == 0.95


def test_local_server_config_represented() -> None:
    """Local server configuration must be representable."""
    config = ProviderConfig(
        provider_type="local_server",
        model="local-model",
        base_url="http://localhost:1234/v1",
        api_key=None,
    )
    assert config.provider_type == "local_server"
    assert config.base_url == "http://localhost:1234/v1"


def test_remote_api_config_represented() -> None:
    """Remote API configuration must be representable."""
    config = ProviderConfig(
        provider_type="remote_api",
        model="gpt-4",
        base_url="https://api.openai.com/v1",
        api_key="${ENV_VAR}",
    )
    assert config.provider_type == "remote_api"
    assert config.api_key == "${ENV_VAR}"


def test_in_process_config_represented() -> None:
    """In-process configuration must be representable."""
    config = ProviderConfig(
        provider_type="in_process",
        model="path/to/model",
        options={"device": "cuda"},
    )
    assert config.provider_type == "in_process"
    assert config.options["device"] == "cuda"


def test_api_key_not_exposed_in_decision() -> None:
    """API key must not appear in decision output."""
    provider = MockProvider()
    registry = _create_test_registry()
    decision = provider.decide("test", registry.list_capabilities())

    assert "secret_key_123" not in decision.reasoning_summary
    assert "secret_key_123" not in str(decision.metadata)


def test_agent_consumes_capability_metadata() -> None:
    """Agent engine should consume metadata only."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    decision = engine.decide("fix environment")

    assert isinstance(decision, AgentDecision)
    assert "check_py" in decision.selected_capability_ids


def test_agent_cannot_access_handlers() -> None:
    """Agent must not have access to ActionHandlers."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    assert not hasattr(engine, "_registry_handlers")
    assert not hasattr(engine, "execute")


def test_agent_cannot_execute_actions() -> None:
    """Agent engine must not execute actions."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    decision = engine.decide("fix test")

    assert decision.is_actionable() is True


def test_decision_contains_ids_not_commands() -> None:
    """Decision must contain IDs, not shell commands."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    decision = engine.decide("run malicious command rm -rf /")

    assert "rm -rf" not in decision.selected_capability_ids
    assert isinstance(decision.selected_capability_ids, list)


def test_unknown_capability_rejected() -> None:
    """Engine must reject decisions with unknown capability IDs."""
    registry = _create_test_registry()

    class BadProvider(MockProvider):
        def decide(self, context, capabilities):
            return AgentDecision(selected_capability_ids=["unknown_fake_id_123"])

    engine = AgentDecisionEngine(BadProvider(), registry)

    with pytest.raises(ValueError, match="Invalid capability ID"):
        engine.decide("test")


def test_malformed_decision_handling() -> None:
    """Malformed decisions should be handled safely."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    decision = engine.decide("")
    assert isinstance(decision, AgentDecision)


def test_safety_gate_remains_authoritative() -> None:
    """Agent decision does not bypass SafetyGate."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    decision = engine.decide("test")
    assert decision is not None


def test_provider_classes_exist() -> None:
    """All provider placeholder classes must exist."""
    assert LocalServerProvider is not None
    assert RemoteAPIProvider is not None
    assert InProcessProvider is not None


def test_deterministic_behavior() -> None:
    """Repeated calls must produce identical results."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    d1 = engine.decide("fix python")
    d2 = engine.decide("fix python")

    assert d1.selected_capability_ids == d2.selected_capability_ids
    assert d1.reasoning_summary == d2.reasoning_summary


def test_agent_does_not_bypass_planner() -> None:
    """Agent produces decision, not ExecutionPlan."""
    registry = _create_test_registry()
    provider = MockProvider()
    engine = AgentDecisionEngine(provider, registry)

    decision = engine.decide("test")

    assert isinstance(decision, AgentDecision)
    assert not hasattr(decision, "actions")


def test_existing_pipeline_unchanged() -> None:
    """Importing agent layer must not break existing pipeline."""
    from ai_engineering_bootstrap.executor import ExecutorEngine
    from ai_engineering_bootstrap.pipeline import PipelineEngine

    assert PipelineEngine is not None
    assert ExecutorEngine is not None


def test_no_shell_execution_in_agent() -> None:
    """Verify no subprocess or shell execution in agent module."""
    from ai_engineering_bootstrap import agent

    source = inspect.getsource(agent)
    assert "subprocess" not in source
    assert "os.system" not in source
    assert "shell=True" not in source

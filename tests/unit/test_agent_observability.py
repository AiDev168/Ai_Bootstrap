"""Tests for observable LLM/provider evidence."""

from ai_engineering_bootstrap.agent.engine import AgentDecisionEngine
from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.executor.capability import default_capability_registry


class FakeProvider:
    def metadata(self):
        return {"provider_type": "local_server"}

    def decide(self, context, available_capabilities):
        return AgentDecision(
            reasoning_summary="Select an existing remediation capability.",
            selected_capability_ids=[available_capabilities[0].capability_id],
            confidence=0.91,
        )


def test_agent_decision_records_provider_metadata() -> None:
    result = AgentDecisionEngine(FakeProvider(), default_capability_registry()).decide(
        "fix environment"
    )

    assert result.metadata["llm_used"] is True
    assert result.metadata["provider"]["provider_type"] == "local_server"
    assert result.confidence == 0.91

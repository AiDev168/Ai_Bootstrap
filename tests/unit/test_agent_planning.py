"""Tests for Agent decision to Planner integration."""

import pytest

from ai_engineering_bootstrap.agent.engine import AgentDecisionEngine
from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.agent.planning import AgentPlanningService
from ai_engineering_bootstrap.agent.provider import MockProvider
from ai_engineering_bootstrap.executor.capability import default_capability_registry
from ai_engineering_bootstrap.planner.engine import PlannerEngine


def test_agent_decision_becomes_execution_plan() -> None:
    registry = default_capability_registry()
    service = AgentPlanningService(
        AgentDecisionEngine(MockProvider(), registry), PlannerEngine(), registry
    )
    result = service.decide_and_plan("fix environment")
    assert result.plan.is_actionable
    assert result.plan.actions[0].action_id == "check_python_version_real"


def test_unknown_capability_cannot_be_planned() -> None:
    registry = default_capability_registry()
    planner = PlannerEngine()
    with pytest.raises(ValueError, match="Unknown capability"):
        planner.generate_plan_from_decision(
            AgentDecision(selected_capability_ids=["does-not-exist"]), registry
        )

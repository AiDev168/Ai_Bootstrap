"""Controlled bridge from Agent decisions to deterministic planning."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering_bootstrap.agent.engine import AgentDecisionEngine
from ai_engineering_bootstrap.agent.models import AgentDecision
from ai_engineering_bootstrap.executor.capability import CapabilityRegistry
from ai_engineering_bootstrap.planner.engine import PlannerEngine
from ai_engineering_bootstrap.planner.models import ExecutionPlan


@dataclass(frozen=True)
class AgentPlanningResult:
    """Decision plus the deterministic plan derived from it."""

    decision: AgentDecision
    plan: ExecutionPlan


class AgentPlanningService:
    """Compose Agent decision-making with Planner without an execution path."""

    def __init__(
        self,
        agent: AgentDecisionEngine,
        planner: PlannerEngine,
        capability_registry: CapabilityRegistry,
    ) -> None:
        self._agent = agent
        self._planner = planner
        self._capability_registry = capability_registry

    def decide_and_plan(self, context: str) -> AgentPlanningResult:
        """Generate an Agent decision and deterministically convert it to a plan."""
        decision = self._agent.decide(context)
        plan = self._planner.generate_plan_from_decision(
            decision, self._capability_registry
        )
        return AgentPlanningResult(decision=decision, plan=plan)

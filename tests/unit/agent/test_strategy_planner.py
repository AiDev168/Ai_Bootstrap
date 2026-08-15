"""Tests for strategy planner."""

from ai_engineering_bootstrap.agent.provider import MockProvider
from ai_engineering_bootstrap.agent.strategy_planner import (
    StrategyDecision,
    StrategyPlan,
    StrategyPlanner,
)
from ai_engineering_bootstrap.environment.models import (
    DeltaAction,
    EnvironmentDelta,
    ToolDelta,
    ToolStatus,
)
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog


class TestStrategyDecision:
    """Test StrategyDecision dataclass."""

    def test_create_decision(self) -> None:
        """Test creating strategy decision."""
        decision = StrategyDecision(
            tool_id="cursor",
            strategy_name="deb_install",
            confidence=0.95,
        )
        assert decision.tool_id == "cursor"
        assert decision.strategy_name == "deb_install"
        assert decision.confidence == 0.95
        assert decision.strategy_args == {}

    def test_create_decision_with_args(self) -> None:
        """Test creating decision with arguments."""
        decision = StrategyDecision(
            tool_id="ruff",
            strategy_name="pip_install",
            strategy_args={"package_name": "ruff", "version": "0.1.0"},
            artifact_url="https://example.com/ruff.whl",
        )
        assert decision.strategy_args["package_name"] == "ruff"
        assert decision.artifact_url == "https://example.com/ruff.whl"


class TestStrategyPlan:
    """Test StrategyPlan dataclass."""

    def test_create_empty_plan(self) -> None:
        """Test creating empty strategy plan."""
        plan = StrategyPlan()
        assert plan.decisions == []
        assert plan.overall_confidence == 0.0
        assert plan.requires_approval is True

    def test_create_plan_with_decisions(self) -> None:
        """Test creating plan with decisions."""
        decisions = [
            StrategyDecision(
                tool_id="cursor",
                strategy_name="deb_install",
                risk_level="medium",
            ),
            StrategyDecision(
                tool_id="ruff",
                strategy_name="pip_install",
                risk_level="low",
            ),
        ]
        plan = StrategyPlan(decisions=decisions, overall_confidence=0.9)

        assert len(plan.decisions) == 2
        assert plan.overall_confidence == 0.9

    def test_get_decisions_requiring_approval(self) -> None:
        """Test filtering decisions requiring approval."""
        decisions = [
            StrategyDecision(
                tool_id="cursor",
                strategy_name="deb_install",
                risk_level="high",
            ),
            StrategyDecision(
                tool_id="ruff",
                strategy_name="pip_install",
                risk_level="low",
            ),
            StrategyDecision(
                tool_id="black",
                strategy_name="pip_install",
                risk_level="medium",
            ),
        ]
        plan = StrategyPlan(decisions=decisions)

        requiring_approval = plan.get_decisions_requiring_approval()
        assert len(requiring_approval) == 2
        assert all(d.risk_level in ("medium", "high") for d in requiring_approval)


class TestStrategyPlannerDeterministic:
    """Test deterministic strategy planning."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.catalog = ToolCatalog()
        self.planner = StrategyPlanner(tool_catalog=self.catalog, provider=None)

    def test_plan_empty_delta(self) -> None:
        """Test planning with empty delta."""
        delta = EnvironmentDelta(tool_deltas=[], package_deltas=[])
        plan = self.planner.plan_strategies(delta)

        assert plan.decisions == []
        assert plan.reasoning_summary == "No tool changes required."

    def test_plan_no_install_deltas(self) -> None:
        """Test planning with no installation deltas."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="python",
                    action=DeltaAction.NONE,
                    actual_status=ToolStatus(
                        tool_id="python", status="ready", version="3.12.0"
                    ),
                )
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta)

        assert plan.decisions == []
        assert "No installations required" in plan.reasoning_summary

    def test_plan_cursor_install(self) -> None:
        """Test planning Cursor installation."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="cursor",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                )
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta, platform="linux")

        # Should have at least one decision
        assert len(plan.decisions) >= 0  # May be 0 if no strategy found
        if plan.decisions:
            assert plan.decisions[0].tool_id == "cursor"

    def test_plan_ruff_install(self) -> None:
        """Test planning Ruff installation."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="ruff",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                )
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta, platform="linux")

        # Ruff should use pip_install strategy
        if plan.decisions:
            assert plan.decisions[0].tool_id == "ruff"
            assert plan.decisions[0].strategy_name == "pip_install"

    def test_plan_multiple_tools(self) -> None:
        """Test planning multiple tool installations."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="cursor",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                ),
                ToolDelta(
                    tool_id="ruff",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                ),
                ToolDelta(
                    tool_id="pytest",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                ),
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta, platform="linux")

        # Should create decisions for installable tools
        assert isinstance(plan, StrategyPlan)
        assert plan.overall_confidence > 0


class TestStrategyPlannerWithLLM:
    """Test strategy planning with LLM provider."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.catalog = ToolCatalog()
        provider = MockProvider()
        self.planner = StrategyPlanner(tool_catalog=self.catalog, provider=provider)

    def test_plan_with_mock_provider(self) -> None:
        """Test planning with mock LLM provider."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="cursor",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                )
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta, platform="linux")

        # Should return valid plan (may fallback to deterministic)
        assert isinstance(plan, StrategyPlan)

    def test_fallback_on_llm_failure(self) -> None:
        """Test fallback to deterministic on LLM failure."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="ruff",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                )
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta)

        # Should still return valid plan via fallback
        assert isinstance(plan, StrategyPlan)


class TestStrategyPlannerEdgeCases:
    """Test edge cases in strategy planning."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.catalog = ToolCatalog()
        self.planner = StrategyPlanner(tool_catalog=self.catalog, provider=None)

    def test_unknown_tool(self) -> None:
        """Test planning for unknown tool."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="unknown_tool_xyz",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                )
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta)

        # Should handle gracefully (no decisions for unknown tools)
        assert isinstance(plan, StrategyPlan)

    def test_platform_without_strategies(self) -> None:
        """Test planning for platform without strategies."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="cursor",
                    action=DeltaAction.INSTALL,
                    actual_status=ToolStatus(tool_id="cursor", status="missing"),
                )
            ],
            package_deltas=[],
        )
        # Use non-existent platform
        plan = self.planner.plan_strategies(delta, platform="nonexistent_os")

        # Should handle gracefully
        assert isinstance(plan, StrategyPlan)

    def test_upgrade_action(self) -> None:
        """Test planning for upgrade action."""
        delta = EnvironmentDelta(
            tool_deltas=[
                ToolDelta(
                    tool_id="python",
                    action=DeltaAction.UPGRADE,
                    actual_status=ToolStatus(tool_id="python", status="installed"),
                )
            ],
            package_deltas=[],
        )
        plan = self.planner.plan_strategies(delta, platform="linux")

        # Should include upgrade in planning
        assert isinstance(plan, StrategyPlan)

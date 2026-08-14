"""Build validated execution plans from environment strategy decisions."""

from __future__ import annotations

from typing import ClassVar

from ai_engineering_bootstrap.agent.strategy_planner import StrategyPlan
from ai_engineering_bootstrap.environment.models import DeltaAction, EnvironmentDelta
from ai_engineering_bootstrap.executor.capability import (
    CapabilityRegistry,
    default_capability_registry,
)
from ai_engineering_bootstrap.planner.models import ExecutionPlan, ExecutionPlanAction


class ExecutionPlanBuilder:
    """Translate strategy decisions into independently addressable executor actions."""

    _TOOL_ACTIONS: ClassVar[dict[str, str]] = {
        "cursor": "install_cursor",
        "git": "install_git",
        "docker": "install_docker",
    }

    _STRATEGY_ACTIONS: ClassVar[dict[str, str | None]] = {
        "pip_install": "install_python_package",
        "deb_install": None,
        "apt_install": None,
        "binary_install": None,
        "tarball_install": None,
    }

    def __init__(self, capability_registry: CapabilityRegistry | None = None) -> None:
        self._capabilities = capability_registry or default_capability_registry()

    def build(
        self, delta: EnvironmentDelta, strategy_plan: StrategyPlan
    ) -> ExecutionPlan:
        """Build an executor plan and fail closed on unsupported actions."""
        actions: list[ExecutionPlanAction] = []
        for decision in strategy_plan.decisions:
            executor_action_id = self._resolve_action_id(
                decision.tool_id, decision.strategy_name
            )
            self._require_capability(executor_action_id)
            context = {
                "executor_action_id": executor_action_id,
                "tool_id": decision.tool_id,
                "strategy": decision.strategy_name,
                "strategy_args": dict(decision.strategy_args),
                "artifact_url": decision.artifact_url,
                "version": decision.version,
                "source": decision.source,
            }
            if executor_action_id == "install_python_package":
                context.update(
                    self._pip_context(
                        decision.tool_id, decision.strategy_args, decision.version
                    )
                )
            actions.append(
                ExecutionPlanAction(
                    action_id=self._instance_action_id(
                        executor_action_id, decision.tool_id
                    ),
                    description=f"Prepare {decision.tool_id} using {decision.strategy_name}",
                    priority=self._priority(decision.risk_level),
                    context=context,
                )
            )

        for package_delta in delta.package_deltas:
            if package_delta.action not in {DeltaAction.INSTALL, DeltaAction.UPGRADE}:
                continue
            executor_action_id = "install_python_package"
            self._require_capability(executor_action_id)
            package = package_delta.package_name
            requirement = package
            if package_delta.desired_version:
                requirement = f"{package}{package_delta.desired_version}"
            actions.append(
                ExecutionPlanAction(
                    action_id=self._instance_action_id(executor_action_id, package),
                    description=f"Install Python package {package}",
                    priority=2,
                    context={
                        "executor_action_id": executor_action_id,
                        "package": package,
                        "requirement": requirement,
                        "package_name": package,
                        "version_constraint": package_delta.desired_version,
                        "actual_version": package_delta.actual_version,
                        "reason": package_delta.reason,
                    },
                )
            )

        actions = self._deduplicate(actions)
        summary = (
            "No actions required."
            if not actions
            else f"Prepared {len(actions)} validated execution action(s)."
        )
        return ExecutionPlan(bool(actions), actions, summary=summary)

    def _resolve_action_id(self, tool_id: str, strategy_name: str) -> str:
        direct_action = self._TOOL_ACTIONS.get(tool_id)
        if direct_action:
            return direct_action
        action_id = self._STRATEGY_ACTIONS.get(strategy_name)
        if action_id:
            return action_id
        raise ValueError(
            f"No executor action is registered for tool '{tool_id}' and strategy '{strategy_name}'."
        )

    @staticmethod
    def _instance_action_id(executor_action_id: str, subject: str) -> str:
        """Return a stable per-action instance ID for approval and evidence."""
        return f"{executor_action_id}:{subject}"

    def _require_capability(self, action_id: str) -> None:
        if not self._capabilities.find_by_action(action_id):
            raise ValueError(
                f"Executor action '{action_id}' is not registered in the capability catalog."
            )

    @staticmethod
    def _pip_context(
        tool_id: str, strategy_args: dict, version: str | None
    ) -> dict[str, str]:
        package = str(
            strategy_args.get("package_name") or strategy_args.get("package") or tool_id
        ).strip()
        requirement = str(strategy_args.get("requirement") or package).strip()
        if version and requirement == package:
            requirement = f"{package}{version}"
        return {"package": package, "requirement": requirement}

    @staticmethod
    def _priority(risk_level: str) -> int:
        return {"critical": 1, "high": 2, "medium": 3, "low": 4}.get(risk_level, 5)

    @staticmethod
    def _deduplicate(actions: list[ExecutionPlanAction]) -> list[ExecutionPlanAction]:
        seen: set[tuple[str, str]] = set()
        result: list[ExecutionPlanAction] = []
        for action in actions:
            key = (action.action_id, str(action.context))
            if key in seen:
                continue
            seen.add(key)
            result.append(action)
        return result


__all__ = ["ExecutionPlanBuilder"]

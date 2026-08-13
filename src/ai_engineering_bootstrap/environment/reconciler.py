"""Environment reconciliation service for AI Engineering Bootstrap."""

from __future__ import annotations

from ai_engineering_bootstrap.environment.models import (
    ActualEnvironmentState,
    DeltaAction,
    DesiredEnvironmentState,
    EnvironmentDelta,
    PackageDelta,
    ToolDelta,
    ToolRequirementLevel,
    ToolStatus,
)


class EnvironmentReconciler:
    """
    Compute deterministic delta between actual and desired environment states.

    This reconciler performs purely deterministic comparison logic.
    LLM is NOT involved in calculating basic state differences.
    """

    def reconcile(
        self,
        actual: ActualEnvironmentState,
        desired: DesiredEnvironmentState,
    ) -> EnvironmentDelta:
        """
        Compute the delta between actual and desired states.

        Returns an EnvironmentDelta containing all required changes.
        """
        tool_deltas = self._reconcile_tools(actual.tools, desired.tools)
        package_deltas = self._reconcile_packages(
            actual.python_packages,
            desired.python_packages,
        )
        configuration_deltas = self._reconcile_configurations(
            actual.system_info,
            desired.configurations,
        )

        return EnvironmentDelta(
            tool_deltas=tool_deltas,
            package_deltas=package_deltas,
            configuration_deltas=configuration_deltas,
        )

    def _reconcile_tools(
        self,
        actual_tools: dict[str, ToolStatus],
        desired_tools: dict[str, ToolRequirement],
    ) -> list[ToolDelta]:
        """Reconcile tool states deterministically."""
        deltas: list[ToolDelta] = []

        # Check all desired tools
        for tool_id, requirement in desired_tools.items():
            actual_status = actual_tools.get(tool_id)

            if actual_status is None:
                # Tool is missing
                if requirement.level == ToolRequirementLevel.REQUIRED:
                    deltas.append(
                        ToolDelta(
                            tool_id=tool_id,
                            action=DeltaAction.INSTALL,
                            desired_requirement=requirement,
                            actual_status=None,
                            reason=f"Required tool '{tool_id}' is not installed",
                        )
                    )
                elif requirement.level == ToolRequirementLevel.OPTIONAL:
                    deltas.append(
                        ToolDelta(
                            tool_id=tool_id,
                            action=DeltaAction.INSTALL,
                            desired_requirement=requirement,
                            actual_status=None,
                            reason=f"Optional tool '{tool_id}' is not installed",
                        )
                    )
            else:
                # Tool exists, check version/constraints
                if requirement.version_constraint and actual_status.version:
                    if not self._version_satisfies(
                        actual_status.version,
                        requirement.version_constraint,
                    ):
                        deltas.append(
                            ToolDelta(
                                tool_id=tool_id,
                                action=DeltaAction.UPGRADE,
                                desired_requirement=requirement,
                                actual_status=actual_status,
                                reason=f"Tool '{tool_id}' version {actual_status.version} does not satisfy {requirement.version_constraint}",
                            )
                        )
                elif actual_status.status == "error" or actual_status.health == "broken":
                    deltas.append(
                        ToolDelta(
                            tool_id=tool_id,
                            action=DeltaAction.INSTALL,
                            desired_requirement=requirement,
                            actual_status=actual_status,
                            reason=f"Tool '{tool_id}' is in broken state",
                        )
                    )

        # Check for tools that should be absent
        for tool_id, actual_status in actual_tools.items():
            if tool_id not in desired_tools:
                continue  # Unknown tools are left alone by default

            requirement = desired_tools.get(tool_id)
            if requirement and requirement.level == ToolRequirementLevel.ABSENT:
                deltas.append(
                    ToolDelta(
                        tool_id=tool_id,
                        action=DeltaAction.REMOVE,
                        desired_requirement=requirement,
                        actual_status=actual_status,
                        reason=f"Tool '{tool_id}' should be removed",
                    )
                )

        return deltas

    def _reconcile_packages(
        self,
        actual_packages: dict[str, str],
        desired_packages: list,
    ) -> list[PackageDelta]:
        """Reconcile Python package states deterministically."""
        deltas: list[PackageDelta] = []

        for pkg_req in desired_packages:
            pkg_name = pkg_req.name.lower()
            actual_version = actual_packages.get(pkg_name)

            if actual_version is None:
                deltas.append(
                    PackageDelta(
                        package_name=pkg_req.name,
                        action=DeltaAction.INSTALL,
                        desired_version=pkg_req.version_constraint,
                        actual_version=None,
                        reason=f"Package '{pkg_req.name}' is not installed",
                    )
                )
            elif pkg_req.version_constraint and not self._version_satisfies(actual_version, pkg_req.version_constraint):
                    deltas.append(
                        PackageDelta(
                            package_name=pkg_req.name,
                            action=DeltaAction.UPGRADE,
                            desired_version=pkg_req.version_constraint,
                            actual_version=actual_version,
                            reason=f"Package '{pkg_req.name}' version {actual_version} does not satisfy {pkg_req.version_constraint}",
                        )
                    )

        return deltas

    def _reconcile_configurations(
        self,
        actual_system: dict,
        desired_configs: dict,
    ) -> dict:
        """Reconcile configuration states."""
        # For MVP, configurations are passed through as deltas
        # A more sophisticated implementation would compare actual vs desired
        return desired_configs

    def _version_satisfies(self, actual: str, constraint: str) -> bool:
        """
        Check if an actual version satisfies a constraint.

        For MVP, this is a simple equality check.
        A full implementation would use packaging.version and specifiers.
        """
        # Simple MVP implementation: exact match or starts-with for >= constraints
        if constraint.startswith(">="):
            target = constraint[2:].strip()
            return self._compare_versions(actual, target) >= 0
        elif constraint.startswith("<="):
            target = constraint[2:].strip()
            return self._compare_versions(actual, target) <= 0
        elif constraint.startswith("=="):
            target = constraint[2:].strip()
            return actual == target
        else:
            return actual == constraint

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
        except ValueError:
            # Fall back to string comparison
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            return 0

        # Pad shorter version with zeros
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        return 0


__all__ = ["EnvironmentReconciler"]

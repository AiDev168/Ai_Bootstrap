"""Environment models for AI Engineering Bootstrap."""

from .models import (
    EnvironmentRequest,
    DesiredEnvironmentState,
    ActualEnvironmentState,
    ToolRequirement,
    ToolRequirementLevel,
    ToolStatus,
    PythonPackageRequirement,
    EnvironmentDelta,
    ToolDelta,
    PackageDelta,
    DeltaAction,
)
from .reconciler import EnvironmentReconciler
from .session_models import SessionStatus, EnvironmentSession, SessionEvent, AgentDecision
from .session_store import SessionStore
from .tool_catalog import (
    ToolCatalog,
    ToolDefinition,
    Platform,
    Architecture,
    ArtifactFormat,
    PrivilegeLevel,
    RiskLevel,
    InstallationStrategy,
    ProbeDefinition,
    get_tool_catalog,
    DuplicateToolError,
)
from .installation_strategies import (
    InstallationStrategyBase,
    DebInstallStrategy,
    PipInstallStrategy,
    BinaryInstallStrategy,
    StrategyFactory,
    ArtifactMetadata,
    InstallationResult,
    get_current_platform,
)

__all__ = [
    # Models
    "EnvironmentRequest",
    "DesiredEnvironmentState",
    "ActualEnvironmentState",
    "ToolRequirement",
    "ToolRequirementLevel",
    "ToolStatus",
    "PythonPackageRequirement",
    "EnvironmentDelta",
    "ToolDelta",
    "PackageDelta",
    "DeltaAction",
    # Session
    "SessionStatus",
    "EnvironmentSession",
    "SessionEvent",
    "AgentDecision",
    "SessionStore",
    # Reconciliation
    "EnvironmentReconciler",
    # Tool Catalog
    "ToolCatalog",
    "ToolDefinition",
    "Platform",
    "Architecture",
    "ArtifactFormat",
    "PrivilegeLevel",
    "RiskLevel",
    "InstallationStrategy",
    "ProbeDefinition",
    "get_tool_catalog",
    # Installation Strategies
    "InstallationStrategyBase",
    "DebInstallStrategy",
    "PipInstallStrategy",
    "BinaryInstallStrategy",
    "StrategyFactory",
    "ArtifactMetadata",
    "InstallationResult",
    "get_current_platform",
]

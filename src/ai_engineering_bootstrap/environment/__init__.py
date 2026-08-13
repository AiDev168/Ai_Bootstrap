"""Environment models for AI Engineering Bootstrap."""

from .installation_strategies import (
    ArtifactMetadata,
    BinaryInstallStrategy,
    DebInstallStrategy,
    InstallationResult,
    InstallationStrategyBase,
    PipInstallStrategy,
    StrategyFactory,
    get_current_platform,
)
from .models import (
    ActualEnvironmentState,
    DeltaAction,
    DesiredEnvironmentState,
    EnvironmentDelta,
    EnvironmentRequest,
    PackageDelta,
    PythonPackageRequirement,
    ToolDelta,
    ToolRequirement,
    ToolRequirementLevel,
    ToolStatus,
)
from .reconciler import EnvironmentReconciler
from .session_models import (
    AgentDecision,
    EnvironmentSession,
    SessionEvent,
    SessionStatus,
)
from .session_store import SessionStore
from .tool_catalog import (
    Architecture,
    ArtifactFormat,
    DuplicateToolError,
    InstallationStrategy,
    Platform,
    PrivilegeLevel,
    ProbeDefinition,
    RiskLevel,
    ToolCatalog,
    ToolDefinition,
    get_tool_catalog,
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

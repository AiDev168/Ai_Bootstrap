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
from .session_models import (
    EnvironmentSession,
    SessionStatus,
    AgentDecision,
    SessionEvent,
    ActionApprovalState,
    ExecutionEvidence,
    RecoveryRecord,
)
from .session_store import (
    SessionStore,
    InMemorySessionStore,
    JSONSessionStore,
    get_session_store,
    set_session_store,
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
    # Session
    "EnvironmentSession",
    "SessionStatus",
    "AgentDecision",
    "SessionEvent",
    "ActionApprovalState",
    "ExecutionEvidence",
    "RecoveryRecord",
    # Session Store
    "SessionStore",
    "InMemorySessionStore",
    "JSONSessionStore",
    "get_session_store",
    "set_session_store",
]

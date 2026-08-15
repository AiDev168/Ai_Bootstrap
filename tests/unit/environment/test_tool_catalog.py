"""Tests for Phase 2: Tool Catalog and Installation Strategies."""

import platform as platform_module

import pytest

from ai_engineering_bootstrap.environment import (
    Architecture,
    ArtifactFormat,
    DebInstallStrategy,
    DuplicateToolError,
    InstallationResult,
    PipInstallStrategy,
    Platform,
    PrivilegeLevel,
    RiskLevel,
    StrategyFactory,
    ToolCatalog,
    get_current_platform,
    get_tool_catalog,
)
from ai_engineering_bootstrap.environment.installation_strategies import (
    ArtifactMetadata,
    ArtifactValidationError,
    StrategyStatus,
)


class TestToolCatalog:
    """Test ToolCatalog functionality."""

    def test_default_catalog_has_tools(self) -> None:
        """Test that default catalog is populated."""
        catalog = get_tool_catalog()
        tools = catalog.list_tools()
        assert len(tools) > 0

        # Check expected tools exist
        tool_ids = [t.tool_id for t in tools]
        assert "python" in tool_ids
        assert "git" in tool_ids
        assert "cursor" in tool_ids
        assert "docker" in tool_ids
        assert "ruff" in tool_ids
        assert "pytest" in tool_ids

    def test_get_tool_by_id(self) -> None:
        """Test retrieving a tool by ID."""
        catalog = ToolCatalog()
        cursor = catalog.get("cursor")

        assert cursor is not None
        assert cursor.tool_id == "cursor"
        assert cursor.display_name == "Cursor"
        assert cursor.risk_level == RiskLevel.MEDIUM
        assert cursor.privilege_level == PrivilegeLevel.SYSTEM

    def test_list_tools_deterministic_order(self) -> None:
        """Test that tools are listed in deterministic order."""
        catalog = ToolCatalog()
        tools = catalog.list_tools()
        tool_ids = [t.tool_id for t in tools]

        assert tool_ids == sorted(tool_ids)

    def test_register_duplicate_tool_raises_error(self) -> None:
        """Test that registering a duplicate tool raises error."""
        catalog = ToolCatalog()
        tool = catalog.get("python")

        with pytest.raises(DuplicateToolError):
            catalog.register(tool)

    def test_find_by_platform(self) -> None:
        """Test finding tools by platform."""
        catalog = ToolCatalog()
        linux_tools = catalog.find_by_platform(Platform.LINUX)

        assert len(linux_tools) > 0
        # All tools should support Linux in our catalog
        for tool in linux_tools:
            assert Platform.LINUX in tool.platforms

    def test_get_installation_strategy(self) -> None:
        """Test getting installation strategy for a tool."""
        catalog = ToolCatalog()

        # Ruff uses pip on Linux
        strategy = catalog.get_installation_strategy(
            "ruff", Platform.LINUX, Architecture.X86_64
        )
        assert strategy is not None
        assert strategy.artifact_format == ArtifactFormat.PIP

        # Cursor uses DEB on Linux x86_64
        strategy = catalog.get_installation_strategy(
            "cursor", Platform.LINUX, Architecture.X86_64
        )
        assert strategy is not None
        assert strategy.artifact_format == ArtifactFormat.DEB


class TestToolDefinition:
    """Test ToolDefinition model."""

    def test_cursor_tool_definition(self) -> None:
        """Test Cursor tool definition."""
        catalog = get_tool_catalog()
        cursor = catalog.get("cursor")

        assert cursor.tool_id == "cursor"
        assert cursor.description != ""
        assert Platform.LINUX in cursor.platforms
        assert Platform.MACOS in cursor.platforms
        assert Architecture.X86_64 in cursor.architectures
        assert cursor.version_probe is not None
        assert len(cursor.installation_strategies) >= 1
        assert "cursor.com" in cursor.allowed_domains

    def test_ruff_tool_definition(self) -> None:
        """Test Ruff tool definition."""
        catalog = get_tool_catalog()
        ruff = catalog.get("ruff")

        assert ruff.tool_id == "ruff"
        assert ruff.privilege_level == PrivilegeLevel.USER
        assert ruff.risk_level == RiskLevel.LOW
        assert "pypi.org" in ruff.allowed_domains


class TestInstallationStrategies:
    """Test installation strategy implementations."""

    def test_deb_strategy_discover_artifact(self) -> None:
        """Test DEB strategy artifact discovery."""
        catalog = get_tool_catalog()
        cursor = catalog.get("cursor")
        strategy_def = catalog.get_installation_strategy(
            "cursor", Platform.LINUX, Architecture.X86_64
        )

        assert strategy_def is not None
        installer = DebInstallStrategy(strategy_def, cursor)

        metadata = installer.discover_artifact()

        # Source domain should be from the URL (www.cursor.com or downloads.cursor.com)
        assert metadata.source_domain in ["www.cursor.com", "downloads.cursor.com"]
        assert metadata.format == ArtifactFormat.DEB
        assert metadata.trust_level == "official"

    def test_pip_strategy_discover_artifact(self) -> None:
        """Test PIP strategy artifact discovery."""
        catalog = get_tool_catalog()
        ruff = catalog.get("ruff")
        strategy_def = catalog.get_installation_strategy(
            "ruff", Platform.LINUX, Architecture.X86_64
        )

        assert strategy_def is not None
        installer = PipInstallStrategy(strategy_def, ruff)

        metadata = installer.discover_artifact()

        assert metadata.source_domain == "pypi.org"
        assert metadata.format == ArtifactFormat.PIP
        assert metadata.trust_level == "official"

    def test_deb_strategy_validate_artifact(self) -> None:
        """Test DEB strategy artifact validation."""
        catalog = get_tool_catalog()
        cursor = catalog.get("cursor")
        strategy_def = catalog.get_installation_strategy(
            "cursor", Platform.LINUX, Architecture.X86_64
        )

        installer = DebInstallStrategy(strategy_def, cursor)
        metadata = installer.discover_artifact()

        # Valid metadata should pass
        assert installer.validate_artifact(metadata) is True

    def test_deb_strategy_rejects_unofficial_source(self) -> None:
        """Test that DEB strategy rejects unofficial sources."""
        catalog = get_tool_catalog()
        cursor = catalog.get("cursor")
        strategy_def = catalog.get_installation_strategy(
            "cursor", Platform.LINUX, Architecture.X86_64
        )

        installer = DebInstallStrategy(strategy_def, cursor)

        # Create metadata with unofficial source
        bad_metadata = ArtifactMetadata(
            source_url="https://evil.com/cursor.deb",
            source_domain="evil.com",
            platform=Platform.LINUX,
            architecture=Architecture.X86_64,
            format=ArtifactFormat.DEB,
            trust_level="unknown",
        )

        with pytest.raises(ArtifactValidationError):
            installer.validate_artifact(bad_metadata)

    def test_pip_strategy_validates_pypi_source(self) -> None:
        """Test that PIP strategy validates PyPI source."""
        catalog = get_tool_catalog()
        ruff = catalog.get("ruff")
        strategy_def = catalog.get_installation_strategy(
            "ruff", Platform.LINUX, Architecture.X86_64
        )

        installer = PipInstallStrategy(strategy_def, ruff)

        # Create metadata with non-PyPI source
        bad_metadata = ArtifactMetadata(
            source_url="https://evil.com/ruff.whl",
            source_domain="evil.com",
            platform=Platform.LINUX,
            architecture=Architecture.X86_64,
            format=ArtifactFormat.PIP,
            trust_level="unknown",
        )

        with pytest.raises(ArtifactValidationError):
            installer.validate_artifact(bad_metadata)

    def test_dry_run_skips_installation(self) -> None:
        """Test that dry run skips actual installation."""
        catalog = get_tool_catalog()
        ruff = catalog.get("ruff")
        strategy_def = catalog.get_installation_strategy(
            "ruff", Platform.LINUX, Architecture.X86_64
        )

        installer = PipInstallStrategy(strategy_def, ruff)
        metadata = installer.discover_artifact()

        result = installer.install(metadata, dry_run=True)

        assert result.status == StrategyStatus.SKIPPED
        assert "Dry run" in result.message


class TestStrategyFactory:
    """Test StrategyFactory."""

    def test_creates_deb_strategy(self) -> None:
        """Test factory creates DEB strategy."""
        catalog = get_tool_catalog()
        cursor = catalog.get("cursor")
        strategy_def = catalog.get_installation_strategy(
            "cursor", Platform.LINUX, Architecture.X86_64
        )

        installer = StrategyFactory.create_strategy(strategy_def, cursor)

        assert isinstance(installer, DebInstallStrategy)

    def test_creates_pip_strategy(self) -> None:
        """Test factory creates PIP strategy."""
        catalog = get_tool_catalog()
        ruff = catalog.get("ruff")
        strategy_def = catalog.get_installation_strategy(
            "ruff", Platform.LINUX, Architecture.X86_64
        )

        installer = StrategyFactory.create_strategy(strategy_def, ruff)

        assert isinstance(installer, PipInstallStrategy)


class TestPlatformDetection:
    """Test platform detection utilities."""

    def test_get_current_platform_returns_tuple(self) -> None:
        """Test platform detection returns correct types."""
        plat, arch = get_current_platform()

        assert isinstance(plat, Platform)
        assert isinstance(arch, Architecture)

    def test_get_current_platform_matches_system(self) -> None:
        """Test platform detection matches system."""
        plat, arch = get_current_platform()

        system = platform_module.system().lower()
        machine = platform_module.machine().lower()

        if system == "linux":
            assert plat == Platform.LINUX
        elif system == "darwin":
            assert plat == Platform.MACOS

        if machine in ("x86_64", "amd64"):
            assert arch == Architecture.X86_64
        elif machine in ("arm64", "aarch64"):
            assert arch in (Architecture.ARM64, Architecture.AARCH64)


class TestArtifactMetadata:
    """Test ArtifactMetadata model."""

    def test_official_trust_level_for_allowed_domains(self) -> None:
        """Test official trust level assignment."""
        catalog = get_tool_catalog()
        cursor = catalog.get("cursor")
        strategy_def = catalog.get_installation_strategy(
            "cursor", Platform.LINUX, Architecture.X86_64
        )

        installer = DebInstallStrategy(strategy_def, cursor)
        metadata = installer.discover_artifact()

        assert metadata.trust_level == "official"


class TestInstallationResult:
    """Test InstallationResult model."""

    def test_result_contains_strategy_and_tool(self) -> None:
        """Test result contains required identifiers."""
        result = InstallationResult(
            strategy_id="test_strategy",
            tool_id="test_tool",
            status=StrategyStatus.SUCCESS,
            message="Test successful",
        )

        assert result.strategy_id == "test_strategy"
        assert result.tool_id == "test_tool"
        assert result.status == StrategyStatus.SUCCESS
        assert result.verification_passed is False  # Default


class TestIntegrationWithReconciler:
    """Test integration between Tool Catalog and Reconciler."""

    def test_catalog_provides_strategies_for_delta_actions(self) -> None:
        """Test that catalog can provide strategies for reconciliation deltas."""
        from ai_engineering_bootstrap.environment import (
            ActualEnvironmentState,
            DesiredEnvironmentState,
            EnvironmentReconciler,
            ToolRequirement,
            ToolRequirementLevel,
            ToolStatus,
        )

        catalog = get_tool_catalog()
        reconciler = EnvironmentReconciler()

        # Create desired state with missing tools
        desired = DesiredEnvironmentState(
            tools={
                "ruff": ToolRequirement(
                    tool_id="ruff", level=ToolRequirementLevel.REQUIRED
                ),
                "pytest": ToolRequirement(
                    tool_id="pytest", level=ToolRequirementLevel.REQUIRED
                ),
            }
        )

        # Create actual state without those tools
        actual = ActualEnvironmentState(
            tools={
                "python": ToolStatus(
                    tool_id="python", status="installed", version="3.12.0"
                ),
            }
        )

        delta = reconciler.reconcile(actual, desired)

        # Should have install actions for missing tools
        assert delta.has_changes
        assert delta.required_actions_count >= 2

        # Verify we can get strategies for the deltas
        for tool_delta in delta.tool_deltas:
            if tool_delta.action.value == "install":
                strategy = catalog.get_installation_strategy(
                    tool_delta.tool_id, Platform.LINUX, Architecture.X86_64
                )
                # Strategy should exist for known tools
                if tool_delta.tool_id in ["ruff", "pytest"]:
                    assert strategy is not None

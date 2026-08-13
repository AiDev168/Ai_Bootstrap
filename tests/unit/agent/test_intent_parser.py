"""Tests for LLM-powered intent parsing."""

import pytest

from ai_engineering_bootstrap.agent.intent_parser import IntentParser, ParsedIntent
from ai_engineering_bootstrap.agent.provider import MockProvider


class TestParsedIntent:
    """Test ParsedIntent dataclass."""

    def test_create_empty_intent(self) -> None:
        """Test creating empty parsed intent."""
        intent = ParsedIntent()
        assert intent.natural_language_goal == ""
        assert intent.required_tools == []
        assert intent.optional_tools == []
        assert intent.confidence == 0.0

    def test_create_intent_with_data(self) -> None:
        """Test creating intent with data."""
        intent = ParsedIntent(
            natural_language_goal="Set up Python environment",
            required_tools=["python", "git"],
            optional_tools=["docker"],
            languages=["python"],
            frameworks=["fastapi"],
            project_dependencies=["uvicorn"],
            constraints=["no_root_required"],
            confidence=0.95,
        )
        assert len(intent.required_tools) == 2
        assert len(intent.optional_tools) == 1
        assert intent.confidence == 0.95

    def test_to_environment_request(self) -> None:
        """Test converting to EnvironmentRequest."""
        intent = ParsedIntent(
            natural_language_goal="Python AI environment",
            required_tools=["python", "pytest"],
            optional_tools=["black"],
            frameworks=["pytorch"],
        )
        request = intent.to_environment_request(
            project_path="/tmp/test-project",
            project_id="test-123",
        )
        assert request.project_path == "/tmp/test-project"
        assert request.project_id == "test-123"
        assert "python" in request.required_tools
        assert "pytest" in request.required_tools
        assert "black" in request.optional_tools


class TestIntentParserDeterministic:
    """Test deterministic intent parsing."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = IntentParser(provider=None)

    def test_parse_simple_python_request(self) -> None:
        """Test parsing simple Python environment request."""
        text = "I need a Python environment for development"
        intent = self.parser.parse(text)

        assert "python" in intent.required_tools
        assert intent.languages == ["python"]
        assert intent.confidence == 0.7

    def test_parse_ai_ml_request(self) -> None:
        """Test parsing AI/ML environment request."""
        text = "Set up machine learning environment with PyTorch"
        intent = self.parser.parse(text)

        assert "python" in intent.required_tools
        assert "pytorch" in intent.frameworks
        assert "transformers" in intent.frameworks

    def test_parse_fastapi_request(self) -> None:
        """Test parsing FastAPI environment request."""
        text = "Prepare FastAPI project environment"
        intent = self.parser.parse(text)

        assert "python" in intent.required_tools
        assert "fastapi" in intent.frameworks
        assert "pytest" in intent.required_tools
        assert "uvicorn" in intent.project_dependencies

    def test_parse_constraints(self) -> None:
        """Test parsing constraint specifications."""
        text = "Setup without root access using virtualenv"
        intent = self.parser.parse(text)

        assert "no_root_required" in intent.constraints
        assert "use_virtualenv" in intent.constraints

    def test_parse_multiple_tools(self) -> None:
        """Test parsing multiple tool mentions."""
        text = "Install python, git, docker, ruff, and black"
        intent = self.parser.parse(text)

        assert "python" in intent.required_tools
        assert "git" in intent.required_tools
        assert "docker" in intent.required_tools
        assert "ruff" in intent.required_tools
        assert "black" in intent.required_tools

    def test_parse_javascript_typescript(self) -> None:
        """Test parsing JS/TS language requests."""
        text = "JavaScript and TypeScript development environment"
        intent = self.parser.parse(text)

        assert "javascript" in intent.languages
        assert "typescript" in intent.languages


class TestIntentParserWithLLM:
    """Test intent parsing with LLM provider."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        provider = MockProvider()
        self.parser = IntentParser(provider=provider)

    def test_parse_with_mock_provider(self) -> None:
        """Test parsing with mock LLM provider."""
        text = "Python environment for AI development"
        intent = self.parser.parse(text)

        # Should return some result (may fallback to deterministic)
        assert isinstance(intent, ParsedIntent)
        assert intent.natural_language_goal == text

    def test_fallback_on_llm_failure(self) -> None:
        """Test fallback to deterministic on LLM failure."""
        # MockProvider will fail for non-fix contexts
        text = "Setup environment"
        intent = self.parser.parse(text)

        # Should still return valid intent via fallback
        assert isinstance(intent, ParsedIntent)


class TestIntentParserEdgeCases:
    """Test edge cases in intent parsing."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = IntentParser(provider=None)

    def test_empty_input(self) -> None:
        """Test parsing empty input."""
        intent = self.parser.parse("")
        assert isinstance(intent, ParsedIntent)
        assert intent.required_tools == []

    def test_unknown_tools(self) -> None:
        """Test parsing with unknown tool names."""
        text = "Install weirdtool123 and unknownpkg"
        intent = self.parser.parse(text)

        # Should not match unknown tools
        assert "weirdtool123" not in intent.required_tools
        assert "unknownpkg" not in intent.required_tools

    def test_case_insensitive(self) -> None:
        """Test case-insensitive parsing."""
        text = "PYTHON and FASTAPI environment"
        intent = self.parser.parse(text)

        assert "python" in intent.required_tools
        assert "fastapi" in intent.frameworks

    def test_very_long_input(self) -> None:
        """Test parsing very long input."""
        text = "I need a comprehensive development environment with " * 100
        text += "python, git, and docker for sure"
        intent = self.parser.parse(text)

        assert "python" in intent.required_tools
        assert "git" in intent.required_tools
        assert "docker" in intent.required_tools

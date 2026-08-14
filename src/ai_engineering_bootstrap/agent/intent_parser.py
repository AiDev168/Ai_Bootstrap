"""LLM-powered intent parsing for natural language environment requests."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ai_engineering_bootstrap.agent.provider import LLMProvider
from ai_engineering_bootstrap.agent.strategy_llm_bridge import StrategyLLMProvider
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog


@dataclass
class ParsedIntent:
    """Structured intent extracted from natural language."""

    natural_language_goal: str = ""
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    project_dependencies: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    platform_preferences: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_summary: str = ""

    def to_environment_request(
        self, project_path: str, project_id: str | None = None
    ) -> EnvironmentRequest:
        """Convert parsed intent into a structured EnvironmentRequest."""
        return EnvironmentRequest(
            request_id="",
            project_id=project_id or "",
            project_path=project_path,
            natural_language_goal=self.natural_language_goal,
            required_tools=self.required_tools,
            optional_tools=self.optional_tools,
            languages=self.languages,
            frameworks=self.frameworks,
            project_dependencies=self.project_dependencies,
            configurations={},
            constraints=self.constraints,
            platform_preferences=self.platform_preferences,
            user_preferences={},
        )


class IntentParser:
    """Parse natural language into structured environment requests."""

    def __init__(
        self,
        provider: LLMProvider | None = None,
        tool_catalog: ToolCatalog | None = None,
    ) -> None:
        self.provider = provider
        self.tool_catalog = tool_catalog
        self._known_tools = (
            {tool.tool_id for tool in tool_catalog.list_tools()}
            if tool_catalog
            else {
                "python",
                "git",
                "cursor",
                "docker",
                "ruff",
                "black",
                "pytest",
                "github-cli",
                "nodejs",
                "npm",
                "uv",
                "poetry",
            }
        )
        self._known_frameworks = {
            "fastapi",
            "flask",
            "django",
            "pytorch",
            "tensorflow",
            "transformers",
            "langchain",
            "llama-index",
            "react",
            "vue",
            "angular",
        }

    def is_llm_available(self) -> bool:
        """Check if an LLM provider is configured."""
        return self.provider is not None

    def parse(self, natural_language: str) -> ParsedIntent:
        """Parse a natural-language goal into structured intent."""
        if not self.provider:
            return self._deterministic_parse(natural_language)
        try:
            return self._llm_parse(natural_language)
        except Exception as error:  # noqa: BLE001 - provider boundary must preserve a usable fallback
            fallback = self._deterministic_parse(natural_language)
            fallback.reasoning_summary = f"Deterministic fallback after LLM failure: {type(error).__name__}: {error}"
            fallback.confidence = min(fallback.confidence, 0.55)
            return fallback

    def _llm_parse(self, natural_language: str) -> ParsedIntent:
        """Use the configured provider through the structured JSON bridge."""
        decision = StrategyLLMProvider(
            self.provider,
            system_prompt=(
                "You are an intent parser for engineering environment setup. "
                "Return ONLY valid JSON matching the requested intent schema."
            ),
        ).decide(self._build_prompt(natural_language), [])
        parsed = json.loads(decision.reasoning_summary.strip())
        if not isinstance(parsed, dict):
            raise TypeError("LLM intent response must be an object.")
        return ParsedIntent(
            natural_language_goal=parsed.get("natural_language_goal", natural_language),
            required_tools=[
                tool
                for tool in parsed.get("required_tools", [])
                if tool in self._known_tools
            ],
            optional_tools=[
                tool
                for tool in parsed.get("optional_tools", [])
                if tool in self._known_tools
            ],
            languages=list(parsed.get("languages", [])),
            frameworks=list(parsed.get("frameworks", [])),
            project_dependencies=list(parsed.get("project_dependencies", [])),
            constraints=list(parsed.get("constraints", [])),
            platform_preferences=list(parsed.get("platform_preferences", [])),
            confidence=decision.confidence,
            reasoning_summary="LLM-parsed intent",
        )

    def _deterministic_parse(self, natural_language: str) -> ParsedIntent:
        """Deterministic fallback parsing using keyword matching."""
        text_lower = natural_language.lower()
        required_tools = [tool for tool in self._known_tools if tool in text_lower]
        optional_tools: list[str] = []
        languages: list[str] = []
        frameworks = [
            framework for framework in self._known_frameworks if framework in text_lower
        ]
        dependencies: list[str] = []
        constraints: list[str] = []
        if "python" in text_lower:
            languages.append("python")
        if "javascript" in text_lower or " js " in f" {text_lower} ":
            languages.append("javascript")
        if "typescript" in text_lower or " ts " in f" {text_lower} ":
            languages.append("typescript")
        if "no sudo" in text_lower or "without root" in text_lower:
            constraints.append("no_root_required")
        if "virtualenv" in text_lower or "venv" in text_lower:
            constraints.append("use_virtualenv")
        if "isolated" in text_lower:
            constraints.append("isolated_environment")
        if "ai" in text_lower or "ml" in text_lower or "machine learning" in text_lower:
            if "python" not in required_tools:
                required_tools.append("python")
            if "pytorch" not in frameworks and "tensorflow" not in frameworks:
                frameworks.append("pytorch")
            if "transformers" not in frameworks:
                frameworks.append("transformers")
        if "fastapi" in text_lower:
            if "python" not in required_tools:
                required_tools.append("python")
            if "uvicorn" not in dependencies:
                dependencies.append("uvicorn")
            if "pytest" not in required_tools:
                required_tools.append("pytest")
        return ParsedIntent(
            natural_language_goal=natural_language,
            required_tools=required_tools,
            optional_tools=optional_tools,
            languages=languages,
            frameworks=frameworks,
            project_dependencies=dependencies,
            constraints=constraints,
            confidence=0.7,
            reasoning_summary="Deterministic keyword-based parsing",
        )

    def _build_prompt(self, natural_language: str) -> str:
        """Build the JSON contract used for intent extraction."""
        return f"""You are an intent parser for engineering environment setup.
Given a natural language goal, extract required tools, optional tools, languages, frameworks, project dependencies, constraints, and platform preferences.
Use only tool IDs from this catalog: {sorted(self._known_tools)}.
Return ONLY valid JSON with this exact shape:
{{
  "natural_language_goal": "...",
  "required_tools": ["tool1", "tool2"],
  "optional_tools": ["tool3"],
  "languages": ["python"],
  "frameworks": ["fastapi"],
  "project_dependencies": ["package1"],
  "constraints": ["no_root_required"],
  "platform_preferences": ["linux"]
}}
User goal: {natural_language}
/no_think"""


__all__ = ["IntentParser", "ParsedIntent"]

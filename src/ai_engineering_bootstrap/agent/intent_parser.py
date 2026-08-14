"""LLM-powered intent parsing for natural language environment requests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ai_engineering_bootstrap.agent.provider import LLMProvider
from ai_engineering_bootstrap.agent.strategy_llm_bridge import StrategyLLMProvider
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog


_TOOL_ALIASES = {
    "cursor": {"cursor"},
    "git": {"git", "گیت"},
    "docker": {"docker", "داکر"},
    "ruff": {"ruff", "روف", "رووف", "راف"},
    "pytest": {"pytest", "py test", "پایتست", "پای تست", "پی‌تست"},
    "black": {"black", "بلک"},
    "github-cli": {"github-cli", "gh"},
    "nodejs": {"node", "nodejs", "نود"},
    "npm": {"npm", "ان پی ام"},
    "uv": {"uv"},
    "poetry": {"poetry", "پواتری"},
    "python": {"python", "python3", "پایتون"},
}

_POSITIVE_VERBS = re.compile(
    r"\b(?:install|reinstall|setup|set up|add|نصب|نصب کن|نصب کنید|راه[ -]?اندازی)\b",
    re.IGNORECASE,
)
_NEGATION = re.compile(
    r"(?:\bdon['’]?t\b|\bdo not\b|\bdont\b|\bnever\b|\bavoid\b|\bwithout\b|"
    r"نصب\s+نکن(?:ید|م)?|نصب\s+نشود|نمی[‌ ]?(?:خوام|خواهم)|نیازی\s+به\s+نصب)",
    re.IGNORECASE,
)
_TOKEN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.+-]*(?:\s*(?:===|==|!=|~=|>=|<=|>|<)\s*[A-Za-z0-9][A-Za-z0-9+_.!-]*)?$"
)


@dataclass
class ParsedIntent:
    """Structured semantic intent extracted from natural language."""

    natural_language_goal: str = ""
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    excluded_tools: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    project_dependencies: list[str] = field(default_factory=list)
    excluded_packages: list[str] = field(default_factory=list)
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
            excluded_tools=self.excluded_tools,
            languages=self.languages,
            frameworks=self.frameworks,
            project_dependencies=self.project_dependencies,
            excluded_packages=self.excluded_packages,
            configurations={},
            constraints={constraint: True for constraint in self.constraints},
            platform_preferences={"preferences": self.platform_preferences}
            if self.platform_preferences
            else {},
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
            else set(_TOOL_ALIASES)
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
        """Return whether a semantic LLM provider is configured."""
        return self.provider is not None

    def parse(self, natural_language: str) -> ParsedIntent:
        """Parse a natural-language goal, using LLM semantics with safe fallback."""
        if not natural_language.strip():
            return ParsedIntent(reasoning_summary="Empty intent")
        if not self.provider:
            return self._deterministic_parse(natural_language)
        try:
            return self._llm_parse(natural_language)
        except Exception as error:  # noqa: BLE001 - provider boundary must preserve a usable fallback
            fallback = self._deterministic_parse(natural_language)
            fallback.reasoning_summary = (
                f"Deterministic fallback after LLM failure: {type(error).__name__}: {error}"
            )
            fallback.confidence = min(fallback.confidence, 0.55)
            return fallback

    def _llm_parse(self, natural_language: str) -> ParsedIntent:
        """Use the configured LLM as the semantic intent authority."""
        decision = StrategyLLMProvider(
            self.provider,
            system_prompt=(
                "You are the semantic intent engine for an engineering environment installer. "
                "Understand English and Persian. Extract what the user explicitly wants installed "
                "and what the user explicitly says must NOT be installed. "
                "Negative instructions override positive mentions. Return ONLY valid JSON."
            ),
        ).decide(self._build_prompt(natural_language), [])
        parsed = json.loads(decision.reasoning_summary.strip())
        if not isinstance(parsed, dict):
            raise TypeError("LLM intent response must be an object.")

        excluded_tools, excluded_packages = self._deterministic_exclusions(
            natural_language
        )
        lexical_tools = self._deterministic_tool_mentions(
            natural_language, excluded_tools
        )
        required_tools = self._normalise_strings(
            parsed.get("required_tools", []), self._known_tools
        )
        optional_tools = self._normalise_strings(
            parsed.get("optional_tools", []), self._known_tools
        )
        excluded_tools = self._merge_unique(
            excluded_tools,
            self._normalise_strings(parsed.get("excluded_tools", []), self._known_tools),
        )
        required_tools = [
            tool
            for tool in self._merge_unique(required_tools, lexical_tools)
            if tool.lower() not in {item.lower() for item in excluded_tools}
        ]
        optional_tools = [
            tool
            for tool in self._merge_unique(optional_tools, [])
            if tool.lower() not in {item.lower() for item in excluded_tools}
            and tool not in required_tools
        ]

        project_dependencies = self._normalise_packages(
            parsed.get("project_dependencies", [])
        )
        excluded_packages = self._merge_unique(
            excluded_packages,
            self._normalise_strings(parsed.get("excluded_packages", [])),
        )
        excluded_package_set = {item.lower() for item in excluded_packages}
        project_dependencies = [
            package
            for package in project_dependencies
            if package.lower() not in excluded_package_set
        ]

        return ParsedIntent(
            natural_language_goal=parsed.get("natural_language_goal", natural_language),
            required_tools=required_tools,
            optional_tools=optional_tools,
            excluded_tools=excluded_tools,
            languages=self._normalise_strings(parsed.get("languages", [])),
            frameworks=self._normalise_strings(parsed.get("frameworks", [])),
            project_dependencies=project_dependencies,
            excluded_packages=excluded_packages,
            constraints=self._normalise_strings(parsed.get("constraints", [])),
            platform_preferences=self._normalise_strings(
                parsed.get("platform_preferences", [])
            ),
            confidence=decision.confidence,
            reasoning_summary="LLM-parsed semantic intent",
        )

    def _deterministic_parse(self, natural_language: str) -> ParsedIntent:
        """High-recall deterministic fallback for common English/Persian requests."""
        excluded_tools, excluded_packages = self._deterministic_exclusions(natural_language)
        required_tools = self._deterministic_tool_mentions(
            natural_language, excluded_tools
        )
        optional_tools: list[str] = []
        text_lower = natural_language.lower()
        languages: list[str] = []
        frameworks = [
            framework for framework in self._known_frameworks if framework in text_lower
        ]
        dependencies = self._extract_install_packages(
            natural_language, required_tools
        )
        dependencies = [
            package
            for package in dependencies
            if package.lower() not in {item.lower() for item in excluded_packages}
        ]
        constraints: list[str] = []

        if "python" in text_lower or "پایتون" in text_lower:
            languages.append("python")
        if "javascript" in text_lower or " js " in f" {text_lower} ":
            languages.append("javascript")
        if "typescript" in text_lower or " ts " in f" {text_lower} ":
            languages.append("typescript")
        if (
            "no sudo" in text_lower
            or "without root" in text_lower
            or "بدون روت" in text_lower
        ):
            constraints.append("no_root_required")
        if "virtualenv" in text_lower or "venv" in text_lower:
            constraints.append("use_virtualenv")
        if "isolated" in text_lower or "ایزوله" in text_lower:
            constraints.append("isolated_environment")
        if any(
            value in text_lower
            for value in (
                "ai",
                "ml",
                "machine learning",
                "هوش مصنوعی",
                "یادگیری ماشین",
            )
        ):
            if "python" not in required_tools:
                required_tools.append("python")
            if "pytorch" not in frameworks and "tensorflow" not in frameworks:
                frameworks.append("pytorch")
            if "transformers" not in frameworks:
                frameworks.append("transformers")
        if "fastapi" in text_lower:
            if "python" not in required_tools:
                required_tools.append("python")
            if "uvicorn" not in [item.lower() for item in dependencies]:
                dependencies.append("uvicorn")
            if "pytest" in self._known_tools and "pytest" not in required_tools:
                required_tools.append("pytest")

        return ParsedIntent(
            natural_language_goal=natural_language,
            required_tools=required_tools,
            optional_tools=optional_tools,
            excluded_tools=excluded_tools,
            languages=languages,
            frameworks=frameworks,
            project_dependencies=dependencies,
            excluded_packages=excluded_packages,
            constraints=constraints,
            confidence=0.7,
            reasoning_summary="Deterministic high-recall fallback parsing",
        )

    def _build_prompt(self, natural_language: str) -> str:
        """Build the semantic JSON contract used for intent extraction."""
        return f"""You are the semantic intent engine for an engineering environment installer.
Understand both English and Persian user requests.

Catalog of valid tool IDs:
{sorted(self._known_tools)}

Return ONLY this JSON object:
{{
  "natural_language_goal": "...",
  "required_tools": ["tool1", "tool2"],
  "optional_tools": ["tool3"],
  "excluded_tools": ["tool4"],
  "languages": ["python"],
  "frameworks": ["fastapi"],
  "project_dependencies": ["package1"],
  "excluded_packages": ["package2"],
  "constraints": ["no_root_required"],
  "platform_preferences": ["linux"]
}}

Rules:
1. Capture EVERY explicitly requested install target; do not stop after one or two.
2. Negative instructions such as "don't install colorama", "do not install pytest", "کالرآما را نصب نکن" or "پی‌تست نصب نشود" go to excluded_tools or excluded_packages and override any positive mention.
3. Never invent a tool ID. Unknown package names may go to project_dependencies.
4. Preserve explicit version constraints when present.
5. Do not infer an installation merely because a framework or language was mentioned.
6. The result is used to build an execution plan, so omission of a requested item is a semantic error.

User goal:
{natural_language}
/no_think"""

    def _deterministic_tool_mentions(
        self, text: str, excluded_tools: list[str]
    ) -> list[str]:
        lowered = text.lower()
        excluded = {item.lower() for item in excluded_tools}
        found: list[str] = []
        for tool_id in self._known_tools:
            aliases = _TOOL_ALIASES.get(tool_id, {tool_id})
            for alias in aliases:
                for match in re.finditer(re.escape(alias.lower()), lowered):
                    context = lowered[max(0, match.start() - 90) : match.start()]
                    if _NEGATION.search(context):
                        continue
                    found.append(tool_id)
                    break
                if tool_id in found:
                    break
        return [
            tool
            for tool in self._merge_unique(found, [])
            if tool.lower() not in excluded
        ]

    def _deterministic_exclusions(self, text: str) -> tuple[list[str], list[str]]:
        lowered = text.lower()
        excluded_tools: list[str] = []
        for tool_id in self._known_tools:
            aliases = _TOOL_ALIASES.get(tool_id, {tool_id})
            for alias in aliases:
                for match in re.finditer(re.escape(alias.lower()), lowered):
                    context = lowered[max(0, match.start() - 100) : match.start()]
                    if _NEGATION.search(context):
                        excluded_tools.append(tool_id)
                        break
                if tool_id in excluded_tools:
                    break

        excluded_packages = self._extract_negative_packages(text)
        return self._merge_unique(excluded_tools, []), self._merge_unique(
            excluded_packages, []
        )

    @staticmethod
    def _extract_negative_packages(text: str) -> list[str]:
        result: list[str] = []
        clauses = re.split(
            r"[\n.;،]+|\bbut\b|\bاما\b|\bولی\b", text, flags=re.IGNORECASE
        )
        for clause in clauses:
            if not _NEGATION.search(clause) or not _POSITIVE_VERBS.search(clause):
                continue
            match = re.search(
                r"(?:don't|do not|dont|never|avoid)\s+(?:install|reinstall|setup|set up|add)\s+(.+)$",
                clause,
                flags=re.IGNORECASE,
            )
            payload = match.group(1) if match else clause
            payload = re.sub(
                r".*?\b(?:نصب\s+نکن(?:ید|م)?|نصب\s+نشود)\b\s*",
                "",
                payload,
                flags=re.IGNORECASE,
            )
            for token in re.split(
                r"\s*(?:,|&|\band\b|\band/or\b|\bو\b|\+)\s*",
                payload,
                flags=re.IGNORECASE,
            ):
                candidate = token.strip(" .;:()[]،")
                candidate = re.sub(
                    r"(?:را|رو)\s*$", "", candidate, flags=re.IGNORECASE
                ).strip()
                if candidate and _TOKEN.fullmatch(candidate):
                    result.append(candidate)
        return list(dict.fromkeys(result))

    @staticmethod
    def _extract_install_packages(text: str, required_tools: list[str]) -> list[str]:
        required = {tool.lower() for tool in required_tools}
        result: list[str] = []
        positive_clauses = [
            match.group(1)
            for match in re.finditer(
                r"\b(?:install|reinstall|setup|set up|add)\s+(.+?)(?=\s+(?:on|onto|into|for|using)\s+|$)",
                text,
                flags=re.IGNORECASE,
            )
        ]
        for clause in positive_clauses:
            for token in re.split(
                r"\s*(?:,|&|\band\b|\+)\s*", clause, flags=re.IGNORECASE
            ):
                candidate = token.strip(" .;:()[]،")
                if (
                    candidate
                    and candidate.lower() not in required
                    and _TOKEN.fullmatch(candidate)
                ):
                    result.append(candidate)
        return list(dict.fromkeys(result))

    @staticmethod
    def _normalise_strings(value: object, allowed: set[str] | None = None) -> list[str]:
        if not isinstance(value, list):
            return []
        values = [str(item).strip() for item in value if str(item).strip()]
        if allowed is not None:
            allowed_lower = {item.lower(): item for item in allowed}
            values = [
                allowed_lower[item.lower()]
                for item in values
                if item.lower() in allowed_lower
            ]
        return list(dict.fromkeys(values))

    @staticmethod
    def _normalise_packages(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                name = item.strip()
            elif isinstance(item, dict):
                name = str(item.get("name", "")).strip()
            else:
                continue
            if name:
                result.append(name)
        return list(dict.fromkeys(result))

    @staticmethod
    def _merge_unique(left: list[str], right: list[str]) -> list[str]:
        return list(dict.fromkeys([*left, *right]))


__all__ = ["IntentParser", "ParsedIntent"]

"""LLM-powered semantic intent parsing for environment installation requests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ai_engineering_bootstrap.agent.provider import LLMProvider
from ai_engineering_bootstrap.agent.strategy_llm_bridge import StrategyLLMProvider
from ai_engineering_bootstrap.environment.models import (
    EnvironmentRequest,
    PythonPackageRequirement,
)
from ai_engineering_bootstrap.environment.tool_catalog import ToolCatalog

_TOOL_ALIASES = {
    "cursor": {"cursor"},
    "git": {"git", "گیت"},
    "docker": {"docker", "داکر"},
    "ruff": {"ruff", "روف", "رووف", "راف"},
    "pytest": {"pytest", "py test", "پایتست", "پای تست", "پای‌تست", "پی‌تست"},
    "black": {"black", "بلک"},
    "github-cli": {"github-cli", "gh", "گیت هاب کلای"},
    "nodejs": {"node", "nodejs", "نود"},
    "npm": {"npm", "ان پی ام"},
    "uv": {"uv"},
    "poetry": {"poetry", "پواتری"},
    "python": {"python", "python3", "پایتون"},
}

_INSTALL_SIGNAL_TOKENS = (
    "install",
    "reinstall",
    "setup",
    "set up",
    "add",
    "نصب",
    "راه اندازی",
    "راه‌اندازی",
    "اضافه",
)
_NEGATION = re.compile(
    r"(?:\bdon['’]?t\b|\bdo\s+not\b|\bdont\b|\bnever\b|\bavoid\b|"
    r"نصب\s+نکن(?:ید|م)?|نصب\s+نشود|نمی[‌ ]?(?:خوام|خواهم)|نیازی\s+به\s+نصب)",
    re.IGNORECASE,
)
_TOKEN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.+\-]*(?:\s*(?:===|==|!=|~=|>=|<=|>|<)\s*[A-Za-z0-9][A-Za-z0-9+_.!\-]*)?$"
)
_ENVIRONMENT_CONTEXT = re.compile(
    r"(?:environment|project|development|need|prepare|set\s+up|setup|"
    r"محیط|پروژه|توسعه|نیاز|آماده|راه[ -]?اندازی|برای)",
    re.IGNORECASE,
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
        """Convert the parsed intent into the canonical request model."""
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
            project_dependencies=[
                PythonPackageRequirement(name=name)
                for name in self.project_dependencies
            ],
            excluded_packages=self.excluded_packages,
            configurations={},
            constraints={constraint: True for constraint in self.constraints},
            platform_preferences={"preferences": self.platform_preferences}
            if self.platform_preferences
            else {},
            user_preferences={},
        )


class IntentParser:
    """Parse natural-language installation intent with LLM-first semantics."""

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
        """Return whether semantic LLM parsing is configured."""
        return self.provider is not None

    def metadata(self) -> dict[str, object]:
        """Return safe provider metadata for observability."""
        if self.provider is None:
            return {"provider": "deterministic"}
        return StrategyLLMProvider(self.provider).metadata()

    def parse(self, natural_language: str) -> ParsedIntent:
        """Parse intent; deterministic parsing is fallback-only."""
        if not natural_language.strip():
            return ParsedIntent(reasoning_summary="Empty intent")
        if self.provider is None:
            return self._deterministic_parse(natural_language)
        try:
            return self._llm_parse(natural_language)
        except Exception as error:  # noqa: BLE001 - semantic provider fallback boundary
            fallback = self._deterministic_parse(natural_language)
            fallback.reasoning_summary = (
                f"Deterministic fallback after LLM failure: {type(error).__name__}: {error}"
            )
            fallback.confidence = min(fallback.confidence, 0.55)
            return fallback

    def _llm_parse(self, natural_language: str) -> ParsedIntent:
        """Delegate semantic extraction to the configured provider."""
        decision = StrategyLLMProvider(
            self.provider,
            system_prompt=(
                "You are the semantic intent engine for an engineering environment installer. "
                "Understand English and Persian. Return ONLY valid JSON. Capture every explicit "
                "installation request and every explicit exclusion. Never infer an installation "
                "from a mere mention of a language, framework, or tool. Negative instructions "
                "override positive mentions."
            ),
        ).decide(self._build_prompt(natural_language), [])
        parsed = json.loads(decision.reasoning_summary.strip())
        if not isinstance(parsed, dict):
            raise TypeError("LLM intent response must be an object.")

        deterministic_excluded_tools, deterministic_excluded_packages = (
            self._deterministic_exclusions(natural_language)
        )
        lexical_tools = self._deterministic_explicit_tool_mentions(
            natural_language, deterministic_excluded_tools
        )

        excluded_tools = self._merge_unique(
            deterministic_excluded_tools,
            self._normalise_strings(
                parsed.get("excluded_tools", []), self._known_tools
            ),
        )
        excluded_packages = self._merge_unique(
            deterministic_excluded_packages,
            self._normalise_packages(parsed.get("excluded_packages", [])),
        )
        excluded_tool_set = {tool.lower() for tool in excluded_tools}
        excluded_package_set = {package.lower() for package in excluded_packages}

        required_tools = self._merge_unique(
            self._normalise_strings(
                parsed.get("required_tools", []), self._known_tools
            ),
            lexical_tools,
        )
        required_tools = [
            tool for tool in required_tools if tool.lower() not in excluded_tool_set
        ]
        optional_tools = [
            tool
            for tool in self._normalise_strings(
                parsed.get("optional_tools", []), self._known_tools
            )
            if tool.lower() not in excluded_tool_set and tool not in required_tools
        ]

        project_dependencies = [
            package
            for package in self._normalise_packages(
                parsed.get("project_dependencies", [])
            )
            if package.lower() not in excluded_package_set
        ]

        return ParsedIntent(
            natural_language_goal=str(
                parsed.get("natural_language_goal", natural_language)
            ),
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
        """Fallback parser for explicit installation/environment requests."""
        excluded_tools, excluded_packages = self._deterministic_exclusions(
            natural_language
        )
        required_tools = self._merge_unique(
            self._deterministic_explicit_tool_mentions(
                natural_language, excluded_tools
            ),
            self._deterministic_environment_tool_mentions(
                natural_language, excluded_tools
            ),
        )
        packages = self._extract_install_packages(natural_language, required_tools)
        excluded_package_set = {package.lower() for package in excluded_packages}
        packages = [
            package
            for package in packages
            if package.lower() not in excluded_package_set
        ]

        text_lower = natural_language.lower()
        languages = []
        if "python" in text_lower or "پایتون" in text_lower:
            languages.append("python")
        if "javascript" in text_lower or re.search(r"\bjs\b", text_lower):
            languages.append("javascript")
        if "typescript" in text_lower or re.search(r"\bts\b", text_lower):
            languages.append("typescript")

        frameworks = [
            framework for framework in self._known_frameworks if framework in text_lower
        ]
        constraints = []
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

        return ParsedIntent(
            natural_language_goal=natural_language,
            required_tools=list(dict.fromkeys(required_tools)),
            optional_tools=[],
            excluded_tools=excluded_tools,
            languages=languages,
            frameworks=frameworks,
            project_dependencies=packages,
            excluded_packages=excluded_packages,
            constraints=constraints,
            confidence=0.7,
            reasoning_summary="Deterministic explicit-intent fallback",
        )

    def _build_prompt(self, natural_language: str) -> str:
        """Build a strict semantic contract for the LLM."""
        return f"""You are the semantic intent engine for an engineering environment installer.
Understand both English and Persian.

Valid tool IDs:
{sorted(self._known_tools)}

Return ONLY one JSON object with exactly these fields:
{{
  "natural_language_goal": "...",
  "required_tools": ["tool1", "tool2"],
  "optional_tools": ["tool3"],
  "excluded_tools": ["tool4"],
  "languages": ["python"],
  "frameworks": ["fastapi"],
  "project_dependencies": ["colorama"],
  "excluded_packages": ["colorama"],
  "constraints": ["no_root_required"],
  "platform_preferences": ["linux"]
}}

Hard rules:
1. Capture EVERY explicit installation target, not only the first one or two.
2. "don't install X", "do not install X", "avoid X", "X را نصب نکن", and "X نصب نشود" are exclusions.
3. Exclusions override positive mentions.
4. Unknown names that look like Python packages belong in project_dependencies/excluded_packages.
5. Do not infer installation because a framework, language, or tool was merely mentioned.
6. Preserve version constraints if the user supplied them.
7. Do not omit an explicit requested item.
8. Persian and English may be mixed in one sentence.

User goal:
{natural_language}
/no_think"""

    def _deterministic_environment_tool_mentions(
        self, text: str, excluded_tools: list[str]
    ) -> list[str]:
        """Recognize tools named as part of an environment request."""
        if not _ENVIRONMENT_CONTEXT.search(text):
            return []
        lowered = text.lower()
        excluded = {tool.lower() for tool in excluded_tools}
        result: list[str] = []
        for tool_id in self._known_tools:
            if tool_id.lower() in excluded:
                continue
            aliases = _TOOL_ALIASES.get(tool_id, {tool_id})
            if any(re.search(re.escape(alias.lower()), lowered) for alias in aliases):
                result.append(tool_id)
        return result

    def _deterministic_explicit_tool_mentions(
        self, text: str, excluded_tools: list[str]
    ) -> list[str]:
        """Recognize named tools when the request contains an installation signal."""
        lowered = text.lower().replace("\u200c", " ")
        if not any(token in lowered for token in _INSTALL_SIGNAL_TOKENS):
            return []
        excluded = {tool.lower() for tool in excluded_tools}
        result: list[str] = []
        for tool_id in self._known_tools:
            if tool_id.lower() in excluded:
                continue
            aliases = _TOOL_ALIASES.get(tool_id, {tool_id})
            if any(
                re.search(re.escape(alias.lower().replace("\u200c", " ")), lowered)
                for alias in aliases
            ):
                result.append(tool_id)
        return self._merge_unique(result, [])

    def _deterministic_exclusions(self, text: str) -> tuple[list[str], list[str]]:
        lowered = text.lower().replace("\u200c", " ")
        excluded_tools: list[str] = []
        clauses = re.split(
            r"[\n.;،]|\bbut\b|\bاما\b|\bولی\b", lowered, flags=re.IGNORECASE
        )
        for clause in clauses:
            if not _NEGATION.search(clause):
                continue
            for tool_id in self._known_tools:
                aliases = _TOOL_ALIASES.get(tool_id, {tool_id})
                if any(
                    re.search(
                        re.escape(alias.lower().replace("\u200c", " ")), clause
                    )
                    for alias in aliases
                ):
                    excluded_tools.append(tool_id)
        return self._merge_unique(excluded_tools, []), self._extract_negative_packages(
            text
        )

    @staticmethod
    def _extract_negative_packages(text: str) -> list[str]:
        result: list[str] = []
        clauses = re.split(
            r"[\n.;،]|\bbut\b|\bاما\b|\bولی\b",
            text.replace("\u200c", " "),
            flags=re.IGNORECASE,
        )
        for clause in clauses:
            if not _NEGATION.search(clause):
                continue
            match = re.search(
                r"(?:don't|do\s+not|dont|never|avoid)\s+(?:install\s+)?(.+)$",
                clause,
                flags=re.IGNORECASE,
            )
            payload = match.group(1) if match else clause
            payload = re.sub(
                r".*?(?:نصب\s+نکن(?:ید|م)?|نصب\s+نشود)\s*",
                "",
                payload,
                flags=re.IGNORECASE,
            )
            for token in re.split(
                r"\s*(?:,|&|\band\b|\bو\b|\+)\s*",
                payload,
                flags=re.IGNORECASE,
            ):
                candidate = re.sub(
                    r"(?:را|رو)\s*$",
                    "",
                    token.strip(" .;:()[]،"),
                    flags=re.IGNORECASE,
                ).strip()
                if candidate and _TOKEN.fullmatch(candidate):
                    result.append(candidate)
        return list(dict.fromkeys(result))

    @staticmethod
    def _extract_install_packages(text: str, required_tools: list[str]) -> list[str]:
        required = {tool.lower() for tool in required_tools}
        result: list[str] = []
        signal_pattern = "|".join(
            re.escape(token) for token in _INSTALL_SIGNAL_TOKENS
        )
        pattern = rf"(?:{signal_pattern})\s+(.+?)(?=\s+(?:on|onto|into|for|using|در|روی|برای)\s+|$)"
        normalized = text.replace("\u200c", " ")
        for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
            clause = re.sub(
                r"\bpython\s+(?:package|packages)\b",
                "",
                match.group(1),
                flags=re.IGNORECASE,
            )
            if _NEGATION.search(match.group(0)):
                continue
            for token in re.split(
                r"\s*(?:,|&|\band\b|\bو\b|\+)\s*",
                clause,
                flags=re.IGNORECASE,
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
    def _normalise_strings(
        value: object, allowed: set[str] | None = None
    ) -> list[str]:
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

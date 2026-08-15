"""High-recall safety normalization for natural-language installation intent."""

from __future__ import annotations

import re

from ai_engineering_bootstrap.agent.intent_parser import ParsedIntent
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

_POSITIVE_CLAUSE = re.compile(
    r"(?:install|reinstall|setup|set up|add|نصب(?:\s+کن(?:ید|م)?)?|راه[ -]?اندازی)\s+(.+)$",
    re.IGNORECASE,
)
_NEGATIVE_EN = re.compile(
    r"(?:don['’]?t|do not|dont|never|avoid)\s+(?:install|reinstall|setup|set up|add)\s+(.+)$",
    re.IGNORECASE,
)
_NEGATIVE_FA = re.compile(
    r"(.+?)\s*(?:را|رو)?\s*نصب\s*(?:نکن(?:ید|م)?|نشود)$",
    re.IGNORECASE,
)
_TOKEN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.+-]*(?:\s*(?:===|==|!=|~=|>=|<=|>|<)\s*[A-Za-z0-9][A-Za-z0-9+_.!-]*)?$"
)


class IntentNormalizer:
    """Guarantee high recall and explicit negative/positive separation."""

    def __init__(self, tool_catalog: ToolCatalog | None = None) -> None:
        self.tool_ids = (
            {item.tool_id for item in tool_catalog.list_tools()}
            if tool_catalog
            else set(_TOOL_ALIASES)
        )

    def normalize(self, goal: str, intent: ParsedIntent) -> ParsedIntent:
        """Merge clause-local lexical evidence without overriding LLM semantics blindly."""
        required = list(intent.required_tools)
        excluded_tools = list(intent.excluded_tools)
        dependencies = list(intent.project_dependencies)
        excluded_packages = list(intent.excluded_packages)

        excluded_tool_set = {item.lower() for item in excluded_tools}
        excluded_package_set = {item.lower() for item in excluded_packages}
        dependency_set = {item.lower() for item in dependencies}
        required_set = {item.lower() for item in required}

        clauses = re.split(
            r"\n|(?<!\d)[,؛;]|\bbut\b|\bاما\b|\bولی\b",
            goal,
            flags=re.IGNORECASE,
        )
        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            negative = self._negative_payload(clause)
            if negative is not None:
                for candidate in self._split_targets(negative):
                    tool_id = self._resolve_tool(candidate)
                    if tool_id:
                        excluded_tools.append(tool_id)
                        excluded_tool_set.add(tool_id.lower())
                    elif candidate and _TOKEN.fullmatch(candidate):
                        excluded_packages.append(candidate)
                        excluded_package_set.add(candidate.lower())
                continue

            positive = _POSITIVE_CLAUSE.search(clause)
            if not positive:
                continue
            for candidate in self._split_targets(positive.group(1)):
                tool_id = self._resolve_tool(candidate)
                if tool_id:
                    if (
                        tool_id.lower() not in excluded_tool_set
                        and tool_id not in required
                    ):
                        required.append(tool_id)
                        required_set.add(tool_id.lower())
                elif (
                    candidate
                    and _TOKEN.fullmatch(candidate)
                    and candidate.lower() not in excluded_package_set
                    and candidate.lower() not in required_set
                    and candidate.lower() not in dependency_set
                ):
                    dependencies.append(candidate)
                    dependency_set.add(candidate.lower())

        intent.required_tools = list(
            dict.fromkeys(
                item for item in required if item.lower() not in excluded_tool_set
            )
        )
        intent.excluded_tools = list(dict.fromkeys(excluded_tools))
        intent.project_dependencies = list(
            dict.fromkeys(
                item
                for item in dependencies
                if item.lower() not in excluded_package_set
            )
        )
        intent.excluded_packages = list(dict.fromkeys(excluded_packages))
        return intent

    def _resolve_tool(self, candidate: str) -> str | None:
        lowered = candidate.lower().strip(" .:()[]،")
        for tool_id in self.tool_ids:
            if lowered == tool_id.lower():
                return tool_id
        for tool_id, aliases in _TOOL_ALIASES.items():
            if tool_id in self.tool_ids and lowered in {
                alias.lower() for alias in aliases
            }:
                return tool_id
        return None

    @staticmethod
    def _negative_payload(clause: str) -> str | None:
        match = _NEGATIVE_EN.search(clause)
        if match:
            return match.group(1)
        match = _NEGATIVE_FA.search(clause)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _split_targets(payload: str) -> list[str]:
        payload = re.sub(
            r"\b(?:python\s+)?(?:package|packages)\b", "", payload, flags=re.IGNORECASE
        )
        parts = re.split(
            r"\s*(?:,|&|\band\b|\band/or\b|\bو\b|\+)\s*",
            payload.strip(" .:()[]،"),
            flags=re.IGNORECASE,
        )
        result: list[str] = []
        for part in parts:
            candidate = part.strip(" .:()[]،")
            candidate = re.sub(
                r"(?:را|رو)\s*$", "", candidate, flags=re.IGNORECASE
            ).strip()
            if candidate:
                result.append(candidate)
        return result


__all__ = ["IntentNormalizer"]

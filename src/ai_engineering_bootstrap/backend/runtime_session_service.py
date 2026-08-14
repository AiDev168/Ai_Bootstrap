"""Runtime session orchestration for GUI-driven environment bootstrap."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from threading import Lock, Thread

from ai_engineering_bootstrap.agent.intent_parser import IntentParser, ParsedIntent
from ai_engineering_bootstrap.backend.session_service import EnvironmentSessionService, SessionServiceResult
from ai_engineering_bootstrap.environment.models import EnvironmentRequest, PythonPackageRequirement
from ai_engineering_bootstrap.environment.session_models import AgentDecision, SessionStatus
from ai_engineering_bootstrap.executor.mode import ExecutionMode

logger = logging.getLogger(__name__)
_PACKAGE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*(?:\s*(?:===|==|!=|~=|>=|<=|>|<)\s*[A-Za-z0-9][A-Za-z0-9+_.!-]*)?$")
_INSTALL_CLAUSE = re.compile(r"\b(?:install|reinstall|setup|set up|add)\s+(.+?)(?=\s+(?:on|onto|into|for|using)\s+|$)", re.IGNORECASE)


class RuntimeSessionService(EnvironmentSessionService):
    """Add runtime LLM intent parsing and non-blocking GUI execution."""

    def __init__(self, intent_parser_factory: Callable[[], IntentParser] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._intent_parser_factory = intent_parser_factory
        self._running: set[str] = set()
        self._running_lock = Lock()

    def create(self, request: EnvironmentRequest) -> SessionServiceResult:
        """Resolve natural-language intent before deterministic reconciliation."""
        parsed = None
        if self._intent_parser_factory and request.natural_language_goal.strip():
            parsed = self._intent_parser_factory().parse(request.natural_language_goal)
            request = self._merge_request(request, parsed)

        result = super().create(request)
        if parsed is not None:
            session = self.get(result.data["session_id"])
            if parsed.reasoning_summary.startswith("LLM-parsed"):
                provider = "llm"
            elif parsed.reasoning_summary.startswith("Deterministic fallback after LLM"):
                provider = "llm_fallback"
            else:
                provider = "deterministic"
            session.add_agent_decision(
                AgentDecision(
                    session_id=session.session_id,
                    provider=provider,
                    decision_type="intent_parsing",
                    reasoning_summary=parsed.reasoning_summary,
                    confidence=parsed.confidence,
                    selected_strategy={
                        "required_tools": list(parsed.required_tools),
                        "optional_tools": list(parsed.optional_tools),
                        "languages": list(parsed.languages),
                        "frameworks": list(parsed.frameworks),
                        "project_dependencies": list(parsed.project_dependencies),
                        "constraints": list(parsed.constraints),
                    },
                )
            )
            session.add_event(
                "intent_parsed",
                "Natural-language environment intent resolved before reconciliation.",
                {
                    "provider": provider,
                    "confidence": parsed.confidence,
                    "required_tools": list(parsed.required_tools),
                    "project_dependencies": list(parsed.project_dependencies),
                },
            )
            self.repository.update(session)
        return result

    def start_async(self, session_id: str, mode: ExecutionMode) -> SessionServiceResult:
        """Start execution in a background worker so the GUI remains responsive."""
        with self._running_lock:
            if session_id in self._running:
                return SessionServiceResult({"session_id": session_id, "status": "executing", "accepted": False})
            session = self.get(session_id)
            if session.status in {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED}:
                raise ValueError(f"Session {session_id} is already terminal: {session.status.value}")
            self._running.add(session_id)

        thread = Thread(target=self._run_worker, args=(session_id, mode), daemon=True, name=f"bootstrap-{session_id[:8]}")
        thread.start()
        return SessionServiceResult({"session_id": session_id, "status": "executing", "accepted": True})

    def _run_worker(self, session_id: str, mode: ExecutionMode) -> None:
        try:
            self.start(session_id, mode)
        except ValueError as error:
            session = self.get(session_id)
            if "Approval required" in str(error):
                session.status = SessionStatus.AWAITING_APPROVAL
                session.add_event("approval_required", str(error))
            else:
                session.status = SessionStatus.FAILED
                session.add_event("session_failed", str(error), {"error_type": type(error).__name__})
            self.repository.update(session)
        except Exception as error:  # noqa: BLE001 - isolated worker boundary must persist failure state
            logger.exception("Unhandled bootstrap worker failure for session %s", session_id)
            session = self.get(session_id)
            session.status = SessionStatus.FAILED
            session.add_event("session_failed", str(error), {"error_type": type(error).__name__})
            self.repository.update(session)
        finally:
            with self._running_lock:
                self._running.discard(session_id)

    @staticmethod
    def _merge_request(request: EnvironmentRequest, parsed: ParsedIntent) -> EnvironmentRequest:
        required = list(dict.fromkeys([*request.required_tools, *parsed.required_tools]))
        optional = [tool for tool in dict.fromkeys([*request.optional_tools, *parsed.optional_tools]) if tool not in required]
        languages = list(dict.fromkeys([*request.languages, *parsed.languages]))
        frameworks = list(dict.fromkeys([*request.frameworks, *parsed.frameworks]))
        dependencies = list(request.project_dependencies)
        existing_dependencies = {item.name.lower() for item in dependencies}
        required_lower = {tool.lower() for tool in required}
        extracted = RuntimeSessionService._extract_install_packages(request.natural_language_goal, required)
        for name in [*parsed.project_dependencies, *extracted]:
            if name.lower() not in existing_dependencies and name.lower() not in required_lower:
                dependencies.append(PythonPackageRequirement(name=name))
                existing_dependencies.add(name.lower())
        constraints = dict(request.constraints)
        for constraint in parsed.constraints:
            constraints[constraint] = True
        platform_preferences = dict(request.platform_preferences)
        if parsed.platform_preferences:
            platform_preferences["preferences"] = list(parsed.platform_preferences)
        return EnvironmentRequest(
            request_id=request.request_id,
            project_id=request.project_id,
            project_path=request.project_path,
            natural_language_goal=request.natural_language_goal,
            required_tools=required,
            optional_tools=optional,
            languages=languages,
            frameworks=frameworks,
            project_dependencies=dependencies,
            configurations=dict(request.configurations),
            constraints=constraints,
            platform_preferences=platform_preferences,
            user_preferences=dict(request.user_preferences),
        )

    @staticmethod
    def _extract_install_packages(goal: str, required_tools: list[str]) -> list[str]:
        required = {tool.lower() for tool in required_tools}
        result: list[str] = []
        for match in _INSTALL_CLAUSE.finditer(goal):
            clause = re.sub(r"\bpython\s+(?:package|packages)\b", "", match.group(1), flags=re.IGNORECASE)
            for token in re.split(r"\s*(?:,|&|\band\b|\+)\s*", clause, flags=re.IGNORECASE):
                token = token.strip(" .;:()[]")
                if not token or token.lower() in required or not _PACKAGE_TOKEN.fullmatch(token):
                    continue
                if token.lower() not in {item.lower() for item in result}:
                    result.append(token)
        return result


__all__ = ["RuntimeSessionService"]

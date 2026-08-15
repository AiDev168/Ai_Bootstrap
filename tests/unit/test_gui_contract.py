"""GUI/backend contract checks for the professional dashboard foundation."""

import re
from pathlib import Path

HTML_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/ai_engineering_bootstrap/gui/static/index.html"
)
RUNTIME_PATH = HTML_PATH.with_name("app-runtime.js")


def test_dashboard_uses_active_backend_routes() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    for route in ("/health", "/audit", "/engineering", "/sessions"):
        assert route in html
    for route in (
        r"/sessions/\$\{[^}]+\}",
        r"/sessions/\$\{[^}]+\}/state",
        r"/sessions/\$\{[^}]+\}/plan",
        r"/sessions/\$\{[^}]+\}/events",
        r"/sessions/\$\{[^}]+\}/agent-decisions",
    ):
        assert re.search(route, html), f"Missing GUI route pattern: {route}"


def test_dashboard_has_professional_console_i18n_and_timeline_controls() -> None:
    source = f"{HTML_PATH.read_text(encoding='utf-8')}\n{RUNTIME_PATH.read_text(encoding='utf-8')}"
    required = (
        "Request Console",
        "window.logRequest",
        "request-filter",
        "requestFilter",
        "Pause Latest",
        "Resume Latest",
        "selectedRequestIndex",
        "maxRequests = 100",
        "language-switch",
        "gui-language",
        "stage-intent",
        "stage-plan",
        "stage-approval",
        "stage-execution",
        "stage-verification",
        "stage-recovery",
        "stage-error",
        'data-start="safe"',
        "/llm/settings",
        "/llm/test",
        "/llm/models",
        "local_server",
        "remote_api",
        "mock",
        "in_process",
    )
    for text in required:
        assert text in source, f"Missing GUI contract token: {text}"

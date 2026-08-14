"""GUI/backend contract checks for the professional dashboard foundation."""

import re
from pathlib import Path

HTML_PATH = Path(__file__).resolve().parents[2] / "src/ai_engineering_bootstrap/gui/static/index.html"


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


def test_dashboard_has_request_console_live_refresh_and_llm_settings() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    for text in (
        "Request Console",
        "logRequest",
        "startPolling",
        "Approve",
        "Start Real",
        "LLM Connection",
        "/llm/settings",
        "/llm/test",
        "local_server",
        "remote_api",
        "mock",
        "in_process",
        "function viewSession",
        "Promise.allSettled",
        "loadSessionPart",
    ):
        assert text in html

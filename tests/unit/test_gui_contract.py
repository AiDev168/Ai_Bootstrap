"""GUI/backend contract checks for the professional dashboard foundation."""

import re
from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[2] / "src/ai_engineering_bootstrap/gui/static/index.html"


def test_dashboard_uses_active_backend_routes() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    static_routes = ("/health", "/audit", "/engineering", "/sessions")
    for route in static_routes:
        assert route in html

    session_routes = (
        r"/sessions/\$\{[^}]+\}",
        r"/sessions/\$\{[^}]+\}/state",
        r"/sessions/\$\{[^}]+\}/plan",
        r"/sessions/\$\{[^}]+\}/events",
        r"/sessions/\$\{[^}]+\}/agent-decisions",
    )
    for route in session_routes:
        assert re.search(route, html), f"Missing GUI route pattern: {route}"


def test_dashboard_has_request_console_and_live_session_refresh() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "Request Console" in html
    assert "startPolling" in html
    assert "logRequest" in html
    assert "Approve" in html
    assert "Start Real" in html

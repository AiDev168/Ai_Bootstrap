"""GUI/backend contract checks for the professional dashboard foundation."""

from pathlib import Path


HTML_PATH = Path(__file__).resolve().parents[2] / "src/ai_engineering_bootstrap/gui/static/index.html"


def test_dashboard_uses_active_backend_routes() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    expected_routes = (
        "'/health'",
        "'/audit'",
        "'/engineering'",
        "'/sessions'",
        "`/sessions/${sessionId}`",
        "`/sessions/${sessionId}/state`",
        "`/sessions/${sessionId}/plan`",
        "`/sessions/${sessionId}/events`",
        "`/sessions/${sessionId}/agent-decisions`",
    )
    for route in expected_routes:
        assert route in html


def test_dashboard_has_request_console_and_live_session_refresh() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "Request Console" in html
    assert "startPolling" in html
    assert "logRequest" in html
    assert "Approve" in html
    assert "Start Real" in html

"""GUI/backend contract checks for the professional dashboard foundation."""

from ai_engineering_bootstrap.gui import static


def _html() -> str:
    return (static.__path__[0] if hasattr(static, "__path__") else "")


def test_dashboard_uses_active_backend_routes() -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "src/ai_engineering_bootstrap/gui/static/index.html"
    html = path.read_text(encoding="utf-8")

    expected_routes = (
        "'/health'",
        "'/audit'",
        "'/engineering'",
        "'/sessions'",
        "'/sessions/${sessionId}'",
        "'/sessions/${sessionId}/state'",
        "'/sessions/${sessionId}/plan'",
        "'/sessions/${sessionId}/events'",
        "'/sessions/${sessionId}/agent-decisions'",
    )
    for route in expected_routes:
        assert route in html


def test_dashboard_has_request_console_and_live_session_refresh() -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "src/ai_engineering_bootstrap/gui/static/index.html"
    html = path.read_text(encoding="utf-8")

    assert "Request Console" in html
    assert "startPolling" in html
    assert "logRequest" in html
    assert "Approve" in html
    assert "Start Real" in html

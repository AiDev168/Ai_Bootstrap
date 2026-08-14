"""Dependency-free HTTP server for the stable backend and GUI."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ai_engineering_bootstrap.backend import ApplicationBackend
from ai_engineering_bootstrap.environment.models import EnvironmentRequest
from ai_engineering_bootstrap.executor.mode import ExecutionMode


class BackendRequestHandler(BaseHTTPRequestHandler):
    """Serve versioned backend and GUI endpoints."""

    backend = ApplicationBackend()
    gui_root = Path(__file__).resolve().parents[1] / "gui" / "static"

    def _write_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _write_error(self, status: int, message: str) -> None:
        self._write_json({"error": message}, status)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("JSON request body must be an object")
        return payload

    @staticmethod
    def _result(result) -> dict:
        return result.data

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/v1/health":
                self._write_json(self._result(self.backend.health()))
                return
            if path == "/api/v1/llm/settings":
                self._write_json(self._result(self.backend.get_llm_settings()))
                return
            if path == "/api/v1/llm/test":
                self._write_json(self._result(self.backend.test_llm_connection()))
                return
            if path == "/api/v1/llm/models":
                self._write_json(self._result(self.backend.list_llm_models()))
                return
            if path == "/api/v1/audit":
                self._write_json(self._result(self.backend.audit()))
                return
            if path == "/api/v1/plan":
                self._write_json(self._result(self.backend.plan()))
                return
            if path == "/api/v1/engineering":
                self._write_json(self._result(self.backend.engineering()))
                return
            if path == "/api/v1/sessions":
                self._write_json(self._result(self.backend.list_sessions()))
                return
            session_match = self._session_route(path)
            if session_match:
                session_id, suffix = session_match
                if suffix == "":
                    self._write_json(self._result(self.backend.get_session(session_id)))
                    return
                if suffix == "/state":
                    self._write_json(self._result(self.backend.get_session_state(session_id)))
                    return
                if suffix == "/plan":
                    self._write_json(self._result(self.backend.get_session_plan(session_id)))
                    return
                if suffix == "/events":
                    self._write_json(self._result(self.backend.get_session_events(session_id)))
                    return
                if suffix == "/agent-decisions":
                    self._write_json(self._result(self.backend.get_agent_decisions(session_id)))
                    return

            if path in {"/", "/index.html"}:
                self._serve_index()
                return
            self._write_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
        except ValueError as exc:
            self._write_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # noqa: BLE001 - HTTP boundary
            self._write_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/v1/llm/settings":
                self._write_json(self._result(self.backend.update_llm_settings(self._read_json())))
                return
            if path == "/api/v1/run-safe":
                self._write_json(self._result(self.backend.run_safe()))
                return
            if path == "/api/v1/bootstrap-safe":
                self._write_json(self._result(self.backend.bootstrap_safe()))
                return
            if path == "/api/v1/run-real":
                self._write_json(self._result(self.backend.run_real_requires_cli()))
                return
            if path == "/api/v1/sessions":
                payload = self._read_json()
                request = EnvironmentRequest(
                    project_path=payload.get("project_path"),
                    natural_language_goal=payload.get("natural_language_goal", ""),
                    required_tools=list(payload.get("required_tools", [])),
                    optional_tools=list(payload.get("optional_tools", [])),
                    project_dependencies=list(payload.get("project_dependencies", [])),
                    constraints=dict(payload.get("constraints", {})),
                )
                self._write_json(self._result(self.backend.create_session(request)))
                return

            session_match = self._session_route(path)
            if session_match:
                session_id, suffix = session_match
                if suffix == "/start":
                    mode = ExecutionMode(query.get("mode", ["safe"])[0].lower())
                    self._write_json(self._result(self.backend.start_session(session_id, mode)))
                    return
                if suffix == "/cancel":
                    self._write_json(self._result(self.backend.cancel_session(session_id)))
                    return
                action_match = self._action_route(suffix)
                if action_match:
                    action_id, action = action_match
                    if action == "approve":
                        self._write_json(self._result(self.backend.approve_action(session_id, action_id)))
                        return
                    if action == "reject":
                        self._write_json(self._result(self.backend.reject_action(session_id, action_id)))
                        return
                    if action == "skip":
                        self._write_json(self._result(self.backend.skip_action(session_id, action_id)))
                        return

            self._write_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
        except ValueError as exc:
            self._write_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # noqa: BLE001 - HTTP boundary
            self._write_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def _serve_index(self) -> None:
        index = self.gui_root / "index.html"
        body = index.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _session_route(path: str) -> tuple[str, str] | None:
        prefix = "/api/v1/sessions/"
        if not path.startswith(prefix):
            return None
        tail = path[len(prefix):]
        parts = tail.split("/", 1)
        session_id = parts[0]
        suffix = "" if len(parts) == 1 else f"/{parts[1]}"
        if not session_id:
            return None
        return session_id, suffix

    @staticmethod
    def _action_route(suffix: str) -> tuple[str, str] | None:
        parts = suffix.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "actions":
            return None
        return parts[1], parts[2]

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    """Run the backend and GUI HTTP server."""
    server = ThreadingHTTPServer((host, port), BackendRequestHandler)
    print(f"AI Engineering Bootstrap GUI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = ["BackendRequestHandler", "serve"]

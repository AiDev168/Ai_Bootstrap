"""Dependency-free HTTP server for the stable backend and GUI."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ai_engineering_bootstrap.backend import ApplicationBackend


class BackendRequestHandler(BaseHTTPRequestHandler):
    """Serve versioned read/safe-run API endpoints and the GUI."""

    backend = ApplicationBackend()
    gui_root = Path(__file__).resolve().parents[1] / "gui" / "static"

    def _write_json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _write_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        routes = {
            "/api/v1/health": lambda: {"status": "ok", "version": ApplicationBackend.VERSION},
            "/api/v1/audit": lambda: self.backend.audit().data,
            "/api/v1/plan": lambda: self.backend.plan().data,
            "/api/v1/engineering": lambda: self.backend.engineering().data,
        }
        if path in routes:
            try:
                self._write_json(routes[path]())
            except Exception as exc:  # noqa: BLE001
                self._write_error(500, str(exc))
            return

        if path == "/" or path == "/index.html":
            index = self.gui_root / "index.html"
            body = index.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self._write_error(404, "Endpoint not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/v1/run-safe":
                self._write_json(self.backend.run_safe().data)
                return
            if path == "/api/v1/bootstrap-safe":
                self._write_json(self.backend.bootstrap_safe().data)
                return
            if path == "/api/v1/run-real":
                self._write_json(self.backend.run_real_requires_cli().data)
                return
        except Exception as exc:  # noqa: BLE001
            self._write_error(500, str(exc))
            return
        self._write_error(404, "Endpoint not found")

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

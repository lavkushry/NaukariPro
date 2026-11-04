"""
Localhost WebSocket + HTTP bridge (autoapplycv pattern) on 127.0.0.1:7433.

CI uses MockDriver — never requires a live Chrome session.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Protocol


class BrowserDriver(Protocol):
    def get_field_inventory(self) -> List[Dict[str, Any]]: ...

    def fill_field(self, field_id: str, value: str) -> Dict[str, Any]: ...

    def screenshot(self) -> str: ...


@dataclass
class MockDriver:
    fields: List[Dict[str, Any]] = field(default_factory=list)
    values: Dict[str, str] = field(default_factory=dict)
    shots: int = 0

    def get_field_inventory(self) -> List[Dict[str, Any]]:
        return list(self.fields)

    def fill_field(self, field_id: str, value: str) -> Dict[str, Any]:
        self.values[field_id] = value
        return {"ok": True, "field_id": field_id, "value": value, "trusted": True}

    def screenshot(self) -> str:
        self.shots += 1
        return f"mock-screenshot-{self.shots}"


class BrowserBridge:
    def __init__(self, driver: Optional[BrowserDriver] = None, *, host: str = "127.0.0.1", port: int = 7433) -> None:
        self.driver = driver or MockDriver(
            fields=[
                {"id": "email", "type": "email", "required": True},
                {"id": "phone", "type": "tel", "required": True},
            ]
        )
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def handle(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body = body or {}
        if path in ("/", "/health", "/ping"):
            return {"ok": True, "bridge": "naukari-pro-browser", "port": self.port}
        if path == "/get_field_inventory":
            return {"fields": self.driver.get_field_inventory()}
        if path == "/fill_field":
            return self.driver.fill_field(str(body.get("field_id") or ""), str(body.get("value") or ""))
        if path == "/screenshot":
            return {"screenshot": self.driver.screenshot()}
        return {"error": "not_found", "path": path}

    def serve_forever(self) -> None:
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
                return

            def _json(self, code: int, payload: Dict[str, Any]) -> None:
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802
                self._json(200, bridge.handle("GET", self.path.split("?", 1)[0]))

            def do_POST(self) -> None:  # noqa: N802
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    body = {}
                self._json(200, bridge.handle("POST", self.path.split("?", 1)[0], body if isinstance(body, dict) else {}))

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        print(f"browser-bridge on http://{self.host}:{self.port}", flush=True)
        self._server.serve_forever()

    def start_background(self) -> None:
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

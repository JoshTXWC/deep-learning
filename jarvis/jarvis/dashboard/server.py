# SPDX-License-Identifier: AGPL-3.0-or-later
"""Optional Jarvis dashboard — localhost only."""
from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from jarvis.assistant import Assistant

STATIC = Path(__file__).resolve().parent / "static"


def make_handler(assistant: "Assistant"):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: N802
            return

        def _json(self, code: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path: Path, content_type: str):
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                return self._file(STATIC / "index.html", "text/html; charset=utf-8")
            if path == "/app.css":
                return self._file(STATIC / "app.css", "text/css; charset=utf-8")
            if path == "/app.js":
                return self._file(STATIC / "app.js", "application/javascript; charset=utf-8")
            if path == "/api/status":
                return self._json(200, assistant.status())
            if path == "/api/audit":
                return self._json(200, {"events": assistant.audit.recent(40)})
            if path == "/api/memory":
                hits = assistant.memory.search("", limit=20)
                return self._json(200, {"items": hits})
            self.send_error(404)

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "invalid json"})
            path = urlparse(self.path).path
            if path == "/api/stop":
                assistant.stop_all_actions()
                return self._json(200, {"ok": True})
            if path == "/api/clear-stop":
                assistant.clear_stop()
                return self._json(200, {"ok": True})
            if path == "/api/approve":
                action_id = data.get("id")
                approved = bool(data.get("approved"))
                pending = {p.id: p for p in assistant.gate.list_pending()}
                action = pending.get(action_id)
                if not action:
                    return self._json(404, {"error": "unknown action"})
                # Re-run decision path: remove pending and optionally grant
                assistant.gate.resolve(action_id, approved)
                if approved:
                    # Fresh, action-specific approval — including high-risk.
                    result = assistant.tools.execute(
                        action.tool, action.arguments, preapproved=True
                    )
                    return self._json(200, {"ok": True, "result": result})
                return self._json(200, {"ok": True, "denied": True})
            if path == "/api/provider":
                provider = data.get("provider")
                model = data.get("model")
                if provider:
                    try:
                        assistant.switch_provider(provider, model)
                    except Exception as e:  # noqa: BLE001
                        return self._json(400, {"error": str(e)})
                elif model:
                    assistant.cfg["model"] = model
                return self._json(200, assistant.status())
            self.send_error(404)

    return Handler


def run_dashboard(assistant: "Assistant", *, open_browser: bool = True) -> None:
    port = int(assistant.cfg.get("dashboard_port") or 8795)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(assistant))
    url = f"http://127.0.0.1:{port}/"
    print(f"Jarvis dashboard: {url} (localhost only)", flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

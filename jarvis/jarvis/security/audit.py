# SPDX-License-Identifier: AGPL-3.0-or-later
"""Append-only audit history of tool decisions and executions."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from jarvis.security.secrets import redact


class AuditLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(self, event: str, **fields) -> None:
        row = {"ts": time.time(), "event": event}
        for k, v in fields.items():
            if isinstance(v, str):
                row[k] = redact(v)
            else:
                row[k] = v
        line = json.dumps(row, ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def recent(self, limit: int = 50) -> list[dict]:
        if not self.path.is_file():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

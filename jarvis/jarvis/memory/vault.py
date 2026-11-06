# SPDX-License-Identifier: AGPL-3.0-or-later
"""Local markdown memory — works offline without OpenAI."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from jarvis.security.secrets import looks_sensitive, redact


class MemoryVault:
    def __init__(self, root: Path, *, expire_days: int = 0):
        self.root = root
        self.expire_days = expire_days
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "conversations").mkdir(exist_ok=True)
        (self.root / "preferences").mkdir(exist_ok=True)
        (self.root / "projects").mkdir(exist_ok=True)
        self.exclusions_file = self.root / "exclusions.json"
        if not self.exclusions_file.exists():
            self.exclusions_file.write_text(
                json.dumps({"patterns": ["password", "api_key", "secret", "ssn"]}, indent=2),
                encoding="utf-8",
            )

    @classmethod
    def from_config(cls, cfg: dict) -> "MemoryVault":
        mem = cfg.get("memory_dir") or ""
        if not mem:
            mem = str(Path(cfg.get("agent_dir") or ".") / "jarvis-memory")
        return cls(Path(mem), expire_days=int(cfg.get("memory_expire_days") or 0))

    def _excluded(self, text: str) -> bool:
        try:
            patterns = json.loads(self.exclusions_file.read_text(encoding="utf-8")).get(
                "patterns"
            ) or []
        except (OSError, ValueError):
            patterns = []
        low = text.lower()
        return any(p.lower() in low for p in patterns if p)

    def save_preference(self, key: str, value: str) -> Path:
        if looks_sensitive(value) or self._excluded(value):
            raise ValueError("Refused to store sensitive preference.")
        path = self.root / "preferences" / f"{_safe(key)}.md"
        path.write_text(
            f"# Preference: {key}\n\nSaved: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{redact(value)}\n",
            encoding="utf-8",
        )
        return path

    def save_conversation_summary(self, title: str, summary: str, *, project: str | None = None) -> Path:
        if looks_sensitive(summary) or self._excluded(summary):
            summary = redact(summary)
            if self._excluded(summary):
                raise ValueError("Refused to store sensitive memory.")
        folder = self.root / "projects" / _safe(project) if project else self.root / "conversations"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{int(time.time())}-{_safe(title)}.md"
        path.write_text(
            f"# {title}\n\nSaved: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Source: local Jarvis memory (not uploaded unless you use a cloud provider for chat)\n\n"
            f"{summary}\n",
            encoding="utf-8",
        )
        return path

    def delete(self, path: str) -> None:
        p = Path(path).resolve()
        p.relative_to(self.root.resolve())
        if p.is_file():
            p.unlink()

    def search(self, query: str, limit: int = 8) -> list[dict]:
        self._expire()
        q = (query or "").lower().strip()
        hits = []
        for path in self.root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if q and q not in text.lower() and q not in path.name.lower():
                continue
            hits.append(
                {
                    "title": path.stem,
                    "path": str(path),
                    "snippet": text[:800],
                }
            )
            if len(hits) >= limit:
                break
        return hits

    def _expire(self) -> None:
        if self.expire_days <= 0:
            return
        cutoff = time.time() - self.expire_days * 86400
        for path in self.root.rglob("*.md"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "note").strip())[:80] or "note"

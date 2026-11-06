# SPDX-License-Identifier: AGPL-3.0-or-later
"""Built-in tool handlers. Computer tools start read-only by default."""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Any

import httpx

from jarvis.security.secrets import looks_sensitive, redact


def _approved_path(path: str, cfg: dict) -> Path:
    p = Path(path).expanduser().resolve()
    for root in cfg.get("approved_dirs") or []:
        try:
            p.relative_to(Path(root).resolve())
            return p
        except ValueError:
            continue
    raise PermissionError(f"Path not in approved directories: {p}")


def handle_list_files(args: dict[str, Any], cfg: dict) -> str:
    p = _approved_path(args["path"], cfg)
    if not p.exists():
        return f"Path does not exist: {p}"
    if p.is_file():
        return str(p)
    entries = sorted(p.iterdir(), key=lambda x: x.name.lower())[:200]
    lines = [("d " if e.is_dir() else "f ") + e.name for e in entries]
    return "\n".join(lines) or "(empty)"


def handle_read_file(args: dict[str, Any], cfg: dict) -> str:
    p = _approved_path(args["path"], cfg)
    if not p.is_file():
        return f"Not a file: {p}"
    data = p.read_text(encoding="utf-8", errors="replace")
    if looks_sensitive(data):
        data = redact(data)
    return data[:100_000]


def handle_write_file(args: dict[str, Any], cfg: dict) -> str:
    if cfg.get("computer_mode") == "off":
        return "Computer assistant is disabled."
    p = _approved_path(args["path"], cfg)
    content = args.get("content") or ""
    if looks_sensitive(content):
        return "Refused: content appears to contain secrets."
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {p}"


def handle_run_command(args: dict[str, Any], cfg: dict) -> str:
    if cfg.get("computer_mode") == "read_only":
        return "Computer assistant is in read-only mode. Change computer_mode to 'ask' after review."
    if cfg.get("computer_mode") == "off":
        return "Computer assistant is disabled."
    cmd = args["command"]
    cwd = args.get("cwd") or cfg.get("agent_dir")
    cwd_path = _approved_path(cwd, cfg)
    # shell=False — never pass model text to a shell.
    parts = cmd.split()
    proc = subprocess.run(
        parts,
        cwd=str(cwd_path),
        capture_output=True,
        text=True,
        timeout=60,
        shell=False,
        check=False,
    )
    out = (proc.stdout or "")[-8000:]
    err = (proc.stderr or "")[-2000:]
    return f"exit={proc.returncode}\n{out}\n{err}".strip()


def handle_system_info(_args: dict[str, Any], cfg: dict) -> str:
    return (
        f"system={platform.system()} {platform.release()}\n"
        f"machine={platform.machine()}\n"
        f"python={platform.python_version()}\n"
        f"agent_dir={cfg.get('agent_dir')}\n"
        f"computer_mode={cfg.get('computer_mode')}\n"
        f"provider={cfg.get('provider')} model={cfg.get('model')}"
    )


def handle_git_status(_args: dict[str, Any], cfg: dict) -> str:
    cwd = _approved_path(cfg.get("agent_dir") or ".", cfg)
    proc = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
        shell=False,
        check=False,
    )
    return (proc.stdout or proc.stderr or "").strip() or "(clean)"


def handle_web_search(args: dict[str, Any], cfg: dict) -> str:
    if not cfg.get("web_search_enabled"):
        return "Web search is disabled. Enable web_search_enabled in jarvis.json."
    query = args["query"]
    # DuckDuckGo Instant Answer API — no key; public facts only.
    url = "https://api.duckduckgo.com/"
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get(
                url,
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        return f"Search failed: {e}"

    parts = []
    if data.get("AbstractText"):
        parts.append(data["AbstractText"])
        if data.get("AbstractURL"):
            parts.append(f"Source: {data['AbstractURL']}")
    for topic in (data.get("RelatedTopics") or [])[:5]:
        if isinstance(topic, dict) and topic.get("Text"):
            line = topic["Text"]
            if topic.get("FirstURL"):
                line += f" ({topic['FirstURL']})"
            parts.append(line)
    if not parts:
        return (
            "No structured results. Treat any follow-up guesses as model conclusions, "
            f"not retrieved facts. Query was: {query}"
        )
    header = (
        "RETRIEVED INFORMATION (not model conclusions). Sources listed when available.\n"
    )
    return header + "\n".join(parts)


def handle_delete_path(args: dict[str, Any], cfg: dict) -> str:
    # Even after approval, refuse deleting outside approved dirs; never recursive wipe of roots.
    p = _approved_path(args["path"], cfg)
    agent = Path(cfg.get("agent_dir") or ".").resolve()
    if p in {Path("/"), Path("C:\\"), agent, Path.home()}:
        return "Refused: refusing to delete a root or home path."
    if p.is_dir():
        # Only empty dirs for extra safety in v0.1
        if any(p.iterdir()):
            return "Refused: directory is not empty."
        p.rmdir()
    elif p.is_file():
        p.unlink()
    else:
        return f"Nothing to delete: {p}"
    return f"Deleted {p}"


def handle_memory_search(args: dict[str, Any], cfg: dict) -> str:
    from jarvis.memory.vault import MemoryVault

    vault = MemoryVault.from_config(cfg)
    hits = vault.search(args.get("query") or "", limit=8)
    if not hits:
        return "No memory hits."
    return "\n\n".join(f"# {h['title']}\n{h['snippet']}" for h in hits)


def default_handlers() -> dict[str, Any]:
    return {
        "list_files": handle_list_files,
        "read_file": handle_read_file,
        "write_file": handle_write_file,
        "run_command": handle_run_command,
        "system_info": handle_system_info,
        "git_status": handle_git_status,
        "web_search": handle_web_search,
        "delete_path": handle_delete_path,
        "memory_search": handle_memory_search,
    }

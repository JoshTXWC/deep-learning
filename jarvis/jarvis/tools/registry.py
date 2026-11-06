# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tool registry: OpenAI function schemas + safe execution."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from jarvis.security.audit import AuditLog
from jarvis.security.injection import quarantine_retrieved
from jarvis.security.permissions import PermissionGate
from jarvis.security.schemas import command_allowed, validate_tool_args
from jarvis.security.secrets import looks_sensitive, redact

ToolHandler = Callable[[dict[str, Any], dict], str]


def openai_tool_specs(enabled: set[str] | None = None) -> list[dict[str, Any]]:
    specs = [
        {
            "type": "function",
            "function": {
                "name": "memory_search",
                "description": "Search local memory vault (read-only).",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Optional web search for public facts. Results are untrusted.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files in an approved directory.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a text file from an approved directory.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create or modify a file (requires approval).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Run an allowlisted development command (requires approval).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"},
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "system_info",
                "description": "Explain basic local system information (read-only).",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Show git status in the agent directory (read-only).",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_path",
                "description": "Delete a file or directory (HIGH RISK — always needs fresh approval).",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
    ]
    if enabled is None:
        return specs
    return [s for s in specs if s["function"]["name"] in enabled]


class ToolExecutor:
    def __init__(
        self,
        cfg: dict,
        gate: PermissionGate,
        audit: AuditLog,
        handlers: dict[str, ToolHandler] | None = None,
    ):
        self.cfg = cfg
        self.gate = gate
        self.audit = audit
        self.handlers = handlers or {}

    def _in_approved(self, path: str) -> Path:
        p = Path(path).expanduser().resolve()
        approved = [Path(d).resolve() for d in self.cfg.get("approved_dirs") or []]
        for root in approved:
            try:
                p.relative_to(root)
                return p
            except ValueError:
                continue
        raise PermissionError(f"Path not in approved directories: {p}")

    def execute(
        self,
        tool: str,
        arguments: dict[str, Any],
        *,
        preapproved: bool = False,
    ) -> str:
        if self.gate.is_stopped:
            self.audit.record("tool_blocked_stop", tool=tool)
            return "Blocked: emergency Stop All Actions is active."

        try:
            args = validate_tool_args(tool, arguments or {})
        except ValueError as e:
            self.audit.record("tool_schema_reject", tool=tool, error=str(e))
            return f"Tool arguments rejected: {e}"

        if tool == "run_command" and not command_allowed(args.get("command", "")):
            self.audit.record("tool_command_reject", tool=tool, command=args.get("command", ""))
            return "Command rejected: not on the allowlist."

        preview = f"{tool}({json.dumps(args, ensure_ascii=False)[:500]})"
        if preapproved:
            allowed, pending = True, None
            self.audit.record("tool_preapproved", tool=tool, preview=preview)
        else:
            allowed, pending = self.gate.decide(tool, args, preview)
        if not allowed:
            self.audit.record(
                "tool_awaiting_approval" if pending else "tool_denied",
                tool=tool,
                preview=preview,
                action_id=pending.id if pending else None,
            )
            if pending:
                return (
                    f"Approval required ({pending.risk.value}). "
                    f"Preview: {preview}. Action id: {pending.id}"
                )
            return f"Denied: {preview}"

        handler = self.handlers.get(tool)
        if handler is None:
            self.audit.record("tool_missing_handler", tool=tool)
            return f"No handler registered for {tool}."

        try:
            result = handler(args, self.cfg)
        except Exception as e:  # noqa: BLE001 — surface to model safely
            self.audit.record("tool_error", tool=tool, error=str(e))
            return f"Tool error: {e}"

        if looks_sensitive(result):
            result = redact(result)
        # Quarantine retrieved-ish outputs
        if tool in {"web_search", "read_file", "summarize_document", "memory_search"}:
            result = quarantine_retrieved(result, source=tool)

        self.audit.record("tool_executed", tool=tool, preview=preview)
        return result

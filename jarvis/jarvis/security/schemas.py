# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strict tool-argument validation and command allowlisting."""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class PathArgs(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


class WriteFileArgs(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    content: str = Field(default="", max_length=500_000)


class RunCommandArgs(BaseModel):
    command: str = Field(min_length=1, max_length=500)
    cwd: str | None = Field(default=None, max_length=1024)

    @field_validator("command")
    @classmethod
    def no_shell_metachar_chains(cls, v: str) -> str:
        # Block obvious chaining / substitution. Allowlist check is separate.
        if re.search(r"[|&;`$<>\n]", v):
            raise ValueError("Command contains blocked shell metacharacters.")
        return v


class WebSearchArgs(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class OpenUrlArgs(BaseModel):
    url: str = Field(min_length=1, max_length=2000)

    @field_validator("url")
    @classmethod
    def http_only(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("http://")):
            raise ValueError("Only http(s) URLs are allowed.")
        return v


class MemoryWriteArgs(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=50_000)
    project: str | None = Field(default=None, max_length=200)


class OrganizeFilesArgs(BaseModel):
    source_dir: str = Field(min_length=1, max_length=1024)
    plan: str = Field(min_length=1, max_length=5000)


SCHEMAS: dict[str, type[BaseModel]] = {
    "read_file": PathArgs,
    "list_files": PathArgs,
    "summarize_document": PathArgs,
    "delete_path": PathArgs,
    "write_file": WriteFileArgs,
    "run_command": RunCommandArgs,
    "admin_command": RunCommandArgs,
    "web_search": WebSearchArgs,
    "open_url": OpenUrlArgs,
    "memory_write": MemoryWriteArgs,
    "organize_files": OrganizeFilesArgs,
}

# Development / read-only helpers — first token must match.
COMMAND_ALLOWLIST = {
    "git",
    "python",
    "python3",
    "uv",
    "node",
    "npm",
    "npx",
    "pytest",
    "dir",
    "ls",
    "type",
    "cat",
    "echo",
    "where",
    "which",
    "rg",
    "grep",
}


def validate_tool_args(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    model = SCHEMAS.get(tool)
    if model is None:
        # Unknown tools: only allow flat JSON-ish scalars/strings under size caps.
        cleaned: dict[str, Any] = {}
        for k, v in (arguments or {}).items():
            if not isinstance(k, str) or len(k) > 64:
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                if isinstance(v, str) and len(v) > 10_000:
                    raise ValueError(f"Argument {k!r} too large.")
                cleaned[k] = v
            else:
                raise ValueError(f"Argument {k!r} has unsupported type.")
        return cleaned
    try:
        return model.model_validate(arguments or {}).model_dump()
    except ValidationError as e:
        raise ValueError(str(e)) from e


def command_allowed(command: str) -> bool:
    first = (command or "").strip().split()[0] if command else ""
    # Strip Windows path prefixes to basename
    first = first.replace("\\", "/").split("/")[-1].lower()
    if first.endswith(".exe"):
        first = first[:-4]
    return first in COMMAND_ALLOWLIST

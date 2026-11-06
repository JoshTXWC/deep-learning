# SPDX-License-Identifier: AGPL-3.0-or-later
"""Common provider adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class ChatMessage:
    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class StreamEvent:
    type: str  # text_delta | tool_calls | usage | error | done
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    error: str = ""
    model: str = ""


class ProviderError(Exception):
    """User-facing provider failure (auth, rate limit, outage)."""

    def __init__(self, message: str, *, code: str = "provider_error"):
        super().__init__(message)
        self.code = code


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        timeout_s: float = 60,
    ) -> AsyncIterator[StreamEvent]:
        ...

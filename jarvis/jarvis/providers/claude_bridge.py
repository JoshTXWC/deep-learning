# SPDX-License-Identifier: AGPL-3.0-or-later
"""Optional Claude bridge — keeps Claude as a selectable provider.

This does not reimplement the Claude Agent SDK. When provider=claude,
users should continue using upstream backtalk + Claude Code. This adapter
returns a clear message so the UI can route correctly.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from jarvis.providers.base import ChatMessage, Provider, ProviderError, StreamEvent


class ClaudeBridgeProvider(Provider):
    name = "claude"

    async def list_models(self) -> list[str]:
        return ["claude-sonnet-via-backtalk", "claude-opus-via-backtalk"]

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
        raise ProviderError(
            "Claude provider uses the existing backtalk + Claude Code stack. "
            "Start with ./start.sh voice (or start.bat voice), or switch "
            "provider to 'openai' / 'ollama' in jarvis.json.",
            code="use_backtalk",
        )
        yield  # pragma: no cover — makes this an async generator type

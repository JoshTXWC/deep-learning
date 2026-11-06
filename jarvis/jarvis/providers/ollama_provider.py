# SPDX-License-Identifier: AGPL-3.0-or-later
"""Future local-model provider via Ollama (OpenAI-compatible subset)."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from jarvis.providers.base import (
    ChatMessage,
    Provider,
    ProviderError,
    StreamEvent,
    ToolCall,
)


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.base_url}/api/tags")
            if r.status_code >= 400:
                raise ProviderError(
                    "Ollama is not reachable. Start Ollama locally to use offline models.",
                    code="network",
                )
            models = r.json().get("models") or []
            return [m.get("name") for m in models if m.get("name")]
        except ProviderError:
            raise
        except httpx.HTTPError as e:
            raise ProviderError(f"Ollama unavailable: {e}", code="network") from e

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
        # Prefer OpenAI-compatible endpoint when available.
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content or ""} for m in messages],
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_output_tokens},
        }
        if tools:
            body["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=body,
                ) as resp:
                    if resp.status_code >= 400:
                        raise ProviderError(
                            f"Ollama chat failed ({resp.status_code}). Is model {model!r} pulled?",
                            code="model_unavailable",
                        )
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = chunk.get("message") or {}
                        text = msg.get("content") or ""
                        if text:
                            yield StreamEvent(type="text_delta", text=text, model=model)
                        raw_tools = msg.get("tool_calls") or []
                        if raw_tools:
                            calls = []
                            for i, tc in enumerate(raw_tools):
                                fn = tc.get("function") or {}
                                args = fn.get("arguments") or {}
                                if isinstance(args, str):
                                    try:
                                        args = json.loads(args)
                                    except json.JSONDecodeError:
                                        args = {}
                                calls.append(
                                    ToolCall(
                                        id=tc.get("id") or f"ollama_{i}",
                                        name=fn.get("name") or "",
                                        arguments=args if isinstance(args, dict) else {},
                                    )
                                )
                            yield StreamEvent(type="tool_calls", tool_calls=calls, model=model)
                        if chunk.get("done"):
                            break
        except httpx.TimeoutException as e:
            raise ProviderError("Ollama request timed out.", code="timeout") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"Ollama network error: {e}", code="network") from e
        yield StreamEvent(type="done", model=model)

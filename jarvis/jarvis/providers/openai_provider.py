# SPDX-License-Identifier: AGPL-3.0-or-later
"""OpenAI Chat Completions adapter with streaming + tool calls."""
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


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api.openai.com/v1",
        max_retries: int = 2,
    ):
        if not api_key:
            raise ProviderError(
                "OpenAI API key missing. Set OPENAI_API_KEY in your environment or .env file.",
                code="auth",
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{self.base_url}/models", headers=self._headers()
                )
            if r.status_code in (401, 403):
                raise ProviderError(
                    "OpenAI authentication failed. Check OPENAI_API_KEY.",
                    code="auth",
                )
            r.raise_for_status()
            data = r.json().get("data") or []
            ids = sorted(
                m["id"]
                for m in data
                if isinstance(m, dict) and isinstance(m.get("id"), str)
                and (m["id"].startswith("gpt") or m["id"].startswith("o"))
            )
            return ids
        except ProviderError:
            raise
        except httpx.HTTPError as e:
            raise ProviderError(f"Could not list OpenAI models: {e}", code="network") from e

    def _serialize_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            item: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                item["content"] = m.content
            if m.name:
                item["name"] = m.name
            if m.tool_call_id:
                item["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                item["tool_calls"] = m.tool_calls
            out.append(item)
        return out

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
        body: dict[str, Any] = {
            "model": model,
            "messages": self._serialize_messages(messages),
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        attempt = 0
        while True:
            attempt += 1
            try:
                async for event in self._stream_once(body, timeout_s=timeout_s):
                    yield event
                return
            except ProviderError as e:
                retryable = e.code in ("rate_limit", "timeout", "network", "server")
                if not retryable or attempt > self.max_retries:
                    yield StreamEvent(type="error", error=str(e), model=model)
                    yield StreamEvent(type="done", model=model)
                    return
                continue

    async def _stream_once(
        self, body: dict[str, Any], *, timeout_s: float
    ) -> AsyncIterator[StreamEvent]:
        model = body.get("model", "")
        tool_acc: dict[int, dict[str, Any]] = {}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                ) as resp:
                    if resp.status_code in (401, 403):
                        raise ProviderError(
                            "OpenAI authentication failed. Check OPENAI_API_KEY.",
                            code="auth",
                        )
                    if resp.status_code == 404:
                        raise ProviderError(
                            f"Model unavailable: {model}. Pick another model in settings.",
                            code="model_unavailable",
                        )
                    if resp.status_code == 429:
                        raise ProviderError(
                            "OpenAI rate limit hit. Wait a moment and try again.",
                            code="rate_limit",
                        )
                    if resp.status_code >= 500:
                        raise ProviderError(
                            "OpenAI is having server issues.",
                            code="server",
                        )
                    if resp.status_code >= 400:
                        detail = (await resp.aread()).decode("utf-8", errors="replace")[:300]
                        raise ProviderError(
                            f"OpenAI request failed ({resp.status_code}): {detail}",
                            code="provider_error",
                        )

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        usage = chunk.get("usage") or {}
                        if usage:
                            yield StreamEvent(
                                type="usage",
                                usage={
                                    "input_tokens": int(usage.get("prompt_tokens") or 0),
                                    "output_tokens": int(usage.get("completion_tokens") or 0),
                                },
                                model=model,
                            )
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        text = delta.get("content") or ""
                        if text:
                            yield StreamEvent(type="text_delta", text=text, model=model)
                        for tc in delta.get("tool_calls") or []:
                            idx = int(tc.get("index") or 0)
                            slot = tool_acc.setdefault(
                                idx,
                                {"id": "", "name": "", "arguments": ""},
                            )
                            if tc.get("id"):
                                slot["id"] = tc["id"]
                            fn = tc.get("function") or {}
                            if fn.get("name"):
                                slot["name"] = fn["name"]
                            if fn.get("arguments"):
                                slot["arguments"] += fn["arguments"]
        except httpx.TimeoutException as e:
            raise ProviderError("OpenAI request timed out.", code="timeout") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"Network error talking to OpenAI: {e}", code="network") from e

        if tool_acc:
            calls: list[ToolCall] = []
            for slot in tool_acc.values():
                try:
                    args = json.loads(slot["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                calls.append(
                    ToolCall(
                        id=slot["id"] or f"call_{slot['name']}",
                        name=slot["name"],
                        arguments=args,
                    )
                )
            yield StreamEvent(type="tool_calls", tool_calls=calls, model=model)
        yield StreamEvent(type="done", model=model)

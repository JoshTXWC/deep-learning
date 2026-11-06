# SPDX-License-Identifier: AGPL-3.0-or-later
import json

import httpx
import pytest

from jarvis.providers.base import ChatMessage, ProviderError
from jarvis.providers.openai_provider import OpenAIProvider


class _StreamResp:
    def __init__(self, status_code: int, lines: list[str]):
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return b'{"error":"nope"}'

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _Client:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, *args, **kwargs):
        return self._resp


@pytest.mark.asyncio
async def test_stream_text(monkeypatch):
    lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{"content":" world"}}],"usage":{"prompt_tokens":3,"completion_tokens":2}}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _Client(_StreamResp(200, lines)),
    )
    p = OpenAIProvider(api_key="sk-test", max_retries=0)
    events = []
    async for e in p.stream_chat([ChatMessage(role="user", content="hi")], model="gpt-4.1-mini"):
        events.append(e)
    texts = "".join(e.text for e in events if e.type == "text_delta")
    assert texts == "Hello world"
    assert any(e.type == "usage" for e in events)
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_auth_failure(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _Client(_StreamResp(401, [])),
    )
    p = OpenAIProvider(api_key="sk-bad", max_retries=0)
    events = []
    async for e in p.stream_chat([ChatMessage(role="user", content="hi")], model="gpt-4.1-mini"):
        events.append(e)
    assert any(e.type == "error" and "authentication" in e.error.lower() for e in events)


def test_missing_key():
    with pytest.raises(ProviderError):
        OpenAIProvider(api_key=None)

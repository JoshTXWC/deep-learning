# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

import pytest

from jarvis.assistant import Assistant
from jarvis.providers.base import Provider, StreamEvent
from jarvis.usage.tracker import UsageTracker


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, events):
        self._events = events

    async def list_models(self):
        return ["fake-1"]

    async def stream_chat(self, messages, **kwargs):
        for e in self._events:
            yield e


def _cfg(tmp_path: Path) -> dict:
    return {
        "name": "Jarvis",
        "agent_dir": str(tmp_path),
        "provider": "openai",
        "model": "fake-1",
        "permission_mode": "ask",
        "computer_mode": "read_only",
        "web_search_enabled": False,
        "signals_dir": str(tmp_path / "signals"),
        "approved_dirs": [str(tmp_path)],
        "max_tool_rounds": 3,
        "max_output_tokens": 128,
        "request_timeout_s": 5,
        "daily_budget_usd": 100,
        "monthly_budget_usd": 100,
        "budget_warn_pct": 80,
        "mic_mode": "ptt",
        "stt_provider": "local",
        "tts_provider": "local",
        "memory_dir": str(tmp_path / "mem"),
    }


def test_rejects_disallowed_command(tmp_path):
    a = Assistant(cfg=_cfg(tmp_path), provider=FakeProvider([]))
    result = a.tools.execute("run_command", {"command": "rm -rf /"})
    assert "rejected" in result.lower() or "allowlist" in result.lower()


def test_write_requires_approval(tmp_path):
    a = Assistant(cfg=_cfg(tmp_path), provider=FakeProvider([]))
    result = a.tools.execute("write_file", {"path": str(tmp_path / "x.txt"), "content": "hi"})
    assert "Approval required" in result


def test_memory_persistence_offline(tmp_path):
    a = Assistant(cfg=_cfg(tmp_path), provider=FakeProvider([]))
    path = a.memory.save_conversation_summary("hello", "remember the blue notebook")
    assert path.exists()
    hits = a.memory.search("blue notebook")
    assert hits


def test_budget_blocks(tmp_path):
    pricing = Path(__file__).resolve().parents[1] / "jarvis" / "jarvis" / "usage" / "pricing.json"
    cfg = _cfg(tmp_path)
    cfg["daily_budget_usd"] = 0.0000001
    tracker = UsageTracker(tmp_path / "usage.json", pricing, cfg)
    tracker.record(provider="openai", model="gpt-4.1-mini", input_tokens=100000, output_tokens=100000)
    ok, reason = tracker.allow_request()
    assert ok is False
    assert "budget" in reason.lower()


@pytest.mark.asyncio
async def test_provider_switch_and_stream(tmp_path):
    events = [
        StreamEvent(type="text_delta", text="Hi"),
        StreamEvent(type="usage", usage={"input_tokens": 1, "output_tokens": 1}),
        StreamEvent(type="done"),
    ]
    a = Assistant(cfg=_cfg(tmp_path), provider=FakeProvider(events))
    out = await a.chat("hello")
    assert "Hi" in out
    # switching to ollama without server should still construct provider
    a.cfg["provider"] = "ollama"
    from jarvis.providers import create_provider

    a.provider = create_provider(a.cfg)
    assert a.provider.name == "ollama"

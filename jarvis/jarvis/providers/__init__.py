# SPDX-License-Identifier: AGPL-3.0-or-later
"""Provider factory."""
from __future__ import annotations

from jarvis.config import openai_api_key
from jarvis.providers.base import Provider, ProviderError
from jarvis.providers.claude_bridge import ClaudeBridgeProvider
from jarvis.providers.ollama_provider import OllamaProvider
from jarvis.providers.openai_provider import OpenAIProvider


def create_provider(cfg: dict) -> Provider:
    name = (cfg.get("provider") or "openai").lower()
    if name == "openai":
        return OpenAIProvider(
            api_key=openai_api_key(),
            base_url=cfg.get("openai_base_url") or "https://api.openai.com/v1",
            max_retries=int(cfg.get("max_retries") or 2),
        )
    if name == "ollama":
        return OllamaProvider(base_url=cfg.get("ollama_base_url") or "http://127.0.0.1:11434")
    if name == "claude":
        return ClaudeBridgeProvider()
    raise ProviderError(f"Unknown provider: {name}", code="config")


__all__ = [
    "Provider",
    "ProviderError",
    "OpenAIProvider",
    "OllamaProvider",
    "ClaudeBridgeProvider",
    "create_provider",
]

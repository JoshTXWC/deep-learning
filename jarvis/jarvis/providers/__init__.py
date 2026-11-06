# SPDX-License-Identifier: AGPL-3.0-or-later
"""Provider factory — ChatGPT / OpenAI only."""
from __future__ import annotations

from jarvis.config import openai_api_key
from jarvis.providers.base import Provider, ProviderError
from jarvis.providers.openai_provider import OpenAIProvider


def create_provider(cfg: dict) -> Provider:
    name = (cfg.get("provider") or "openai").lower()
    if name in ("openai", "chatgpt"):
        return OpenAIProvider(
            api_key=openai_api_key(),
            base_url=cfg.get("openai_base_url") or "https://api.openai.com/v1",
            max_retries=int(cfg.get("max_retries") or 2),
        )
    raise ProviderError(
        f"Only ChatGPT (OpenAI) is supported. Got provider={name!r}. "
        "Set provider to \"openai\" in jarvis.json.",
        code="config",
    )


__all__ = [
    "Provider",
    "ProviderError",
    "OpenAIProvider",
    "create_provider",
]

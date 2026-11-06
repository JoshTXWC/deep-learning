# SPDX-License-Identifier: AGPL-3.0-or-later
"""Redact secrets before they enter prompts, logs, or memory."""
from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{16,})\b"),
    re.compile(r"(?i)\b(sk-proj-[A-Za-z0-9_-]{16,})\b"),
    re.compile(r"(?i)\b(OPENAI_API_KEY\s*[=:]\s*)(\S+)"),
    re.compile(r"(?i)\b(ELEVENLABS_API_KEY\s*[=:]\s*)(\S+)"),
    re.compile(r"(?i)\b(api[_-]?key\s*[=:]\s*)([A-Za-z0-9_\-]{16,})"),
    re.compile(r"(?i)\b(bearer\s+)([A-Za-z0-9._\-]{16,})"),
    re.compile(r"(?i)\b(password\s*[=:]\s*)(\S+)"),
    re.compile(
        r"(?i)\b([A-Z0-9_]*(SECRET|TOKEN|PASSWORD|CREDENTIAL)[A-Z0-9_]*\s*[=:]\s*)(\S+)"
    ),
]


def redact(text: str | None) -> str:
    if not text:
        return ""
    out = text
    for pat in _PATTERNS:
        if pat.groups >= 2:
            out = pat.sub(lambda m: f"{m.group(1)}[REDACTED]", out)
        else:
            out = pat.sub("[REDACTED]", out)
    return out


def looks_sensitive(text: str | None) -> bool:
    if not text:
        return False
    return redact(text) != text

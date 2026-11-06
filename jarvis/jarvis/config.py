# SPDX-License-Identifier: AGPL-3.0-or-later
"""Load jarvis.json + environment. Secrets never live in the JSON file."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
HOME_CANDIDATE = REPO.parent
CONFIG_PATH = Path(os.environ.get("JARVIS_CONFIG") or (REPO / "jarvis.json"))

DEFAULTS: dict = {
    "name": "Jarvis",
    "agent_dir": str(HOME_CANDIDATE),
    "provider": "openai",  # openai | ollama | claude
    "model": "gpt-4.1-mini",
    "fallback_model": "gpt-4.1-nano",
    "reasoning_provider": "openai",
    "stt_provider": "local",  # local | openai
    "tts_provider": "local",  # local | openai | elevenlabs
    "openai_base_url": "https://api.openai.com/v1",
    "ollama_base_url": "http://127.0.0.1:11434",
    "temperature": 0.7,
    "max_output_tokens": 2048,
    "request_timeout_s": 60,
    "max_retries": 2,
    "max_tool_rounds": 8,
    "mic_mode": "ptt",  # ptt | open
    "wake_word_enabled": False,
    "voice": "alloy",
    "speaking_speed": 1.0,
    "visualizer_theme": "board",  # board | radial | rain | neural | jarvis-orb
    "dashboard_enabled": True,
    "dashboard_port": 8795,
    "memory_dir": "",
    "memory_expire_days": 0,
    "approved_dirs": [],
    "computer_mode": "read_only",  # read_only | ask | off
    "web_search_enabled": False,
    "webcam_enabled": False,
    "gesture_controls": False,
    "monthly_budget_usd": 20.0,
    "daily_budget_usd": 5.0,
    "budget_warn_pct": 80,
    "permission_mode": "ask",  # ask only for high-risk; bypass never covers high-risk
    "signals_dir": "",
    "greeting": "",
}


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path | None = None) -> dict:
    """Merge defaults with jarvis.json and expand paths. Loads .env for secrets."""
    load_dotenv(REPO / ".env")
    load_dotenv(HOME_CANDIDATE / ".env")
    cfg = deepcopy(DEFAULTS)
    cfg_path = path or CONFIG_PATH
    if cfg_path.is_file():
        try:
            user = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg = _deep_merge(cfg, user)
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Invalid jarvis config at {cfg_path}: {e}") from e

    for key in ("agent_dir", "memory_dir", "signals_dir"):
        val = cfg.get(key) or ""
        if val:
            cfg[key] = str(Path(val).expanduser().resolve())
    if not cfg.get("signals_dir"):
        # Prefer sibling backtalk bus so existing faces keep working.
        bt = HOME_CANDIDATE / "backtalk"
        cfg["signals_dir"] = str(bt if bt.is_dir() else REPO / "state")
    Path(cfg["signals_dir"]).mkdir(parents=True, exist_ok=True)

    approved = []
    for d in cfg.get("approved_dirs") or []:
        approved.append(str(Path(d).expanduser().resolve()))
    agent = cfg.get("agent_dir")
    if agent and agent not in approved:
        approved.insert(0, agent)
    cfg["approved_dirs"] = approved
    return cfg


def openai_api_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY") or None


def save_config(cfg: dict, path: Path | None = None) -> None:
    """Persist non-secret settings only."""
    cfg_path = path or CONFIG_PATH
    safe = {k: v for k, v in cfg.items() if "key" not in k.lower() and "secret" not in k.lower()}
    cfg_path.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8")

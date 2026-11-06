# SPDX-License-Identifier: AGPL-3.0-or-later
"""Signal bus compatible with backtalk / ai-visualizer / barehands.

Writes the same tiny files upstream faces already read:
  .voice_state, .voice_waveform, .voice_loading_pid, ...
"""
from __future__ import annotations

import json
import time
from pathlib import Path


class SignalBus:
    def __init__(self, signals_dir: str | Path):
        self.dir = Path(signals_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def set_state(self, name: str) -> None:
        try:
            (self.dir / ".voice_state").write_text(name, encoding="utf-8")
        except OSError:
            pass

    def feed_waveform(self, samples: list[float] | None = None) -> None:
        try:
            payload = {
                "ts": time.time(),
                "samples": samples or [0.0] * 64,
            }
            (self.dir / ".voice_waveform").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            self.set_state("speaking")
        except OSError:
            pass

    def reply_done(self) -> None:
        try:
            (self.dir / ".voice_reply_done").write_text(
                json.dumps({"ts": time.time()}), encoding="utf-8"
            )
        except OSError:
            pass

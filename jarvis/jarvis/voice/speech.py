# SPDX-License-Identifier: AGPL-3.0-or-later
"""Speech provider selectors.

Local STT/TTS remain preferred for privacy. OpenAI Whisper/TTS are opt-in
and clearly disclosed — raw mic audio is only sent when stt_provider=openai.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpeechRouting:
    stt_provider: str
    tts_provider: str
    voice: str
    speaking_speed: float
    mic_mode: str
    wake_word_enabled: bool

    @classmethod
    def from_config(cls, cfg: dict) -> "SpeechRouting":
        return cls(
            stt_provider=cfg.get("stt_provider") or "local",
            tts_provider=cfg.get("tts_provider") or "local",
            voice=cfg.get("voice") or "alloy",
            speaking_speed=float(cfg.get("speaking_speed") or 1.0),
            mic_mode=cfg.get("mic_mode") or "ptt",
            wake_word_enabled=bool(cfg.get("wake_word_enabled")),
        )

    def disclosure(self) -> str:
        lines = [
            f"STT: {self.stt_provider}",
            f"TTS: {self.tts_provider}",
            f"Mic mode: {self.mic_mode} (default push-to-talk keeps the mic closed)",
        ]
        if self.stt_provider == "openai":
            lines.append(
                "NOTICE: microphone audio will be sent to OpenAI for transcription."
            )
        else:
            lines.append("Microphone audio stays local for speech recognition.")
        if self.tts_provider == "openai":
            lines.append("NOTICE: reply text is sent to OpenAI for speech synthesis.")
        elif self.tts_provider == "elevenlabs":
            lines.append("NOTICE: reply text is sent to ElevenLabs for speech synthesis.")
        else:
            lines.append("Speech synthesis uses the local/free engine when available.")
        if self.wake_word_enabled:
            lines.append("Wake-word detection is local-only.")
        return "\n".join(lines)

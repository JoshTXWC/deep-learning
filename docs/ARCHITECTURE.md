# Architecture — Secure Multi-Provider Jarvis

## Goal

Extend fullstack-agent so the assistant brain is **OpenAI (ChatGPT) only**. No Claude Code / backtalk wiring in this fork. Optional face/hands/memory pieces remain available.

## Layering

```
┌─────────────────────────────────────────────────────────┐
│  UI: Jarvis dashboard (optional) + existing faces       │
│      ai-visualizer / barehands (unchanged upstream)     │
└──────────────────────────▲──────────────────────────────┘
                           │ signal bus (.voice_*)
┌──────────────────────────┴──────────────────────────────┐
│  Voice adapters                                          │
│  STT: local whisper OR OpenAI Whisper API                │
│  TTS: Kokoro / ElevenLabs OR OpenAI TTS                  │
│  (local STT/TTS optional; OpenAI speech opt-in)          │
└──────────────────────────▲──────────────────────────────┘
                           │ Assistant interface
┌──────────────────────────┴──────────────────────────────┐
│  jarvis/  (this repo)                                    │
│  ├─ providers/   openai (ChatGPT) only                   │
│  ├─ security/    permissions, schemas, secrets, audit    │
│  ├─ tools/       search, computer, memory, git           │
│  ├─ usage/       tokens, budgets, pricing config         │
│  └─ memory/      vault summaries + exclusions            │
└─────────────────────────────────────────────────────────┘
                           │
              agent home (AGENTS.md / JARVIS.md + vault)
```

## Design rules

1. **Extension, not rewrite** — optional face/hands/memory still clone as siblings; Jarvis lives in this toolbox.
2. **ChatGPT only** — `Assistant.chat_stream()` talks to OpenAI; Claude/Ollama bridges are removed.
3. **Ask Before Acting** — default; high-risk never blanket-approved.
4. **Signal bus** — Jarvis writes `.voice_*` files so existing faces can still sync.
5. **Secrets** — `.env` / OS env only; `.env.example` placeholders; never committed.
6. **AGPL attribution** — Jared Rhodenizer copyright retained; Jarvis additions attributed in package headers.

## Config

- `jarvis/jarvis.json` (gitignored) from `jarvis.json.example`
- `.env` for `OPENAI_API_KEY` (and optional `ELEVENLABS_API_KEY`)
- Model/voice/budget settings editable without reinstall

## Launch

- Default: ChatGPT Jarvis dashboard via `start.sh` / `start.bat`

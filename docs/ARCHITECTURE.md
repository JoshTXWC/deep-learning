# Architecture — Secure Multi-Provider Jarvis

## Goal

Extend fullstack-agent so the assistant brain can be **OpenAI (ChatGPT)** or (later) **Ollama**, while keeping Claude Code / backtalk compatible. Preserve upstream components and update paths.

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
│  (backtalk remains supported for Claude-first installs)  │
└──────────────────────────▲──────────────────────────────┘
                           │ Assistant interface
┌──────────────────────────┴──────────────────────────────┐
│  jarvis/  (this repo)                                    │
│  ├─ providers/   openai | ollama | claude-bridge         │
│  ├─ security/    permissions, schemas, secrets, audit    │
│  ├─ tools/       search, computer, memory, git           │
│  ├─ usage/       tokens, budgets, pricing config         │
│  └─ memory/      vault summaries + exclusions            │
└─────────────────────────────────────────────────────────┘
                           │
              agent home (AGENTS.md / CLAUDE.md + vault)
```

## Design rules

1. **Extension, not rewrite** — upstream repos still clone/update as siblings; Jarvis lives in this toolbox.
2. **Common assistant interface** — chat, voice, and dashboard call `Assistant.chat_stream()` / tool loop; providers are swappable.
3. **Ask Before Acting** — default; high-risk never blanket-approved.
4. **Same signal bus** — Jarvis writes the same `.voice_*` files backtalk uses so existing faces keep working.
5. **Secrets** — `.env` / OS env only; `.env.example` placeholders; never committed.
6. **AGPL attribution** — Jared Rhodenizer copyright retained; Jarvis additions attributed in package headers.

## Config

- `jarvis.json` (gitignored user copy) from `jarvis.json.example`
- `.env` for `OPENAI_API_KEY` (and optional `ELEVENLABS_API_KEY`)
- Provider/model/voice/budget settings editable without reinstall

## Launch

- `start.sh` / `start.bat` gain optional `jarvis` mode: dashboard + OpenAI assistant loop
- Existing `voice` / `hands` modes unchanged for Claude/backtalk stacks

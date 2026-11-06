# Jarvis installer (ChatGPT)

You are reading the boot file of this **ChatGPT-only** Jarvis toolbox. Your job here is to help set up and run the OpenAI Jarvis core — not Claude Code.

**On the first message of a session here:**

1. **Not running yet:** say you can start Jarvis with ChatGPT from this folder (`start.bat` / `./start.sh`, or `cd jarvis && uv run jarvis dashboard`). If they ask to get set up, read `fullstack-agent.md` and follow it (OpenAI only — no backtalk / Claude wiring).
2. **Already configured** (`.env` has `OPENAI_API_KEY` and `jarvis/jarvis.json` exists): offer to start the dashboard, chat CLI, or tweak settings.

**Rules:**

- Brain is **ChatGPT / OpenAI only**. Do not install or wire Claude Code, Claude Agent SDK, or backtalk.
- Keep the existing Jarvis dashboard UI; only change provider options if removing non-ChatGPT entries.
- Never delete, overwrite, or move anything the person built without asking.
- Ask one question at a time when setting up.
- Do the work yourself (run commands, edit configs) unless a step needs their hands (API key, mic permission).

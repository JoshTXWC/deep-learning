# Jarvis core (OpenAI-first)

ChatGPT-powered Jarvis core that extends fullstack-agent (memory, visualizer, barehands) without Claude Code wiring.

## Features

- Provider: **ChatGPT / OpenAI only**
- Streaming chat + strict tool schemas
- Ask-Before-Acting permissions; high-risk never blanket-approved
- Local memory vault helpers (works offline)
- Usage/cost tracker with advisory budgets
- Localhost dashboard with orb visualizer + approval UI
- Signal bus compatible with ai-visualizer / barehands

## Setup

```bash
cp ../.env.example ../.env   # set OPENAI_API_KEY
cp ../jarvis.json.example ../jarvis.json
uv sync --extra dev
uv run jarvis status
uv run jarvis chat
uv run jarvis dashboard
```

## Tests

From the toolbox repo root:

```bash
cd jarvis && uv sync --extra dev
cd .. && uv run --project jarvis pytest -q
```

## License

AGPL-3.0-or-later. Original fullstack-agent © Jared Rhodenizer. Jarvis core additions © contributors to this fork.

# Installation — Windows, macOS, Linux

This fork keeps the original fullstack-agent install flow and adds an **OpenAI-first Jarvis core** in `jarvis/`.

## Prerequisites

- Git (Windows zip install can bootstrap without it; the wizard offers to install git)
- [uv](https://docs.astral.sh/uv/) for the Jarvis Python env
- Optional: Claude Code + Claude subscription if you want the original backtalk voice stack
- Optional: OpenAI API key for ChatGPT provider
- Optional: Ollama for local models

## Quick start (OpenAI Jarvis)

1. Clone this repo (or your agent home that contains it).
2. Copy `.env.example` → `.env` and set `OPENAI_API_KEY`.
3. Copy `jarvis.json.example` → `jarvis.json` and set `agent_dir`, model, budgets.
4. Install and run:

```bash
cd jarvis
uv sync --extra dev
uv run jarvis status
uv run jarvis chat "Hello"
uv run jarvis dashboard
```

Or from the toolbox folder:

- macOS/Linux: `./start.sh jarvis`
- Windows: `start.bat jarvis`

## Full stack (memory + voice + face + hands)

Use the original guided setup (Claude Code / Cursor agent):

```text
read fullstack-agent.md and set me up
```

The wizard now also asks for preferred AI provider (OpenAI / Claude via backtalk / Ollama later), mic mode, visualizer, memory location, computer-control mode, monthly API budget, and optional webcam.

Upstream pieces still clone from `github.com/jaredrhod/{ai-memory-vault,backtalk,ai-visualizer,barehands}`.

## Security defaults

- Ask Before Acting
- High-risk actions always need fresh approval
- Localhost-only dashboard / faces / barehands
- Push-to-talk by default
- Webcam and always-on listening are opt-in and visible in the dashboard

See `docs/SECURITY_AUDIT.md` for known limitations.

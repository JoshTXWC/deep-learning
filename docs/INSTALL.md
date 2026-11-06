# Installation — Windows, macOS, Linux

This fork keeps the original fullstack-agent install flow and adds an **OpenAI-first Jarvis core** in `jarvis/`.

## Prerequisites

- Git (Windows zip install can bootstrap without it; the wizard offers to install git)
- [uv](https://docs.astral.sh/uv/) for the Jarvis Python env
- OpenAI API key for ChatGPT (`OPENAI_API_KEY` in `.env`)

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

The wizard configures ChatGPT model, mic mode, visualizer, memory location, computer-control mode, monthly API budget, and optional webcam. Brain is OpenAI only (no Claude wiring).

Optional face/hands still clone from `github.com/jaredrhod/{ai-visualizer,barehands}`; memory from `ai-memory-vault` if wanted.

## Security defaults

- Ask Before Acting
- High-risk actions always need fresh approval
- Localhost-only dashboard / faces / barehands
- Push-to-talk by default
- Webcam and always-on listening are opt-in and visible in the dashboard

See `docs/SECURITY_AUDIT.md` for known limitations.

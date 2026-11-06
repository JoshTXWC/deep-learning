# Security Audit — fullstack-agent / Jarvis upgrade

**Scope:** This installer repo (`JoshTXWC/deep-learning`, fork of `jaredrhod/fullstack-agent`) plus reviewed upstream sources for `backtalk`, `ai-visualizer`, `ai-memory-vault`, and `barehands` (fetched from GitHub `main` at audit time).  
**Method:** Static review of scripts, configs, and published source. No untrusted installers were executed; no system settings were changed.

## Architecture snapshot

| Piece | Role | AI dependency |
| --- | --- | --- |
| This repo | Setup wizard + launchers + (new) Jarvis core | Was Claude Code only |
| `ai-memory-vault` | Markdown memory + agent identity (`CLAUDE.md`) | Consumed by the AI session |
| `backtalk` | Voice I/O; brain = Claude Agent SDK | Hard-wired to Claude Code |
| `ai-visualizer` | Localhost face gallery; reads signal bus | None |
| `barehands` | Localhost webcam hand board | None (camera stays in browser) |

Integration surface between voice and face is filesystem signal files (`.voice_state`, `.voice_waveform`, …), not a network RPC API.

---

## Confirmed findings

### C1 — Hard dependency on Claude Code / Claude Agent SDK
`backtalk/brain.py` imports `claude_agent_sdk` and runs a persistent `ClaudeSDKClient` with tool permissions. ChatGPT cannot replace Claude without a new provider adapter (this upgrade adds one in `jarvis/`).

### C2 — Optional auto-approve of tool use
`permission_mode: "bypassPermissions"` disables spoken approval. Documented and intentional, but high risk if enabled casually. Jarvis core defaults to **Ask Before Acting** and refuses blanket override of high-risk actions.

### C3 — Global keyboard listener (push-to-talk)
`backtalk/ptt.py` uses `pynput` for system-wide key events. Only the configured talk key is acted on; nothing is logged. Still requires macOS Input Monitoring trust. Residual risk: any global key hook elevates process privilege surface.

### C4 — Hands-free mic can capture ambient audio
`mic_mode: "open"` keeps listening with VAD. Local STT by default (good), but ambient speech / media can trigger the agent. Not silently enabled; wizard asks.

### C5 — Update path trusts unsigned `origin/main`
`update.sh` (and zip→git conversion) runs `git fetch` + fast-forward / `reset --hard origin/main` from `github.com/jaredrhod/*`. Compromise of upstream or DNS/MITM without TLS pinning would ship code automatically. No checksum or signature gate.

### C6 — Installer can install system packages
Wizard may run `winget`, Homebrew, `apt`/`dnf`/`pacman`, and `curl … \| sh` for `uv` (backtalk `install.sh`). These require user confirmation in the wizard text, but still execute privileged package managers.

### C7 — Marketing add-on prompt during setup
Phase 6 of `fullstack-agent.md` offers installing `ai-marketing-skills`. Optional, but expands trust boundary mid-setup.

---

## Potential risks (not confirmed exploits)

| ID | Risk | Notes |
| --- | --- | --- |
| P1 | Secret leakage via prompts/logs/memory | ElevenLabs key intended for OS keychain; env var fallback is plaintext. Agent memory can store user-pasted secrets if not redacted. |
| P2 | Prompt injection via vault / web / docs | Retrieved notes or search results could instruct the model to escalate tools. Needs isolation + permission gate (Jarvis implements). |
| P3 | Model-generated command execution | Claude Code / future tools can run shell commands after approval (or auto-approve). Strict schemas + allowlists reduce blast radius. |
| P4 | Zip bootstrap integrity | Windows one-liner downloads GitHub zip over HTTPS without hash verification. |
| P5 | Shared-screen skill description leakage | backtalk documents that skill descriptions enter the system prompt; `visible_skills` mitigates. |
| P6 | Localhost services | Visualizer (8790) and barehands bind `127.0.0.1` — good default. Misconfiguration to `0.0.0.0` would expose them on LAN. |
| P7 | Downstream forks changing remotes | This fork’s `update.sh` still points at `jaredrhod/*`. Custom Jarvis code in this repo is not overwritten by component updates, but wizard/docs can drift. |

---

## Not yet verifiable (components not installed locally)

- Full `ai-memory-vault` migration / Obsidian install paths
- Runtime behavior of Claude Agent SDK tool sandbox on Windows
- ElevenLabs keychain vs env on Windows Credential Manager (planned upstream)
- MediaPipe / TensorFlow WASM supply chain inside barehands browser assets
- Whether any face HTML phones home (static review of gallery pages not fully expanded)

---

## Positive controls already present upstream

- Non-destructive adoption rules (never delete user builds)
- Config files untracked / restored across updates
- Visualizer & barehands bind localhost only
- Default push-to-talk (mic closed unless key held)
- Default ask-before-acting in backtalk
- Signal-bus integration avoids opening extra network ports between pieces
- Windows `update.bat` deliberately emptied after AV false positives on self-copy pattern

---

## Jarvis upgrade security targets

1. Multi-provider brain with secrets only from env / OS secret store — never committed.
2. Tiered permissions: read-only / approval-required / high-risk (fresh, action-specific approval; no blanket high-risk auto-approve).
3. Strict tool-argument schemas; command allowlists; audit log; Stop All Actions.
4. Secret redaction before memory / logs / prompts.
5. Prompt-injection quarantine for retrieved content.
6. Localhost-only dashboard; no public exposure by default.
7. Local budgets + documented OpenAI project spend limits (local budgets do not stop API billing alone).

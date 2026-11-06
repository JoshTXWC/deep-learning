# Known security limitations

1. **Local budgets are advisory.** They stop new Jarvis requests locally but do not cancel OpenAI billing. Set project spend limits in the OpenAI dashboard.
2. **Upstream updates trust GitHub HTTPS remotes** without artifact signing (`update.sh`).
3. **Global push-to-talk key hook** (backtalk) can see key-down/up events for the configured key; review `backtalk/ptt.py` if that trust boundary matters to you.
4. **Model tool calls are only as safe as the permission gate.** If you set `permission_mode` to bypass, approval-required tools may run without prompts; high-risk tools still require fresh approval in Jarvis.
5. **Web search results are untrusted.** They are quarantined, but a determined injection may still confuse the model — permissions still gate side effects.
6. **This audit did not execute package installers or fuzz the Claude Agent SDK sandbox.**
7. **Downloaded third-party modules remain untrusted until you review them.**

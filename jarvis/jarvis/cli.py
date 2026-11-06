# SPDX-License-Identifier: AGPL-3.0-or-later
"""Jarvis CLI — chat, dashboard, status."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis", description="Secure multi-provider Jarvis assistant")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Print assistant status JSON")
    p_chat = sub.add_parser("chat", help="Interactive text chat (OpenAI/Ollama)")
    p_chat.add_argument("message", nargs="?", help="Single-shot message")
    sub.add_parser("dashboard", help="Open localhost Jarvis dashboard")
    p_sum = sub.add_parser("remember", help="Save a conversation summary to local memory")
    p_sum.add_argument("title")
    p_sum.add_argument("summary")

    args = parser.parse_args(argv)

    # Lazy imports so --help works without deps resolved oddly
    from jarvis.assistant import Assistant

    if args.cmd == "status":
        print(json.dumps(Assistant().status(), indent=2))
        return 0

    if args.cmd == "remember":
        a = Assistant()
        path = a.memory.save_conversation_summary(args.title, args.summary)
        print(f"Saved memory: {path}")
        return 0

    if args.cmd == "dashboard":
        from jarvis.dashboard import run_dashboard

        run_dashboard(Assistant())
        return 0

    if args.cmd == "chat":
        assistant = Assistant()
        print(assistant.speech.disclosure(), flush=True)
        print(f"Provider={assistant.cfg.get('provider')} model={assistant.cfg.get('model')}", flush=True)
        print("Type a message (Ctrl-C to quit). Prefix with /stop to halt actions.\n", flush=True)

        async def once(msg: str) -> None:
            if msg.strip() == "/stop":
                assistant.stop_all_actions()
                print("All actions stopped.", flush=True)
                return
            async for delta in assistant.chat_stream(msg):
                sys.stdout.write(delta)
                sys.stdout.flush()
            print("\n", flush=True)

        if args.message:
            asyncio.run(once(args.message))
            return 0

        try:
            while True:
                msg = input("you> ").strip()
                if not msg:
                    continue
                asyncio.run(once(msg))
        except (KeyboardInterrupt, EOFError):
            print("\nbye.", flush=True)
            return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

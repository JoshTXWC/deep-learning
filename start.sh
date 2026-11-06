#!/bin/bash
# fullstack-agent / Jarvis: ChatGPT-powered assistant launcher.
# Copyright (C) 2026 Jared Rhodenizer
# ChatGPT-only fork adaptations © contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# Starts ChatGPT Jarvis (+ optional face / hands).
#   ./start.sh          Jarvis dashboard (+ face if installed)
#   ./start.sh face     face visualizer only
#   ./start.sh hands    barehands board only

HERE="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="$(dirname "$HERE")"
MODE="${1:-jarvis}"
PIDS=()

cleanup() {
  trap - EXIT INT TERM
  for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done
  echo
  echo "agent stopped."
}
trap cleanup EXIT INT TERM

echo "jarvis: starting from $HOME_DIR (ChatGPT)"

if [ -d "$HOME_DIR/ai-visualizer" ] && [ "$MODE" != "hands" ]; then
  (cd "$HOME_DIR/ai-visualizer" && exec python3 server.py) &
  PIDS+=($!)
  echo "  face:  starting"
fi

if [ -d "$HOME_DIR/barehands" ] && [ "$MODE" = "hands" ]; then
  (cd "$HOME_DIR/barehands" && exec python3 server.py) &
  PIDS+=($!)
  echo "  hands: starting (open the printed URL in Chrome)"
fi

if [ "$MODE" = "face" ] || [ "$MODE" = "hands" ]; then
  wait
  exit 0
fi

if [ -d "$HERE/jarvis" ]; then
  echo "  jarvis: ChatGPT dashboard (http://127.0.0.1:8795/)"
  cd "$HERE/jarvis" && uv run jarvis dashboard
else
  echo "  jarvis core missing; expected toolbox/jarvis"
  wait
fi

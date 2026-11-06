@echo off
rem fullstack-agent / Jarvis: ChatGPT-powered assistant launcher.
rem Copyright (C) 2026 Jared Rhodenizer
rem ChatGPT-only fork adaptations © contributors
rem
rem SPDX-License-Identifier: AGPL-3.0-or-later
rem
rem   start.bat          Jarvis dashboard (+ face if installed)
rem   start.bat face     face visualizer only
rem   start.bat hands    barehands board only

set "TOOLBOX=%~dp0"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=jarvis"
cd /d "%~dp0.."

if exist "ai-visualizer\" if /I not "%MODE%"=="hands" (
  echo   face:  starting
  start "agent face" cmd /c "cd ai-visualizer && run.bat"
)

if exist "barehands\" if /I "%MODE%"=="hands" (
  echo   hands: starting
  start "agent hands" cmd /c "cd barehands && run.bat"
)

if /I "%MODE%"=="face" goto :eof
if /I "%MODE%"=="hands" goto :eof

echo   jarvis: ChatGPT dashboard (http://127.0.0.1:8795/)
cd /d "%TOOLBOX%jarvis"
uv run --native-tls jarvis dashboard

@echo off
title Makinity UGC Director AI Dashboard
cd /d "%~dp0"

echo ========================================================
echo   Starting Makinity UGC Director Dashboard...
echo ========================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" launch_ui.py
) else (
    python launch_ui.py
)

pause


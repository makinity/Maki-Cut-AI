@echo off
title Makinity Cut - CapCut AI Desktop
cd /d "%~dp0"
call .\.venv\Scripts\activate.bat
python main.py
pause

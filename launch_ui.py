#!/usr/bin/env python3
"""
Makinity UGC Director — Web UI Launcher
Launches the FastAPI backend and opens the dashboard in your default browser.
"""

import sys
import os
import time
import webbrowser
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

PORT = 8000
HOST = "127.0.0.1"
URL = f"http://{HOST}:{PORT}"

def main():
    print("=" * 65)
    print("  🎬 MAKINITY UGC DIRECTOR — AUTONOMOUS AI VIDEO EDITOR")
    print("=" * 65)
    print(f">> Starting Web Dashboard server at {URL}...")
    print(f">> Python Interpreter: {PYTHON_EXE}")

    cmd = [
        str(PYTHON_EXE),
        "-m", "uvicorn",
        "ui.server:app",
        "--host", HOST,
        "--port", str(PORT),
        "--log-level", "info"
    ]

    # Open web browser after slight delay
    def open_browser():
        time.sleep(1.2)
        print(f">> Opening dashboard in your default browser: {URL}")
        try:
            webbrowser.open(URL)
        except Exception as e:
            print(f"Note: Could not open browser automatically: {e}")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    try:
        # Run uvicorn server in foreground
        subprocess.run(cmd, cwd=str(BASE_DIR))
    except KeyboardInterrupt:
        print("\n>> Server stopped by user.")

if __name__ == "__main__":
    main()


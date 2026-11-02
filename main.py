#!/usr/bin/env python3
"""
Makinity Cut - CapCut AI Desktop Main Entrypoint.
Usage:
    .\\.venv\\Scripts\\activate
    python main.py
"""

import sys
import time
import threading
import webbrowser
from pathlib import Path

# Ensure utf-8 on Windows terminal to prevent cp1252 charmap errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def open_browser():
    """Wait 1.5s for Uvicorn to initialize, then launch the browser."""
    time.sleep(1.5)
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception:
        pass

def main():
    import uvicorn

    print("\n" + "=" * 65)
    print("  MAKINITY CUT - CAPCUT AI DESKTOP EDITOR")
    print("=" * 65)
    print("  [>] Status   : Running")
    print("  [>] Web UI   : http://127.0.0.1:8000")
    print("  [>] Workspace: " + str(ROOT_DIR))
    print("  [!] To Stop  : Press CTRL + C")
    print("=" * 65 + "\n")

    # Launch browser automatically in a non-blocking background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run FastAPI server
    uvicorn.run(
        "ui.server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(ROOT_DIR / "ui"), str(ROOT_DIR / "skills")]
    )

if __name__ == "__main__":
    main()

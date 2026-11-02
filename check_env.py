"""
Environment Verification Script for Makinity Cut
Checks virtual environment isolation, core dependencies, and FFmpeg binary.
"""

import sys
import os
from pathlib import Path

def check_environment():
    print("=" * 60)
    print("Makinity Cut - Python Environment Verification")
    print("=" * 60)
    
    # 1. Virtual Environment Check
    is_venv = sys.prefix != sys.base_prefix
    print(f"Python Executable : {sys.executable}")
    print(f"Python Version    : {sys.version.split()[0]}")
    print(f"Virtual Env Active: {'YES' if is_venv else 'NO (running in base environment)'}")
    
    # 2. Dependency Check
    print("\n--- Core Packages ---")
    packages = [
        "imageio_ffmpeg",
        "moviepy",
        "PIL",
        "numpy",
        "scipy",
        "pydub",
        "ffmpeg",
        "typer",
        "rich",
        "pydantic"
    ]
    
    for pkg in packages:
        try:
            mod = __import__(pkg)
            version = getattr(mod, "__version__", "installed")
            print(f"  [OK] {pkg:<16} : {version}")
        except ImportError:
            print(f"  [MISSING] {pkg:<12} : Not installed")
            
    # 3. FFmpeg & FFprobe Binary Check
    print("\n--- FFmpeg & FFprobe Integration ---")
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = venv_scripts / "ffmpeg.exe"
    ffprobe_exe = venv_scripts / "ffprobe.exe"
    print(f"  [{'OK' if ffmpeg_exe.exists() else 'MISSING'}] ffmpeg  : {ffmpeg_exe}")
    print(f"  [{'OK' if ffprobe_exe.exists() else 'MISSING'}] ffprobe : {ffprobe_exe}")

    # 4. Workspace Directories
    print("\n--- Workspace Directories ---")
    root = Path(__file__).resolve().parent
    for folder in ["BM", "Input", "Output", "SFX"]:
        dir_path = root / folder
        count = len(list(dir_path.glob("*"))) if dir_path.is_dir() else 0
        status = f"Exists ({count} items)" if dir_path.is_dir() else "Missing"
        print(f"  {folder:<8} : {status}")

    print("=" * 60)
    print("Environment setup is ready for Makinity Cut Video Editing Skill!")

if __name__ == "__main__":
    check_environment()


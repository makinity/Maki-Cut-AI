# Makinity Cut - AI Video Editing Environment

An isolated, agent-ready Python environment and workspace for automated video editing workflows (cuts, captions, silence trimming, morphing shapes, sound effects, and BGM mixing).

## Workspace Structure

- `.venv/`: Isolated Python virtual environment (Python 3.11 with FFmpeg 7.1 embedded).
- `BM/`: Background Music tracks.
- `Input/`: Source raw video/audio files for processing.
- `Output/`: Rendered final cut videos, clips, and exports.
- `SFX/`: Curated sound effects library (whooshes, risers, UI beeps, impacts, comedic SFX).
- `pyproject.toml`: Environment dependency manifest.
- `check_env.py`: Environment verification utility.

## Environment Activation

### Windows (PowerShell)
```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)
```cmd
.\.venv\Scripts\activate.bat
```

### Direct Agent Execution
AI agents (e.g. Codex, Claude Code, Hermes, Kliro, Gemini CLI) can run scripts directly using:
```powershell
.\.venv\Scripts\python.exe <script.py>
```
and invoke FFmpeg directly via:
```powershell
.\.venv\Scripts\ffmpeg.exe
```

## Installed Core Capabilities
- **FFmpeg 7.1** embedded in `.venv\Scripts` for seamless transcoding, filtering, and rendering without system dependency prerequisites.
- **MoviePy & ffmpeg-python**: High-level compositing, cuts, shape overlays, transformations, and audio track mixing.
- **Pydub & Scipy**: Audio waveform analysis, silence/dead-air detection, and volume normalization.
- **Pillow & NumPy**: Frame generation, dynamic morphing shape generation, and pixel manipulation.
- **Typer & Rich**: Structured CLI command-line tools for agents.
- **Pydantic**: Robust schema validation for editing instructions and timelines.


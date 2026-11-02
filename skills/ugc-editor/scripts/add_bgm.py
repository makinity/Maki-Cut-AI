#!/usr/bin/env python3
"""
Background Music (BGM) Engine with Intelligent Voice-Ducking for UGC Videos.
Loops music from BM/, applies professional broadcast sidechain ducking so the voice stays crisp,
and smoothly swells background music during visual transitions and pauses.
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from typing import Optional, Tuple, List
import typer
from rich.console import Console

app = typer.Typer(help="Mix background music with automatic voice-ducking.")
console = Console()

BM_DIR = Path("BM")
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_duration(video_path: Path, ffprobe_exe: str) -> float:
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(res.stdout.strip())

def find_bgm_track(query: Optional[str] = None) -> Optional[Path]:
    if not BM_DIR.exists():
        return None
    tracks = [f for f in BM_DIR.iterdir() if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS]
    if not tracks:
        return None
    if query:
        q = query.lower()
        for t in tracks:
            if q in t.stem.lower():
                return t
    return tracks[0]

@app.command(name="list")
def list_bgm():
    """List all available background music tracks in BM/."""
    if not BM_DIR.exists() or not list(BM_DIR.glob("*.*")):
        console.print("[yellow]No music tracks found in BM/ folder. Place your .mp3 or .wav files there![/yellow]")
        return
    console.print("[bold green]Available BGM Tracks in BM/:[/bold green]")
    for idx, f in enumerate(BM_DIR.iterdir(), 1):
        if f.suffix.lower() in AUDIO_EXTENSIONS:
            console.print(f"  {idx}. [cyan]{f.name}[/cyan]")

@app.command(name="mix")
def mix_bgm(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    music_file: Optional[Path] = typer.Option(None, "--music", "-m", help="Path to specific music file or query from BM/"),
    volume: float = typer.Option(0.18, "--volume", "-v", help="Base background music volume (0.05 to 0.5, default 0.18)"),
    ducking_ratio: float = typer.Option(5.0, "--ducking", "-d", help="Ducking strength: how much music lowers during speech (2.0 to 10.0, default 5.0)"),
    fade_out: float = typer.Option(1.5, "--fade-out", help="Fade out duration in seconds at end of video")
):
    """
    Mixes BGM with sidechain compression so music ducks under speech automatically.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input video '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_with_bgm.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    resolved_music = None
    if music_file and music_file.exists():
        resolved_music = music_file
    elif music_file:
        resolved_music = find_bgm_track(str(music_file))
    else:
        resolved_music = find_bgm_track()
        
    if not resolved_music:
        console.print("[yellow]Notice: No music track found in BM/ folder. Copying video without BGM.[/yellow]")
        cmd = [ffmpeg_exe, "-y", "-i", str(input_file), "-c", "copy", str(output_file)]
        subprocess.run(cmd, check=True)
        return

    console.print(f"[bold green]Selected BGM Track:[/bold green] [cyan]{resolved_music.name}[/cyan]")
    video_dur = get_video_duration(input_file, ffprobe_exe)
    fade_start = max(0.0, video_dur - fade_out)
    
    console.print(f"Video Duration: [bold yellow]{video_dur:.2f}s[/bold yellow] · Applying dynamic voice-ducking...")

    filter_complex = (
        f"[1:a]volume={volume:.3f},atrim=0:{video_dur:.3f},afade=t=out:st={fade_start:.3f}:d={fade_out:.3f}[bgm_raw];"
        f"[bgm_raw][0:a]sidechaincompress=threshold=0.06:ratio={ducking_ratio:.1f}:attack=40:release=350[ducked_bgm];"
        f"[0:a][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=0[outa]"
    )

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
        "-stream_loop", "-1",
        "-i", str(resolved_music),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_file)
    ]

    subprocess.run(cmd, check=True)
    console.print(f"\n[bold green]Success![/bold green] Video with ducked BGM saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()


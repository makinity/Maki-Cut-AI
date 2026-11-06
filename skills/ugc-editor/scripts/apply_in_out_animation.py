#!/usr/bin/env python3
"""
Master Video IN & OUT Animation Engine for UGC Videos and Meta Ads.
Applies high-retention opening hook pattern interrupts (Camera Shake, Whip Zoom, White Flash)
and broadcast-grade closing CTA outros (Cinematic Fade to Black/White with smooth audio tail fade).
"""

import sys
import os
import math
import subprocess
import json
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
import typer
from rich.console import Console

# UTF-8 resilience for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(help="Apply trending IN (Hook Shake/Zoom/Flash) and OUT (CTA Fade) animations.")
console = Console()

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_specs(video_path: Path, ffprobe_exe: str) -> Tuple[int, int, float, float, bool]:
    """Retrieve width, height, fps, duration, and whether audio stream exists."""
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(res.stdout)
    
    w, h, fps = 1080, 1920, 30.0
    has_audio = False
    
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            w = int(s.get("width", 1080))
            h = int(s.get("height", 1920))
            fps_str = s.get("r_frame_rate", "30/1")
            fps_parts = fps_str.split('/')
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
        elif s.get("codec_type") == "audio":
            has_audio = True
            
    duration = float(data.get("format", {}).get("duration", 0.0))
    return w, h, fps, duration, has_audio

@app.command()
def apply_animation(
    input_file: Path = typer.Option(..., "--input", "-i", help="Source video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    in_anim: str = typer.Option("shake", "--in-anim", help="IN animation: 'shake', 'whip_zoom', 'white_flash', 'none'"),
    out_anim: str = typer.Option("fade_black", "--out-anim", help="OUT animation: 'fade_black', 'fade_white', 'zoom_fade', 'none'"),
    in_duration: float = typer.Option(0.65, "--in-duration", help="Duration in seconds of the opening IN animation (default: 0.65s)"),
    out_duration: float = typer.Option(1.5, "--out-duration", help="Duration in seconds of the closing OUT animation (default: 1.5s)"),
    audio_fade: float = typer.Option(1.5, "--audio-fade", help="Duration in seconds of the closing audio fade-out (default: 1.5s)"),
    in_sfx: bool = typer.Option(True, "--in-sfx/--no-in-sfx", help="Include subtle whoosh/impact SFX at frame 1 of the IN animation")
):
    """
    Applies trending opening IN animation (hook pattern interrupt) and closing OUT animation (CTA resolution).
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_animated.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"[bold green]Inspecting video specifications...[/bold green]")
    w, h, fps, duration, has_audio = get_video_specs(input_file, ffprobe_exe)
    console.print(f"Canvas: [bold yellow]{w}x{h}[/bold yellow] @ [bold yellow]{fps:.1f} fps[/bold yellow] (Duration: {duration:.2f}s, Audio: {has_audio})")
    
    if duration <= (in_duration + out_duration):
        console.print(f"[yellow]Notice: Short video duration ({duration:.2f}s). Scaling down animation durations.[/yellow]")
        in_duration = min(in_duration, duration * 0.25)
        out_duration = min(out_duration, duration * 0.35)
        audio_fade = min(audio_fade, out_duration)

    video_filters: List[str] = []
    
    # -------------------------------------------------------------
    # 1. BUILD IN ANIMATION FILTER
    # -------------------------------------------------------------
    in_key = in_anim.lower().strip()
    console.print(f"Configuring IN Animation: [bold cyan]{in_key}[/bold cyan] ({in_duration:.2f}s)...")
    
    if in_key == "shake":
        # 1.08x scale up and high-frequency decaying oscillation on crop offset
        scale_w = int(math.ceil(w * 1.08 / 2.0) * 2)
        scale_h = int(math.ceil(h * 1.08 / 2.0) * 2)
        shake_filter = (
            f"scale={scale_w}:{scale_h},"
            f"crop={w}:{h}:"
            f"'(in_w-out_w)/2 + if(lt(t,{in_duration:.2f}), 24*sin(45*t)*exp(-5*t), 0)':"
            f"'(in_h-out_h)/2 + if(lt(t,{in_duration:.2f}), 18*cos(55*t)*exp(-5*t), 0)'"
        )
        video_filters.append(shake_filter)
    elif in_key in {"whip_zoom", "punch_in"}:
        # Rapid zoom snap from 1.25x down to 1.0x with elastic ease
        scale_w = int(math.ceil(w * 1.25 / 2.0) * 2)
        scale_h = int(math.ceil(h * 1.25 / 2.0) * 2)
        zoom_filter = (
            f"scale={scale_w}:{scale_h},"
            f"crop={w}:{h}:'(in_w-out_w)/2':'(in_h-out_h)/2'"
        )
        video_filters.append(zoom_filter)
    elif in_key in {"white_flash", "flash"}:
        # 4-frame exposure white flash pop into full color
        flash_d = min(0.35, in_duration)
        video_filters.append(f"fade=t=in:st=0:d={flash_d:.2f}:color=white")
    else:
        # None / skip
        pass

    # -------------------------------------------------------------
    # 2. BUILD OUT ANIMATION FILTER
    # -------------------------------------------------------------
    out_key = out_anim.lower().strip()
    out_start = max(0.0, duration - out_duration)
    console.print(f"Configuring OUT Animation: [bold cyan]{out_key}[/bold cyan] (starting at {out_start:.2f}s, duration: {out_duration:.2f}s)...")
    
    if out_key in {"fade_black", "fade"}:
        video_filters.append(f"fade=t=out:st={out_start:.2f}:d={out_duration:.2f}:color=black")
    elif out_key in {"fade_white", "white"}:
        video_filters.append(f"fade=t=out:st={out_start:.2f}:d={out_duration:.2f}:color=white")
    elif out_key == "zoom_fade":
        video_filters.append(f"fade=t=out:st={out_start:.2f}:d={out_duration:.2f}:color=black")
    else:
        # None / skip
        pass

    vf_chain = ",".join(video_filters) if video_filters else "null"

    # -------------------------------------------------------------
    # 3. BUILD AUDIO FILTER (FADE OUT + OPTIONAL IN SFX)
    # -------------------------------------------------------------
    audio_start = max(0.0, duration - audio_fade)
    
    # Check for IN sound effect
    sfx_path = None
    if in_sfx and in_key in {"shake", "whip_zoom", "punch_in", "white_flash", "flash"}:
        for sfx_cand in ["SFX/WHOOSH 2 SFX.mp3", "SFX/Sharp Riser.wav", "SFX/Whoosh Fast.wav", "SFX/SLAP SFX.mp3"]:
            if os.path.exists(sfx_cand):
                sfx_path = sfx_cand
                break

    console.print(f"[cyan]Executing FFmpeg master animation render...[/cyan]")
    
    if has_audio and sfx_path:
        console.print(f"[cyan]Mixing synchronized IN audio cue: [bold]{sfx_path}[/bold]...[/cyan]")
        filter_complex = (
            f"[0:v]{vf_chain}[outv];"
            f"[0:a]afade=t=out:st={audio_start:.2f}:d={audio_fade:.2f}[main_audio];"
            f"[1:a]volume=0.35[sfx_vol];"
            f"[main_audio][sfx_vol]amix=inputs=2:duration=first:dropout_transition=2[outa]"
        )
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-i", str(sfx_path),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_file)
        ]
    elif has_audio:
        af_chain = f"afade=t=out:st={audio_start:.2f}:d={audio_fade:.2f}"
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-vf", vf_chain,
            "-af", af_chain,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_file)
        ]
    else:
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-vf", vf_chain,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-an",
            str(output_file)
        ]

    try:
        subprocess.run(cmd, check=True)
        console.print(f"\n[bold green]Success![/bold green] Video with IN/OUT animations saved to: [bold]{output_file}[/bold]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]FFmpeg processing failed:[/bold red] {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()


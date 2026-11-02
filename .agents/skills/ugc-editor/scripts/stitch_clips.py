#!/usr/bin/env python3
"""
Multi-Clip Assembler & Natural Sequence Stitcher for UGC Videos.
Detects multiple clips in Input/, sorts them naturally by name (e.g. clip 1, clip 2, clip 10),
normalizes resolutions/framerates/audio, and stitches them into a seamless master video.
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Assemble and stitch multiple video clips from Input/ in natural order.")
console = Console()

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def natural_sort_key(s: str) -> List[Any]:
    """Sort strings with embedded numbers naturally (e.g. clip 1, clip 2, clip 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def get_clip_metadata(clip_path: Path, ffprobe_exe: str) -> Dict[str, Any]:
    """Probe video and audio stream metadata."""
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
        "-of", "json",
        str(clip_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(res.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        streams = data.get("streams", [])
        
        has_video = False
        has_audio = False
        width, height = 1080, 1920
        fps = 30.0
        
        for s in streams:
            if s.get("codec_type") == "video" and not has_video:
                has_video = True
                width = int(s.get("width", 1080))
                height = int(s.get("height", 1920))
                fps_parts = s.get("r_frame_rate", "30/1").split('/')
                fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) > 0 else 30.0
            elif s.get("codec_type") == "audio":
                has_audio = True
                
        return {
            "path": clip_path,
            "filename": clip_path.name,
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
            "has_audio": has_audio
        }
    except Exception as e:
        console.print(f"[yellow]Warning: Could not probe {clip_path.name}: {e}[/yellow]")
        return {
            "path": clip_path,
            "filename": clip_path.name,
            "duration": 0.0,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "has_audio": True
        }

def find_input_clips(input_dir: Path, pattern: Optional[str] = None) -> List[Path]:
    """Find and return video files in input_dir sorted naturally."""
    if not input_dir.exists():
        return []
        
    candidates = []
    if pattern:
        candidates = list(input_dir.glob(pattern))
    else:
        for f in input_dir.iterdir():
            if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
                candidates.append(f)
                
    return sorted(candidates, key=lambda p: natural_sort_key(p.name))

@app.command(name="list")
def list_clips(
    input_dir: Path = typer.Option(Path("Input"), "--input-dir", "-i", help="Directory containing raw clips")
):
    """Scan and list all video clips in natural playback sequence."""
    _, ffprobe_exe = get_ffmpeg_paths()
    clips = find_input_clips(input_dir)
    
    if not clips:
        console.print(f"[bold yellow]No video clips found in '{input_dir}' directory.[/bold yellow]")
        return
        
    table = Table(title=f"Detected Video Clips in Natural Order ({len(clips)} files)")
    table.add_column("Seq", justify="right", style="cyan", no_wrap=True)
    table.add_column("Filename", style="bold white")
    table.add_column("Resolution", style="green")
    table.add_column("FPS", style="yellow")
    table.add_column("Duration", justify="right", style="magenta")
    
    total_dur = 0.0
    for idx, clip_path in enumerate(clips, 1):
        meta = get_clip_metadata(clip_path, ffprobe_exe)
        dur = meta["duration"]
        total_dur += dur
        table.add_row(
            str(idx),
            meta["filename"],
            f"{meta['width']}x{meta['height']}",
            f"{meta['fps']:.1f}",
            f"{dur:.2f}s"
        )
        
    console.print(table)
    console.print(f"Total Combined Timeline Duration: [bold green]{total_dur:.2f}s[/bold green]")

@app.command(name="stitch")
def stitch_clips(
    input_dir: Path = typer.Option(Path("Input"), "--input-dir", "-i", help="Directory containing raw clips"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Filename glob pattern (e.g. 'clip*.mp4')"),
    order: Optional[str] = typer.Option(None, "--order", help="Custom comma-separated filename order (e.g. 'hook.mp4,body.mp4,cta.mp4')"),
    target_res: str = typer.Option("1080x1920", "--res", "-r", help="Target resolution 'WIDTHxHEIGHT' or 'auto' (default: 1080x1920 vertical)"),
    fps: int = typer.Option(30, "--fps", help="Unified frame rate (default: 30 fps)"),
    fit_mode: str = typer.Option("crop", "--fit", help="Fit mode: 'crop' (fill full frame without black bars) or 'pad' (letterbox)")
):
    """
    Stitches multiple clips into one unified sequence based on natural filename order.
    Normalizes resolutions, frame rates, and audio to eliminate stutter and sync drift.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    # 1. Gather clips
    if order:
        filenames = [x.strip() for x in order.split(",") if x.strip()]
        clips = [input_dir / fn for fn in filenames if (input_dir / fn).exists()]
    else:
        clips = find_input_clips(input_dir, pattern=pattern)
        
    if not clips:
        console.print(f"[bold red]No video clips found to stitch in '{input_dir}'![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / "assembled_sequence.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"[bold green]Assembling {len(clips)} clips in sequence:[/bold green]")
    for i, c in enumerate(clips, 1):
        console.print(f"  {i}. [cyan]{c.name}[/cyan]")
        
    # 2. Determine target resolution
    if target_res.lower() == "auto":
        first_meta = get_clip_metadata(clips[0], ffprobe_exe)
        target_w, target_h = first_meta["width"], first_meta["height"]
    else:
        parts = target_res.lower().split("x")
        target_w, target_h = int(parts[0]), int(parts[1])
        
    console.print(f"Target Master Format: [bold yellow]{target_w}x{target_h}[/bold yellow] @ [bold yellow]{fps} fps[/bold yellow] (Fit: {fit_mode})")
    
    # 3. Build FFmpeg command with complex normalization filter
    cmd = [ffmpeg_exe, "-y"]
    
    for c in clips:
        cmd.extend(["-i", str(c)])
        
    filter_parts = []
    concat_inputs = []
    
    for idx, c in enumerate(clips):
        meta = get_clip_metadata(c, ffprobe_exe)
        
        # Video normalization filter
        if fit_mode == "crop":
            # Scale to fill then center-crop
            v_filter = (
                f"[{idx}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h},setsar=1,fps={fps}[v{idx}]"
            )
        else: # pad
            # Scale to fit then pad
            v_filter = (
                f"[{idx}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps}[v{idx}]"
            )
        filter_parts.append(v_filter)
        
        # Audio normalization filter
        if meta["has_audio"]:
            a_filter = f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,aresample=48000[a{idx}]"
        else:
            dur = max(0.1, meta["duration"])
            a_filter = f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={dur:.3f}[a{idx}]"
        filter_parts.append(a_filter)
        
        concat_inputs.append(f"[v{idx}][a{idx}]")
        
    concat_filter = f"{''.join(concat_inputs)}concat=n={len(clips)}:v=1:a=1[outv][outa]"
    filter_parts.append(concat_filter)
    
    filter_complex = ";".join(filter_parts)
    
    cmd.extend([
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
    ])
    
    console.print("[cyan]Stitching and normalizing video sequence via FFmpeg...[/cyan]")
    subprocess.run(cmd, check=True)
    
    total_specs = get_clip_metadata(output_file, ffprobe_exe)
    console.print(f"\n[bold green]Success![/bold green] Stitched master saved to: [bold]{output_file}[/bold]")
    console.print(f"Total Duration: [bold yellow]{total_specs['duration']:.2f}s[/bold yellow] ({len(clips)} clips combined)")

if __name__ == "__main__":
    app()


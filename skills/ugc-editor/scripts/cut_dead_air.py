#!/usr/bin/env python3
"""
Dead Air / Silence Trimming Script for UGC Videos.
Detects silence in video/audio and cuts out dead space to produce tight, fast-paced UGC cuts.
"""

import sys
import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple
import typer
from rich.console import Console

app = typer.Typer(help="Cut dead air and silences from raw video footage.")
console = Console()

def get_ffmpeg_paths() -> Tuple[str, str]:
    """Locate ffmpeg and ffprobe executables."""
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_duration(video_path: Path, ffprobe_exe: str) -> float:
    """Get the total duration of the video in seconds."""
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(res.stdout.strip())

def detect_silences(
    video_path: Path, 
    ffmpeg_exe: str, 
    noise_db: float = -32.0, 
    min_duration: float = 0.4
) -> List[Tuple[float, float]]:
    """
    Run ffmpeg silencedetect to find all (silence_start, silence_end) timestamps.
    """
    cmd = [
        ffmpeg_exe,
        "-i", str(video_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null",
        "-"
    ]
    console.print(f"[cyan]Scanning audio for silences below {noise_db}dB (min {min_duration}s)...[/cyan]")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    silences = []
    start_time = None
    
    # Regex matches
    start_re = re.compile(r"silence_start:\s*([0-9.]+)")
    end_re = re.compile(r"silence_end:\s*([0-9.]+)")
    
    for line in res.stderr.splitlines():
        start_match = start_re.search(line)
        if start_match:
            start_time = float(start_match.group(1))
        
        end_match = end_re.search(line)
        if end_match and start_time is not None:
            end_time = float(end_match.group(1))
            silences.append((start_time, end_time))
            start_time = None
            
    return silences

def invert_silences_to_speech(
    silences: List[Tuple[float, float]], 
    total_duration: float, 
    padding: float = 0.12
) -> List[Tuple[float, float]]:
    """
    Invert silent intervals to speech/active intervals, adding buffer padding
    so words and natural breath endings are never clipped.
    """
    if not silences:
        return [(0.0, total_duration)]
    
    speech_segments = []
    current_time = 0.0
    
    for s_start, s_end in silences:
        seg_end = min(total_duration, s_start + padding)
        if seg_end > current_time:
            speech_segments.append((current_time, seg_end))
        current_time = max(0.0, s_end - padding)
        
    if current_time < total_duration:
        speech_segments.append((current_time, total_duration))
        
    # Merge overlapping or tiny gaps (< 0.05s)
    merged = []
    for seg in speech_segments:
        if not merged:
            merged.append(seg)
        else:
            prev_start, prev_end = merged[-1]
            if seg[0] <= prev_end + 0.05:
                merged[-1] = (prev_start, max(prev_end, seg[1]))
            else:
                merged.append(seg)
                
    # Filter out empty or negative duration segments
    valid_segments = [s for s in merged if (s[1] - s[0]) > 0.15]
    return valid_segments

@app.command()
def trim_dead_air(
    input_file: Path = typer.Option(..., "--input", "-i", help="Path to raw source video in Input/"),
    output_file: Path = typer.Option(None, "--output", "-o", help="Path to save trimmed video in Output/"),
    noise_db: float = typer.Option(-32.0, "--noise-db", "-n", help="Silence audio threshold in dB (default -32dB)"),
    min_silence: float = typer.Option(0.40, "--min-silence", "-s", help="Minimum silence duration to cut in seconds (default 0.4s)"),
    padding: float = typer.Option(0.12, "--padding", "-p", help="Safety padding around speech in seconds (default 0.12s)")
):
    """
    Automatically cuts out dead air and long pauses from a video.
    Produces tight UGC cuts while keeping audio and video in sync.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    if output_file is None:
        output_dir = Path("Output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{input_file.stem}_trimmed.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"[bold green]Analyzing:[/bold green] {input_file.name}")
    total_dur = get_video_duration(input_file, ffprobe_exe)
    console.print(f"Total video duration: [bold yellow]{total_dur:.2f}s[/bold yellow]")
    
    # 1. Detect silences
    silences = detect_silences(input_file, ffmpeg_exe, noise_db=noise_db, min_duration=min_silence)
    
    if not silences:
        console.print("[yellow]No dead air detected above threshold. Video is already tight![/yellow]")
        # Copy input to output
        cmd = [ffmpeg_exe, "-y", "-i", str(input_file), "-c", "copy", str(output_file)]
        subprocess.run(cmd, check=True)
        console.print(f"[bold green]Saved output directly to:[/bold green] {output_file}")
        return

    # 2. Invert silences to keep segments
    segments = invert_silences_to_speech(silences, total_dur, padding=padding)
    kept_duration = sum(end - start for start, end in segments)
    removed_duration = total_dur - kept_duration
    
    console.print(f"Found [bold red]{len(silences)}[/bold red] pauses / dead air gaps.")
    console.print(f"Kept [bold green]{len(segments)}[/bold green] active speech segments.")
    console.print(f"Trimming out [bold red]{removed_duration:.2f}s[/bold red] of dead air.")
    console.print(f"Projected output duration: [bold green]{kept_duration:.2f}s[/bold green] (Saved {removed_duration/total_dur*100:.1f}%)")
    
    # 3. Build filter_complex for seamless cut and concatenation
    # Format: [0:v]trim=start=S:end=E,setpts=PTS-STARTPTS[v0]; [0:a]atrim=start=S:end=E,asetpts=PTS-STARTPTS[a0]; ...
    filter_parts = []
    concat_inputs = []
    
    for i, (start, end) in enumerate(segments):
        filter_parts.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}]")
        filter_parts.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]")
        concat_inputs.append(f"[v{i}][a{i}]")
        
    filter_complex = ";".join(filter_parts) + f";{''.join(concat_inputs)}concat=n={len(segments)}:v=1:a=1[outv][outa]"
    
    console.print("[cyan]Rendering seamless cuts via FFmpeg...[/cyan]")
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
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
    
    subprocess.run(cmd, check=True)
    
    console.print(f"\n[bold green]Success![/bold green] Trimmed video saved to: [bold]{output_file}[/bold]")
    console.print(f"Finished trimming dead air: [yellow]{total_dur:.2f}s[/yellow] -> [bold green]{kept_duration:.2f}s[/bold green]")

if __name__ == "__main__":
    app()


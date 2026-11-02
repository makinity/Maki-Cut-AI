#!/usr/bin/env python3
"""
Dynamic Transitions & Multi-Clip Stitcher for UGC Videos.
Stitches multiple clips with high-retention transitions (slide, zoom, smooth wipe, iris, flash)
and automatically syncs whoosh SFX to each cut point for high-energy production.
"""

import sys
import os
import re
import json
import math
import subprocess
import random
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Stitch multiple clips with engaging transitions and auto-synced SFX.")
console = Console()

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}

TRANSITION_MAP = {
    "slide_left": "slideleft",
    "slide_right": "slideright",
    "slide_up": "slideup",
    "slide_down": "slidedown",
    "smooth_left": "smoothleft",
    "smooth_right": "smoothright",
    "zoom_in": "zoomin",
    "circle_crop": "circlecrop",
    "fade_black": "fadeblack",
    "fade_white": "fadewhite",
    "pixelize": "pixelize",
    "wipe_left": "wipeleft",
    "dissolve": "dissolve",
}

UGC_RECOMMENDED_TRANSITIONS = ["slideleft", "slideright", "smoothleft", "zoomin", "circlecrop", "fadewhite"]

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def natural_sort_key(s: str) -> List[Any]:
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def get_clip_metadata(clip_path: Path, ffprobe_exe: str) -> Dict[str, Any]:
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
        dur = float(data.get("format", {}).get("duration", 0.0))
        streams = data.get("streams", [])
        w, h, fps = 1080, 1920, 30.0
        has_audio = False
        for s in streams:
            if s.get("codec_type") == "video":
                w = int(s.get("width", 1080))
                h = int(s.get("height", 1920))
                fps_parts = s.get("r_frame_rate", "30/1").split('/')
                fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) > 0 else 30.0
            elif s.get("codec_type") == "audio":
                has_audio = True
        return {"path": clip_path, "filename": clip_path.name, "duration": dur, "width": w, "height": h, "fps": fps, "has_audio": has_audio}
    except Exception as e:
        return {"path": clip_path, "filename": clip_path.name, "duration": 0.0, "width": 1080, "height": 1920, "fps": 30.0, "has_audio": True}

def find_input_clips(input_dir: Path, pattern: Optional[str] = None) -> List[Path]:
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

def get_whoosh_sfx() -> Optional[Path]:
    sfx_dir = Path("SFX")
    if not sfx_dir.exists():
        return None
    preferred = ["whoosh-6316.mp3", "WHOOSH 2 SFX.mp3", "WHOOSH 6 SFX.mp3", "WHOOSH 3 SFX.mp3", "Whoosh Fast.wav"]
    for p_name in preferred:
        p = sfx_dir / p_name
        if p.exists():
            return p
    for f in sfx_dir.glob("*whoosh*.*"):
        return f
    return None

def prep_whoosh_sfx(sfx_path: Path) -> Tuple[Any, int]:
    from pydub import AudioSegment, silence
    import numpy as np
    clip = AudioSegment.from_file(str(sfx_path))
    nonsilent = silence.detect_nonsilent(clip, min_silence_len=20, silence_thresh=-40)
    if nonsilent and nonsilent[0][0] > 10:
        clip = clip[nonsilent[0][0] - 10:]
    samples = np.array(clip.get_array_of_samples())
    if len(samples) > 0:
        max_search = min(len(samples), int(clip.frame_rate * 0.50 * clip.channels))
        peak_idx = int(np.argmax(np.abs(samples[:max_search]))) // clip.channels
        peak_ms = int((peak_idx / clip.frame_rate) * 1000)
    else:
        peak_ms = 70
    return clip.apply_gain(-6.0), peak_ms

@app.command(name="list")
def list_transitions():
    """List available transition styles and recommendations."""
    table = Table(title="Available UGC Video Transitions (Makinity Cut)")
    table.add_column("Transition Style", style="cyan", no_wrap=True)
    table.add_column("FFmpeg Keyword", style="green")
    table.add_column("Aesthetic Impact", style="yellow")
    
    hints = {
        "slide_left": "Fast horizontal swipe (signature TikTok/Reels look)",
        "slide_up": "Vertical card scroll (feed-scroll feel)",
        "smooth_left": "Eased directional motion blur wipe",
        "zoom_in": "High-energy snap zoom punch into next scene",
        "circle_crop": "Retro iris reveal (playful, focuses on subject center)",
        "fade_white": "Dramatic flash-to-white scene transition",
        "fade_black": "Classic theatrical dip to black",
        "pixelize": "Digital glitch wipe (tech / gaming / crypto)",
        "random": "Alternates dynamic transitions across all cuts automatically",
    }
    
    for name, ffmpeg_kw in TRANSITION_MAP.items():
        table.add_row(name, ffmpeg_kw, hints.get(name, "Clean visual cut transition"))
    table.add_row("random", "dynamic", hints["random"])
    console.print(table)

@app.command(name="apply")
def apply_transitions(
    input_dir: Path = typer.Option(Path("Input"), "--input-dir", "-i", help="Directory containing source clips"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    transition: str = typer.Option("slide_left", "--transition", "-t", help="Transition: slide_left, slide_up, smooth_left, zoom_in, circle_crop, fade_white, pixelize, random"),
    duration: float = typer.Option(0.22, "--duration", "-d", help="Transition duration in seconds (0.18s - 0.35s)"),
    auto_sfx: bool = typer.Option(True, "--auto-sfx/--no-sfx", help="Auto-sync whoosh sound effects on transitions"),
    target_res: str = typer.Option("1080x1920", "--res", "-r", help="Target output resolution (default: 1080x1920 vertical)"),
    fps: int = typer.Option(30, "--fps", help="Unified frame rate (default: 30 fps)")
):
    """
    Stitches clips in Input/ with dynamic transitions and auto-synced whoosh sound effects.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    clips = find_input_clips(input_dir)
    
    if len(clips) < 2:
        console.print(f"[bold red]Error: Transitions require at least 2 clips in '{input_dir}' (Found: {len(clips)})[/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"stitched_{transition}_sequence.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"[bold green]Assembling {len(clips)} clips with '{transition}' transitions:[/bold green]")
    meta_list = []
    for idx, c in enumerate(clips, 1):
        m = get_clip_metadata(c, ffprobe_exe)
        meta_list.append(m)
        console.print(f"  {idx}. [cyan]{c.name}[/cyan] ({m['duration']:.2f}s)")
        
    parts = target_res.lower().split("x")
    tw, th = int(parts[0]), int(parts[1])
    
    cmd = [ffmpeg_exe, "-y"]
    for c in clips:
        cmd.extend(["-i", str(c)])
        
    filter_parts = []
    
    for idx, m in enumerate(meta_list):
        v_norm = f"[{idx}:v]scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th},setsar=1,fps={fps}[v{idx}]"
        filter_parts.append(v_norm)
        if m["has_audio"]:
            a_norm = f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,aresample=48000[a{idx}]"
        else:
            dur = max(0.1, m["duration"])
            a_norm = f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={dur:.3f}[a{idx}]"
        filter_parts.append(a_norm)
        
    cur_vid_label = "v0"
    cur_aud_label = "a0"
    accumulated_dur = meta_list[0]["duration"]
    transition_times = []
    
    for i in range(1, len(meta_list)):
        next_m = meta_list[i]
        offset = accumulated_dur - duration
        transition_times.append(offset)
        
        if transition.lower() == "random":
            xfade_type = random.choice(UGC_RECOMMENDED_TRANSITIONS)
        else:
            xfade_type = TRANSITION_MAP.get(transition.lower(), "slideleft")
            
        next_vid_label = f"xfv{i}"
        next_aud_label = f"xfa{i}"
        
        v_xfade = f"[{cur_vid_label}][v{i}]xfade=transition={xfade_type}:duration={duration:.3f}:offset={offset:.3f}[{next_vid_label}]"
        filter_parts.append(v_xfade)
        
        # Exponential audio curve prevents voice blurring and mumble across sentence boundaries
        a_xfade = f"[{cur_aud_label}][a{i}]acrossfade=d={duration:.3f}:curve1=exp:curve2=exp[{next_aud_label}]"
        filter_parts.append(a_xfade)
        
        cur_vid_label = next_vid_label
        cur_aud_label = next_aud_label
        accumulated_dur = (accumulated_dur + next_m["duration"]) - duration
        
    filter_complex = ";".join(filter_parts)
    temp_stitched = output_dir / "temp_transition_no_sfx.mp4"
    
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", f"[{cur_vid_label}]",
        "-map", f"[{cur_aud_label}]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        str(temp_stitched if auto_sfx else output_file)
    ])
    
    console.print(f"[cyan]Rendering {len(clips)-1} transitions across timeline via FFmpeg...[/cyan]")
    subprocess.run(cmd, check=True)
    
    if auto_sfx:
        whoosh_file = get_whoosh_sfx()
        if whoosh_file:
            console.print(f"[bold green]Auto-syncing Whoosh SFX:[/bold green] [yellow]{whoosh_file.name}[/yellow] (Transient-Peak Aligned)")
            from pydub import AudioSegment
            
            temp_wav = output_dir / "temp_t_audio.wav"
            temp_mixed_wav = output_dir / "temp_t_mixed.wav"
            subprocess.run([ffmpeg_exe, "-y", "-i", str(temp_stitched), "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", str(temp_wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            base_audio = AudioSegment.from_file(str(temp_wav))
            sfx_clip, peak_ms = prep_whoosh_sfx(whoosh_file)
            
            for t_sec in transition_times:
                # Align the whoosh peak exactly to the visual midpoint of the transition
                midpoint_ms = int((t_sec + duration / 2.0) * 1000)
                pos_ms = max(0, midpoint_ms - peak_ms)
                if pos_ms < len(base_audio):
                    base_audio = base_audio.overlay(sfx_clip, position=pos_ms)
                    
            base_audio.export(str(temp_mixed_wav), format="wav")
            
            subprocess.run([
                ffmpeg_exe, "-y",
                "-i", str(temp_stitched),
                "-i", str(temp_mixed_wav),
                "-c:v", "copy",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_file)
            ], check=True)
            
            for tmp in [temp_stitched, temp_wav, temp_mixed_wav]:
                if tmp.exists():
                    tmp.unlink()
        else:
            temp_stitched.replace(output_file)
            
    final_meta = get_clip_metadata(output_file, ffprobe_exe)
    console.print(f"\n[bold green]Success![/bold green] Transition video saved to: [bold]{output_file}[/bold]")
    console.print(f"Total Duration: [bold yellow]{final_meta['duration']:.2f}s[/bold yellow] with {len(clips)-1} smooth transitions!")

if __name__ == "__main__":
    app()


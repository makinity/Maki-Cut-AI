#!/usr/bin/env python3
"""
Keyframed Dynamic Zooms & Camera Reframing Script for UGC Videos.
Applies slow push-ins, slow pull-backs, and punch-cut zooms to create dynamic motion
and prevent visual fatigue in talking-head / UGC content.
"""

import sys
import os
import math
import subprocess
import json
from pathlib import Path
from typing import Tuple, List, Optional
import typer
from rich.console import Console

app = typer.Typer(help="Apply keyframed camera zooms and dynamic reframing to video footage.")
console = Console()

ANCHOR_Y_FACTORS = {
    "face": 0.35,     # Upper third (ideal for talking heads / 9:16 vertical video)
    "center": 0.50,   # Exact center
    "top": 0.15,      # Top edge
    "bottom": 0.85,   # Bottom edge
}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_specs(video_path: Path, ffprobe_exe: str) -> Tuple[int, int, float, float]:
    """Retrieve width, height, duration, and fps from input video."""
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:format=duration",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(res.stdout)
    stream = data["streams"][0]
    duration = float(data["format"]["duration"])
    w = int(stream["width"])
    h = int(stream["height"])
    fps_parts = stream["r_frame_rate"].split('/')
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
    return w, h, duration, fps

def generate_smart_zoom_cues(
    duration: float,
    scene_cuts_str: Optional[str] = None,
    ass_file: Optional[Path] = None,
    max_zoom: float = 1.18
) -> List[Tuple[float, float]]:
    """
    Intelligently generates camera framing cues aligned to scene boundaries,
    sentence pauses, and retention hooks (no mid-sentence robotic cuts).
    """
    cuts = []
    if scene_cuts_str:
        for x in scene_cuts_str.split(","):
            try:
                val = float(x.strip())
                if 0.5 < val < duration - 0.5:
                    cuts.append(val)
            except ValueError:
                pass
    elif ass_file and ass_file.exists():
        with open(ass_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    parts = line.split(",", 9)
                    if len(parts) >= 10:
                        h, m, s = parts[1].split(":")
                        t_sec = int(h) * 3600 + int(m) * 60 + float(s)
                        if not cuts or (t_sec - cuts[-1] >= 2.8 and t_sec < duration - 1.0):
                            if t_sec > 0.8:
                                cuts.append(t_sec)

    cuts.sort()
    if not cuts:
        cur_t = 3.0
        while cur_t < duration - 1.0:
            cuts.append(cur_t)
            cur_t += 3.2

    cues = []
    first_cut = cuts[0] if cuts else duration
    if first_cut >= 3.5:
        cues.append((0.0, max_zoom))
        cues.append((2.0, 1.0))
        is_zoomed = False
    else:
        cues.append((0.0, max_zoom))
        is_zoomed = True

    for cp in cuts:
        is_zoomed = not is_zoomed
        z_val = max_zoom if is_zoomed else 1.0
        cues.append((cp, z_val))

    return cues

def build_zoom_expression(
    mode: str,
    duration: float,
    max_zoom: float = 1.15,
    cues_str: Optional[str] = None,
    cycle_interval: float = 3.5,
    scene_cuts: Optional[str] = None,
    from_ass: Optional[Path] = None
) -> str:
    """
    Constructs an analytical mathematical expression Z(t) for FFmpeg crop filter.
    """
    zoom_delta = max_zoom - 1.0
    
    if mode == "slow_push":
        return f"(1.0+{zoom_delta:.4f}*(t/{duration:.3f}))"
        
    elif mode == "slow_pull":
        return f"({max_zoom:.4f}-{zoom_delta:.4f}*(t/{duration:.3f}))"
        
    elif mode == "punch_cuts":
        return f"(1.0+{zoom_delta:.4f}*mod(floor(t/{cycle_interval:.2f}),2))"
        
    elif mode == "smart_cuts":
        cues_list = generate_smart_zoom_cues(duration, scene_cuts_str=scene_cuts, ass_file=from_ass, max_zoom=max_zoom)
        if not cues_list:
            return "1.0"
        expr = f"{cues_list[-1][1]:.3f}"
        for i in range(len(cues_list) - 1, 0, -1):
            t_next = cues_list[i][0]
            z_val = cues_list[i-1][1]
            expr = f"if(lt(t,{t_next:.3f}),{z_val:.3f},{expr})"
        return expr
        
    elif mode == "custom" and cues_str:
        cues = []
        for item in cues_str.split(","):
            if ":" in item:
                t_str, z_str = item.strip().split(":", 1)
                cues.append((float(t_str), float(z_str)))
        cues.sort(key=lambda x: x[0])
        
        if not cues:
            return "1.0"
            
        expr = f"{cues[-1][1]:.3f}"
        for i in range(len(cues) - 1, 0, -1):
            t_curr = cues[i-1][0]
            t_next = cues[i][0]
            z_val = cues[i-1][1]
            expr = f"if(lt(t,{t_next:.3f}),{z_val:.3f},{expr})"
        return expr
        
    else:
        return f"(1.0+{zoom_delta:.4f}*(t/{duration:.3f}))"

@app.command()
def apply_zoom(
    input_file: Path = typer.Option(..., "--input", "-i", help="Input video path (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    mode: str = typer.Option("smart_cuts", "--mode", "-m", help="Zoom mode: 'smart_cuts', 'punch_cuts', 'slow_push', 'slow_pull', 'custom'"),
    max_zoom: float = typer.Option(1.18, "--max-zoom", "-z", help="Peak zoom level (e.g. 1.15 = 115%, 1.25 = 125%)"),
    anchor: str = typer.Option("face", "--anchor", "-a", help="Focal anchor point: 'face' (upper third), 'center', 'top', 'bottom'"),
    cycle: float = typer.Option(3.5, "--cycle", "-c", help="Interval in seconds for punch_cuts alternating zoom"),
    scene_cuts: Optional[str] = typer.Option(None, "--scene-cuts", help="Scene cut timestamps e.g. '7.7, 10.9, 16.9'"),
    from_ass: Optional[Path] = typer.Option(None, "--from-ass", help="Generate smart zoom cuts from ASS subtitle timestamps"),
    cues: Optional[str] = typer.Option(None, "--cues", help="Custom timestamp cues (e.g. '0:1.0, 4.0:1.18, 8.0:1.0')")
):
    """
    Applies dynamic keyframed camera zooms (slow zooms, punch zooms, reframing).
    Keeps talking-head UGC footage engaging and eliminates static visual fatigue.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_{mode}.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"[bold green]Analyzing video dimensions and duration...[/bold green]")
    w, h, duration, fps = get_video_specs(input_file, ffprobe_exe)
    console.print(f"Video: [bold yellow]{w}x{h}[/bold yellow] · [bold yellow]{duration:.2f}s[/bold yellow] · [bold yellow]{fps:.1f} fps[/bold yellow]")
    
    zoom_expr = build_zoom_expression(
        mode,
        duration,
        max_zoom=max_zoom,
        cues_str=cues,
        cycle_interval=cycle,
        scene_cuts=scene_cuts,
        from_ass=from_ass
    )
    console.print(f"Applied Zoom Profile: [bold cyan]{mode.upper()}[/bold cyan] (Max: {max_zoom}x)")
    
    y_factor = ANCHOR_Y_FACTORS.get(anchor.lower(), 0.35 if h > w else 0.50)
    
    scale_expr = f"scale=w='trunc({w}*({zoom_expr})/2)*2':h='trunc({h}*({zoom_expr})/2)*2':eval=frame"
    crop_filter = f"crop={w}:{h}:x='(iw-ow)/2':y='(ih-oh)*{y_factor:.2f}'"
    vf_chain = f"{scale_expr},{crop_filter}"
    
    console.print("[cyan]Rendering keyframed video zoom via FFmpeg...[/cyan]")
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
        "-vf", vf_chain,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        str(output_file)
    ]
    
    subprocess.run(cmd, check=True)
    console.print(f"\n[bold green]Success![/bold green] Keyframed zoom video saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()


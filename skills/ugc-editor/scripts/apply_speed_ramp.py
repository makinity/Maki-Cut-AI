#!/usr/bin/env python3
"""
Speed Ramping & Velocity Curve Engine for UGC Videos (CapCut 1:1 Parity).
Applies variable speed ramping curves (Montage, Bullet Time, Flash In, Hero, Custom Bezier)
to video clips using FFmpeg dynamic PTS and chained audio time-stretching.
"""

import sys
import os
import json
import math
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import typer
from rich.console import Console

# Ensure utf-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(help="Apply dynamic speed ramping curves to video clips.")
console = Console(highlight=False, legacy_windows=False)

# Preset speed curves: list of (time_percentage 0.0-1.0, speed_multiplier)
PRESET_CURVES: Dict[str, List[Tuple[float, float]]] = {
    "none": [
        (0.0, 1.0),
        (1.0, 1.0)
    ],
    "custom": [
        (0.0, 1.0),
        (0.25, 1.5),
        (0.5, 0.5),
        (0.75, 2.0),
        (1.0, 1.0)
    ],
    "montage": [
        (0.0, 2.5),
        (0.2, 0.6),
        (0.4, 2.8),
        (0.6, 0.5),
        (0.8, 2.2),
        (1.0, 1.0)
    ],
    "hero": [
        (0.0, 0.6),
        (0.25, 0.6),
        (0.5, 3.5),
        (0.75, 0.5),
        (1.0, 0.5)
    ],
    "bullet_time": [
        (0.0, 3.0),
        (0.2, 2.5),
        (0.35, 0.2),
        (0.65, 0.2),
        (0.8, 2.5),
        (1.0, 3.0)
    ],
    "flash_in": [
        (0.0, 4.0),
        (0.25, 3.0),
        (0.5, 1.0),
        (1.0, 1.0)
    ],
    "flash_out": [
        (0.0, 1.0),
        (0.5, 1.0),
        (0.75, 3.0),
        (1.0, 4.5)
    ],
    "jump_cut": [
        (0.0, 3.0),
        (0.2, 1.0),
        (0.4, 3.0),
        (0.6, 1.0),
        (0.8, 3.0),
        (1.0, 1.0)
    ]
}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_media_duration(file_path: Path, ffprobe_exe: str) -> float:
    cmd = [
        ffprobe_exe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(json.loads(res.stdout)["format"]["duration"])
    except Exception:
        return 8.0

def build_atempo_chain(speed: float) -> str:
    """Build chained atempo filters for speeds outside [0.5, 2.0]."""
    speed = max(0.1, min(10.0, float(speed)))
    filters = []
    current = speed
    while current > 2.0:
        filters.append("atempo=2.0")
        current /= 2.0
    while current < 0.5:
        filters.append("atempo=0.5")
        current /= 0.5
    filters.append(f"atempo={current:.4f}")
    return ",".join(filters)

def calculate_ramped_duration(orig_dur: float, points: List[Tuple[float, float]]) -> float:
    """Calculate the exact mathematical duration resulting from a speed curve."""
    if not points or len(points) < 2:
        return orig_dur
    pts = sorted(points, key=lambda p: p[0])
    total_new = 0.0
    for i in range(len(pts) - 1):
        t1, v1 = pts[i]
        t2, v2 = pts[i + 1]
        dt = (t2 - t1) * orig_dur
        v1 = max(0.05, v1)
        v2 = max(0.05, v2)
        if abs(v1 - v2) < 0.001:
            total_new += dt / v1
        else:
            total_new += (dt / (v2 - v1)) * math.log(v2 / v1)
    return round(total_new, 3)

def parse_points_str(points_str: str) -> List[Tuple[float, float]]:
    pts = []
    for item in points_str.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":") if ":" in item else item.split(",")
        if len(parts) == 2:
            pts.append((float(parts[0]), float(parts[1])))
    if not pts:
        pts = [(0.0, 1.0), (1.0, 1.0)]
    return sorted(pts, key=lambda p: p[0])

@app.command()
def apply(
    input_file: Path = typer.Option(..., "-i", "--input", help="Source video file"),
    output_file: Path = typer.Option(..., "-o", "--output", help="Destination video file"),
    preset: str = typer.Option("montage", "-p", "--preset", help="Preset name (montage, hero, bullet_time, flash_in, flash_out, jump_cut, custom)"),
    points_str: Optional[str] = typer.Option(None, "--points", help="Custom points string (e.g. '0:3.0;0.5:0.5;1.0:3.0')"),
    smooth_slowmo: bool = typer.Option(False, "--smooth-slowmo", help="Use optical flow/frame interpolation for slow sections")
):
    """Apply speed ramping curve to a video file."""
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file {input_file} does not exist.[/bold red]")
        raise typer.Exit(1)

    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    orig_dur = get_media_duration(input_file, ffprobe_exe)

    if points_str:
        points = parse_points_str(points_str)
    else:
        preset_key = preset.lower().replace("-", "_")
        points = PRESET_CURVES.get(preset_key, PRESET_CURVES["montage"])

    # Ensure points start at 0.0 and end at 1.0
    if points[0][0] > 0.0:
        points.insert(0, (0.0, points[0][1]))
    if points[-1][0] < 1.0:
        points.append((1.0, points[-1][1]))

    estimated_dur = calculate_ramped_duration(orig_dur, points)
    console.print(f"[bold cyan]⚡ Speed Ramping:[/bold cyan] Preset: [yellow]{preset}[/yellow] | Original: [white]{orig_dur:.2f}s[/white] ➔ Ramped: [green]{estimated_dur:.2f}s[/green]")

    # Check if input has audio stream
    has_audio = False
    try:
        chk = subprocess.run([
            ffprobe_exe, "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(input_file)
        ], capture_output=True, text=True)
        if "audio" in chk.stdout:
            has_audio = True
    except Exception:
        pass

    # Build multi-segment FFmpeg filtergraph
    filter_complex_parts = []
    v_labels = []
    a_labels = []
    num_segments = len(points) - 1

    for i in range(num_segments):
        t1, v1 = points[i]
        t2, v2 = points[i + 1]
        start_sec = t1 * orig_dur
        end_sec = t2 * orig_dur
        avg_speed = max(0.1, min(10.0, (v1 + v2) / 2.0))
        pts_factor = 1.0 / avg_speed

        # Video segment
        v_label = f"v{i}"
        if avg_speed < 0.6 and smooth_slowmo:
            # Enhanced motion interpolation for butter-smooth slow motion
            v_filter = (
                f"[0:v]trim=start={start_sec:.3f}:end={end_sec:.3f},"
                f"setpts=PTS-STARTPTS,minterpolate=fps=60:mi_mode=mci,"
                f"setpts={pts_factor:.4f}*PTS[{v_label}]"
            )
        else:
            v_filter = (
                f"[0:v]trim=start={start_sec:.3f}:end={end_sec:.3f},"
                f"setpts=PTS-STARTPTS,setpts={pts_factor:.4f}*PTS[{v_label}]"
            )
        filter_complex_parts.append(v_filter)
        v_labels.append(f"[{v_label}]")

        # Audio segment
        if has_audio:
            a_label = f"a{i}"
            atempo_str = build_atempo_chain(avg_speed)
            a_filter = (
                f"[0:a]atrim=start={start_sec:.3f}:end={end_sec:.3f},"
                f"asetpts=PTS-STARTPTS,{atempo_str}[{a_label}]"
            )
            filter_complex_parts.append(a_filter)
            a_labels.append(f"[{a_label}]")

    # Concatenate all segments
    concat_inputs = ""
    for i in range(num_segments):
        concat_inputs += v_labels[i]
        if has_audio:
            concat_inputs += a_labels[i]

    if has_audio:
        concat_filter = f"{concat_inputs}concat=n={num_segments}:v=1:a=1[v_out][a_out]"
    else:
        concat_filter = f"{concat_inputs}concat=n={num_segments}:v=1:a=0[v_out]"
    filter_complex_parts.append(concat_filter)

    full_filter = ";".join(filter_complex_parts)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_exe, "-y",
        "-i", str(input_file),
        "-filter_complex", full_filter,
        "-map", "[v_out]"
    ]
    if has_audio:
        cmd.extend(["-map", "[a_out]", "-c:a", "aac", "-b:a", "192k"])
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_file)
    ])

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        final_dur = get_media_duration(output_file, ffprobe_exe)
        console.print(f"[bold green]✔ Speed ramp applied successfully![/bold green] Output: {output_file.name} ({final_dur:.2f}s)")
    except subprocess.CalledProcessError as err:
        console.print(f"[bold red]FFmpeg Error:[/bold red] {err.stderr}")
        raise typer.Exit(1)

@app.command()
def presets():
    """List available presets and their keypoints."""
    data = {}
    for name, pts in PRESET_CURVES.items():
        data[name] = [{"time": p[0], "speed": p[1]} for p in pts]
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    app()

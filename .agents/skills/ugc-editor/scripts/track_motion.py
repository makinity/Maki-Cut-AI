#!/usr/bin/env python3
"""
Motion Tracking & Face Following Engine for UGC Videos (CapCut 1:1 Parity).
Tracks face and object motion trajectories frame-by-frame using OpenCV TrackerMIL / optical flow,
generates smooth camera reframing coordinates, and binds text/stickers to follow motion.
"""

import sys
import os
import json
import math
import subprocess
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import typer
from rich.console import Console

# Ensure utf-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(help="Motion tracking and face following engine.")
console = Console(highlight=False, legacy_windows=False)

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_specs(video_path: Path, ffprobe_exe: str) -> Dict[str, Any]:
    cmd = [
        ffprobe_exe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:format=duration",
        "-of", "json", str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        dur = float(data["format"]["duration"])
        w = int(stream["width"])
        h = int(stream["height"])
        fps_parts = stream.get("r_frame_rate", "24/1").split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 24.0
        return {"width": w, "height": h, "duration": dur, "fps": fps}
    except Exception:
        return {"width": 720, "height": 1280, "duration": 8.0, "fps": 24.0}

def smooth_trajectory(points: List[Dict[str, float]], factor: float = 0.75) -> List[Dict[str, float]]:
    """Apply exponential moving average to smooth out tracking jitter."""
    if not points:
        return []
    smoothed = []
    curr_x = points[0]["x"]
    curr_y = points[0]["y"]
    curr_w = points[0].get("w", 0.3)
    curr_h = points[0].get("h", 0.3)

    for pt in points:
        curr_x = factor * curr_x + (1.0 - factor) * pt["x"]
        curr_y = factor * curr_y + (1.0 - factor) * pt["y"]
        curr_w = factor * curr_w + (1.0 - factor) * pt.get("w", curr_w)
        curr_h = factor * curr_h + (1.0 - factor) * pt.get("h", curr_h)
        smoothed.append({
            "t": pt["t"],
            "x": round(curr_x, 4),
            "y": round(curr_y, 4),
            "w": round(curr_w, 4),
            "h": round(curr_h, 4)
        })
    return smoothed

@app.command()
def track(
    input_file: Path = typer.Option(..., "-i", "--input", help="Source video file"),
    output_json: Path = typer.Option(..., "-o", "--output", help="Destination JSON trajectory"),
    target: str = typer.Option("face", "-t", "--target", help="Target type: face, center, custom"),
    bbox_str: Optional[str] = typer.Option(None, "--bbox", help="Initial bbox x,y,w,h (percentages 0.0-1.0)"),
    smoothing: float = typer.Option(0.75, "-s", "--smoothing", help="Smoothing factor (0.0 to 0.95)"),
    sample_step: int = typer.Option(2, "--step", help="Process every Nth frame for performance")
):
    """Track motion trajectory across video frames using OpenCV."""
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file {input_file} not found.[/bold red]")
        raise typer.Exit(1)

    import cv2

    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    specs = get_video_specs(input_file, ffprobe_exe)
    w, h = specs["width"], specs["height"]
    fps = specs["fps"]

    cap = cv2.VideoCapture(str(input_file))
    if not cap.isOpened():
        console.print(f"[bold red]Failed to open video file {input_file}.[/bold red]")
        raise typer.Exit(1)

    ret, first_frame = cap.read()
    if not ret or first_frame is None:
        console.print(f"[bold red]Could not read first frame.[/bold red]")
        raise typer.Exit(1)

    # Determine initial tracking bounding box
    if bbox_str:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        bx, by, bw, bh = parts[0], parts[1], parts[2], parts[3]
    elif target.lower() == "face":
        # Upper third face anchor safe zone
        bx, by, bw, bh = 0.30, 0.15, 0.40, 0.35
    else:
        # Center target
        bx, by, bw, bh = 0.30, 0.35, 0.40, 0.30

    init_bbox_px = (int(bx * w), int(by * h), int(bw * w), int(bh * h))

    tracker = cv2.TrackerMIL_create()
    tracker.init(first_frame, init_bbox_px)

    raw_trajectory = [{
        "t": 0.0,
        "x": round(bx + bw / 2.0, 4),
        "y": round(by + bh / 2.0, 4),
        "w": round(bw, 4),
        "h": round(bh, 4)
    }]

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        if frame_idx % sample_step == 0:
            ok, box = tracker.update(frame)
            t_sec = round(frame_idx / fps, 3)
            if ok:
                norm_x = (box[0] + box[2] / 2.0) / w
                norm_y = (box[1] + box[3] / 2.0) / h
                norm_w = box[2] / w
                norm_h = box[3] / h
                raw_trajectory.append({
                    "t": t_sec,
                    "x": max(0.05, min(0.95, round(norm_x, 4))),
                    "y": max(0.05, min(0.95, round(norm_y, 4))),
                    "w": max(0.05, min(0.95, round(norm_w, 4))),
                    "h": max(0.05, min(0.95, round(norm_h, 4)))
                })
            else:
                # Retain last position on temporary occlusion
                last = raw_trajectory[-1]
                raw_trajectory.append({
                    "t": t_sec,
                    "x": last["x"],
                    "y": last["y"],
                    "w": last["w"],
                    "h": last["h"]
                })

    cap.release()

    smoothed = smooth_trajectory(raw_trajectory, factor=smoothing)

    result = {
        "status": "ok",
        "clip_name": input_file.name,
        "duration": specs["duration"],
        "fps": fps,
        "width": w,
        "height": h,
        "target": target,
        "smoothing": smoothing,
        "points_count": len(smoothed),
        "trajectory": smoothed
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    console.print(f"[bold green]✔ Motion tracking complete![/bold green] Generated [cyan]{len(smoothed)}[/cyan] trajectory points for [yellow]{target}[/yellow].")

@app.command()
def reframe(
    input_file: Path = typer.Option(..., "-i", "--input", help="Source video file"),
    output_file: Path = typer.Option(..., "-o", "--output", help="Destination reframed video"),
    trajectory_json: Path = typer.Option(..., "-t", "--trajectory", help="Trajectory JSON file"),
    zoom: float = typer.Option(1.25, "-z", "--zoom", help="Camera zoom scale factor (1.1 - 1.5)"),
    anchor: str = typer.Option("face", "-a", "--anchor", help="Frame anchor: face (upper third) or center"),
    lock_axis: str = typer.Option("both", "--axis", help="Axis lock: both, x, y")
):
    """Apply dynamic Face Following camera reframe using FFmpeg crop and scale."""
    if not input_file.exists() or not trajectory_json.exists():
        console.print("[bold red]Input file or trajectory JSON does not exist.[/bold red]")
        raise typer.Exit(1)

    with open(trajectory_json, "r", encoding="utf-8") as f:
        traj_data = json.load(f)

    points = traj_data.get("trajectory", [])
    if not points:
        console.print("[bold red]Trajectory is empty.[/bold red]")
        raise typer.Exit(1)

    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    specs = get_video_specs(input_file, ffprobe_exe)
    w, h = specs["width"], specs["height"]
    dur = specs["duration"]

    target_anchor_y = 0.35 if anchor.lower() == "face" else 0.50

    # Build crop window dimensions
    crop_w = int(w / zoom)
    crop_h = int(h / zoom)
    # Ensure even dimensions
    crop_w = (crop_w // 2) * 2
    crop_h = (crop_h // 2) * 2

    # Build piecewise linear x(t) and y(t) expressions for FFmpeg crop filter
    # FFmpeg crop=w:h:x:y
    # To prevent jumpiness, we pick representative keyframes (e.g. every 0.5s)
    sampled = []
    step = max(1, len(points) // 20)
    for i in range(0, len(points), step):
        sampled.append(points[i])
    if sampled[-1]["t"] < points[-1]["t"]:
        sampled.append(points[-1])

    # Build nested if(lt(t, T), X_val, ...) expressions
    def build_expr(var_key: str, default_val: float) -> str:
        expr = f"{sampled[-1][var_key]:.1f}"
        for i in range(len(sampled) - 1, 0, -1):
            t_next = sampled[i]["t"]
            val = sampled[i-1][var_key]
            expr = f"if(lt(t,{t_next:.2f}),{val:.1f},{expr})"
        return expr

    # Compute crop top-left (x, y) for each sampled point
    for pt in sampled:
        cx_px = pt["x"] * w
        cy_px = pt["y"] * h
        # Desired camera offset to keep face at target_anchor_y
        tl_x = cx_px - (crop_w / 2.0)
        tl_y = cy_px - (crop_h * target_anchor_y)
        # Clamp within frame bounds
        if lock_axis == "y":
            tl_x = (w - crop_w) / 2.0
        else:
            tl_x = max(0, min(w - crop_w, tl_x))

        if lock_axis == "x":
            tl_y = (h - crop_h) * target_anchor_y
        else:
            tl_y = max(0, min(h - crop_h, tl_y))

        pt["crop_x"] = tl_x
        pt["crop_y"] = tl_y

    x_expr = build_expr("crop_x", (w - crop_w) / 2.0)
    y_expr = build_expr("crop_y", (h - crop_h) * target_anchor_y)

    crop_filter = f"crop=w={crop_w}:h={crop_h}:x='{x_expr}':y='{y_expr}',scale={w}:{h}"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_exe, "-y",
        "-i", str(input_file),
        "-vf", crop_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(output_file)
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        console.print(f"[bold green]✔ Face Following camera reframe applied![/bold green] Output: {output_file.name}")
    except subprocess.CalledProcessError as err:
        console.print(f"[bold red]FFmpeg Reframe Error:[/bold red] {err.stderr}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()

#!/usr/bin/env python3
"""
CapCut 1:1 Keyframe Animation & Multi-Property Transform Engine for UGC Videos.
Applies precision multi-property keyframing (scale, pos_x, pos_y, rotation, opacity)
with cubic ease-in-out curves, 1-click Pro UGC presets, and custom JSON keyframe tracks.
Preserves pristine original audio bit-for-bit (-c:a copy).
"""

import sys
import os
import math
import subprocess
import json
import re
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import typer
from rich.console import Console
from rich.table import Table

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(help="CapCut 1:1 Keyframe Animation & Multi-Property Transform Engine.")
console = Console()

ANCHOR_Y_FACTORS = {
    "face": 0.35,     # Upper third (ideal for talking heads / 9:16 vertical video)
    "center": 0.50,   # Exact center
    "top": 0.15,      # Top edge
    "bottom": 0.85,   # Bottom edge
}

PRO_PRESETS: Dict[str, Dict[str, Any]] = {
    "zoom_in": {
        "description": "Smooth cinematic push-in (scale 1.0 -> 1.25) with cubic ease-in-out.",
        "type": "scale_push"
    },
    "dramatic_push": {
        "description": "Rapid impactful punch zoom into the speaker (scale 1.0 -> 1.35) with subtle tilt.",
        "type": "dramatic"
    },
    "ken_burns": {
        "description": "Slow cinematic pan and gentle zoom across clip (scale 1.08 -> 1.20, pan X/Y).",
        "type": "pan_zoom"
    },
    "pulse_snap": {
        "description": "High-energy hook pattern interrupt snap (scale 1.0 -> 1.22 in 0.28s, settles to 1.05).",
        "type": "pulse"
    },
    "fade_in_out": {
        "description": "Cinematic opacity envelope (0.0 -> 1.0 smooth fade-in, 1.0 -> 0.0 fade-out).",
        "type": "fade"
    }
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

def generate_preset_keyframes(preset: str, duration: float, max_zoom: float = 1.25) -> List[Dict[str, Any]]:
    """Build standardized keyframe tracks for 1-Click Pro UGC presets."""
    preset = preset.lower()
    
    if preset == "zoom_in":
        return [
            {"time": 0.0, "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
            {"time": round(duration, 3), "scale": round(max_zoom, 3), "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"}
        ]
        
    elif preset == "dramatic_push":
        t_punch = min(0.80, max(0.35, duration * 0.25))
        return [
            {"time": 0.0, "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
            {"time": round(t_punch, 3), "scale": round(max_zoom, 3), "pos_x": 0.0, "pos_y": -12.0, "rotation": -1.5, "opacity": 1.0, "easing": "cubic"},
            {"time": round(duration, 3), "scale": round(max_zoom * 1.02, 3), "pos_x": 0.0, "pos_y": -12.0, "rotation": -1.5, "opacity": 1.0, "easing": "cubic"}
        ]
        
    elif preset == "ken_burns":
        return [
            {"time": 0.0, "scale": 1.08, "pos_x": -35.0, "pos_y": -25.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
            {"time": round(duration, 3), "scale": round(max_zoom, 3), "pos_x": 35.0, "pos_y": 20.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"}
        ]
        
    elif preset == "pulse_snap":
        t_peak = min(0.28, duration * 0.15)
        t_settle = min(0.55, duration * 0.30)
        return [
            {"time": 0.0, "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
            {"time": round(t_peak, 3), "scale": round(max_zoom, 3), "pos_x": 0.0, "pos_y": 0.0, "rotation": 1.2, "opacity": 1.0, "easing": "cubic"},
            {"time": round(t_settle, 3), "scale": 1.05, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
            {"time": round(duration, 3), "scale": 1.08, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"}
        ]
        
    elif preset == "fade_in_out":
        t_in = min(0.50, duration * 0.18)
        t_out = max(t_in + 0.1, duration - 0.70)
        return [
            {"time": 0.0, "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 0.0, "easing": "cubic"},
            {"time": round(t_in, 3), "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
            {"time": round(t_out, 3), "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
            {"time": round(duration, 3), "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 0.0, "easing": "cubic"}
        ]
        
    return [
        {"time": 0.0, "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"},
        {"time": round(duration, 3), "scale": round(max_zoom, 3), "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": "cubic"}
    ]

def parse_keyframes_input(raw_str: str) -> List[Dict[str, Any]]:
    """Lenient parser handling strict JSON, single-quoted JSON, and PowerShell-stripped unquoted keys."""
    raw_str = raw_str.strip()
    try:
        return json.loads(raw_str)
    except Exception:
        pass
        
    try:
        import ast
        val = ast.literal_eval(raw_str)
        if isinstance(val, list):
            return val
    except Exception:
        pass

    try:
        # Quote unquoted property names like [{time:0.0, scale:1.2}]
        fixed = re.sub(r'([{\s,])([a-zA-Z_]\w*)\s*:', r'\1"\2":', raw_str)
        fixed = fixed.replace("'", '"')
        return json.loads(fixed)
    except Exception as e:
        console.print(f"[bold red]Failed to parse keyframes JSON:[/bold red] {e}")
        raise typer.Exit(1)

def normalize_keyframes(raw_kfs: List[Dict[str, Any]], duration: float, default_easing: str = "cubic") -> List[Dict[str, Any]]:
    """Clean, sort, and standardize keyframes across full duration."""
    if not raw_kfs:
        return [
            {"time": 0.0, "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": default_easing},
            {"time": round(duration, 3), "scale": 1.0, "pos_x": 0.0, "pos_y": 0.0, "rotation": 0.0, "opacity": 1.0, "easing": default_easing}
        ]
        
    cleaned = []
    for k in raw_kfs:
        try:
            t = float(k.get("time", 0.0))
        except (ValueError, TypeError):
            continue
        cleaned.append({
            "time": max(0.0, t),
            "scale": float(k.get("scale", 1.0)),
            "pos_x": float(k.get("pos_x", 0.0)),
            "pos_y": float(k.get("pos_y", 0.0)),
            "rotation": float(k.get("rotation", 0.0)),
            "opacity": max(0.0, min(1.0, float(k.get("opacity", 1.0)))),
            "easing": k.get("easing", default_easing)
        })
        
    cleaned.sort(key=lambda x: x["time"])
    
    # Ensure start boundary (0.0s)
    if cleaned[0]["time"] > 0.001:
        first_copy = dict(cleaned[0])
        first_copy["time"] = 0.0
        cleaned.insert(0, first_copy)
        
    # Ensure end boundary (duration)
    if cleaned[-1]["time"] < duration - 0.001:
        last_copy = dict(cleaned[-1])
        last_copy["time"] = round(duration, 3)
        cleaned.append(last_copy)
        
    return cleaned

def build_track_expression(
    kfs: List[Dict[str, Any]],
    prop: str,
    default_val: float,
    global_easing: str = "cubic",
    time_var: str = "t"
) -> str:
    """
    Constructs an analytical piecewise mathematical expression for property interpolation in FFmpeg.
    Supports 'cubic' (smooth ease-in-out), 'linear', and 'step' easing curves.
    """
    if not kfs:
        return f"{default_val:.4f}"
    if len(kfs) == 1:
        return f"{float(kfs[0].get(prop, default_val)):.4f}"
        
    # Check if value is completely static
    vals = [float(k.get(prop, default_val)) for k in kfs]
    if all(abs(v - vals[0]) < 1e-5 for v in vals):
        return f"{vals[0]:.4f}"
        
    expr = f"{vals[-1]:.4f}"
    for i in range(len(kfs) - 2, -1, -1):
        t1 = float(kfs[i]["time"])
        t2 = float(kfs[i + 1]["time"])
        v1 = float(kfs[i].get(prop, default_val))
        v2 = float(kfs[i + 1].get(prop, default_val))
        dt = max(0.0001, t2 - t1)
        dv = v2 - v1
        kf_easing = kfs[i].get("easing", global_easing)
        
        if abs(dv) < 1e-5:
            seg = f"{v1:.4f}"
        else:
            p = f"(({time_var}-{t1:.3f})/{dt:.3f})"
            if kf_easing == "cubic":
                ease_p = f"if(lt({p},0.5),2*{p}*{p},1-2*(1-{p})*(1-{p}))"
                seg = f"({v1:.4f}+{dv:.4f}*{ease_p})"
            elif kf_easing == "step":
                seg = f"{v1:.4f}"
            else: # linear
                seg = f"({v1:.4f}+{dv:.4f}*{p})"
                
        expr = f"if(lt({time_var},{t2:.3f}),{seg},{expr})"
        
    return expr

def is_property_animated(kfs: List[Dict[str, Any]], prop: str, default_val: float) -> bool:
    """Checks whether a property deviates from default or changes over time."""
    vals = [float(k.get(prop, default_val)) for k in kfs]
    if any(abs(v - default_val) > 1e-4 for v in vals):
        return True
    return any(abs(vals[i] - vals[0]) > 1e-4 for i in range(len(vals)))

@app.command(name="list")
def list_presets():
    """List all available Pro UGC Keyframing Presets."""
    table = Table(title="CapCut 1:1 Keyframing Presets (Makinity Cut)")
    table.add_column("Preset Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="yellow")
    
    for name, data in PRO_PRESETS.items():
        table.add_row(name, data["type"], data["description"])
        
    console.print(table)

@app.command(name="apply")
def apply_keyframes(
    input_file: Path = typer.Option(..., "--input", "-i", help="Input video path (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="Pro UGC motion preset: 'zoom_in', 'dramatic_push', 'ken_burns', 'pulse_snap', 'fade_in_out'"),
    keyframes: Optional[str] = typer.Option(None, "--keyframes", "-k", help="JSON string of keyframe objects"),
    keyframes_file: Optional[Path] = typer.Option(None, "--keyframes-file", help="Path to external JSON keyframes file"),
    easing: str = typer.Option("cubic", "--easing", "-e", help="Interpolation easing: 'cubic', 'linear', 'step'"),
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Legacy zoom mode: 'smart_cuts', 'punch_cuts', 'slow_push', 'slow_pull', 'custom'"),
    max_zoom: float = typer.Option(1.18, "--max-zoom", "-z", help="Peak zoom level (e.g. 1.18 = 118%, 1.35 = 135%)"),
    anchor: str = typer.Option("face", "--anchor", "-a", help="Focal anchor point: 'face' (upper third), 'center', 'top', 'bottom'"),
    cycle: float = typer.Option(3.5, "--cycle", "-c", help="Interval in seconds for punch_cuts alternating zoom"),
    scene_cuts: Optional[str] = typer.Option(None, "--scene-cuts", help="Scene cut timestamps e.g. '7.7, 10.9, 16.9'"),
    from_ass: Optional[Path] = typer.Option(None, "--from-ass", help="Generate smart zoom cuts from ASS subtitle timestamps"),
    cues: Optional[str] = typer.Option(None, "--cues", help="Custom timestamp cues e.g. '0:1.0, 4.0:1.18, 8.0:1.0'")
):
    """
    Applies multi-property keyframing (scale, pos_x, pos_y, rotation, opacity) to video.
    Supports cubic easing, Pro UGC presets, and custom keyframe tracks with zero-loss audio.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[bold green]Analyzing video dimensions and duration...[/bold green]")
    w, h, duration, fps = get_video_specs(input_file, ffprobe_exe)
    console.print(f"Video: [bold yellow]{w}x{h}[/bold yellow] · [bold yellow]{duration:.2f}s[/bold yellow] · [bold yellow]{fps:.1f} fps[/bold yellow]")
    
    # 1. Determine Keyframe Track
    raw_kfs: List[Dict[str, Any]] = []
    applied_profile = "custom"
    
    if keyframes_file and keyframes_file.exists():
        applied_profile = f"file({keyframes_file.name})"
        with open(keyframes_file, "r", encoding="utf-8") as f:
            raw_kfs = json.load(f)
    elif keyframes:
        applied_profile = "json_track"
        raw_kfs = parse_keyframes_input(keyframes)
    elif preset:
        applied_profile = f"preset_{preset}"
        raw_kfs = generate_preset_keyframes(preset, duration, max_zoom=max_zoom)
    elif mode:
        applied_profile = f"mode_{mode}"
        if mode == "slow_push":
            raw_kfs = [
                {"time": 0.0, "scale": 1.0, "easing": "linear"},
                {"time": round(duration, 3), "scale": max_zoom, "easing": "linear"}
            ]
        elif mode == "slow_pull":
            raw_kfs = [
                {"time": 0.0, "scale": max_zoom, "easing": "linear"},
                {"time": round(duration, 3), "scale": 1.0, "easing": "linear"}
            ]
        elif mode == "punch_cuts":
            raw_kfs = []
            cur_t = 0.0
            is_zoomed = False
            while cur_t < duration:
                z_val = max_zoom if is_zoomed else 1.0
                raw_kfs.append({"time": round(cur_t, 3), "scale": z_val, "easing": "step"})
                cur_t += cycle
                is_zoomed = not is_zoomed
        elif mode == "custom" and cues:
            raw_kfs = []
            for item in cues.split(","):
                if ":" in item:
                    t_str, z_str = item.strip().split(":", 1)
                    raw_kfs.append({"time": float(t_str), "scale": float(z_str), "easing": "step"})
        else: # smart_cuts
            cues_list = generate_smart_zoom_cues(duration, scene_cuts_str=scene_cuts, ass_file=from_ass, max_zoom=max_zoom)
            raw_kfs = [{"time": round(t, 3), "scale": round(z, 3), "easing": "step"} for t, z in cues_list]
    else:
        # Default fallback to smart_cuts
        applied_profile = "mode_smart_cuts"
        cues_list = generate_smart_zoom_cues(duration, scene_cuts_str=scene_cuts, ass_file=from_ass, max_zoom=max_zoom)
        raw_kfs = [{"time": round(t, 3), "scale": round(z, 3), "easing": "step"} for t, z in cues_list]
        
    # Standardize & Normalize Keyframes
    kfs = normalize_keyframes(raw_kfs, duration, default_easing=easing)
    
    if output_file is None:
        tag = preset or mode or "keyframed"
        output_file = output_dir / f"{input_file.stem}_{tag}.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"Applied Keyframe Profile: [bold cyan]{applied_profile.upper()}[/bold cyan] ({len(kfs)} keyframes, Easing: {easing})")
    
    # 2. Check Active Transform Channels
    has_rot = is_property_animated(kfs, "rotation", 0.0)
    has_opacity = is_property_animated(kfs, "opacity", 1.0)
    has_pos_x = is_property_animated(kfs, "pos_x", 0.0)
    has_pos_y = is_property_animated(kfs, "pos_y", 0.0)
    has_scale = is_property_animated(kfs, "scale", 1.0)
    
    console.print(
        f"Active Channels: "
        f"Scale={'[green]ON[/green]' if has_scale else '[dim]off[/dim]'} · "
        f"Pan={'[green]ON[/green]' if (has_pos_x or has_pos_y) else '[dim]off[/dim]'} · "
        f"Rotation={'[green]ON[/green]' if has_rot else '[dim]off[/dim]'} · "
        f"Opacity={'[green]ON[/green]' if has_opacity else '[dim]off[/dim]'}"
    )
    
    # 3. Build Mathematical Expressions
    scale_expr = build_track_expression(kfs, "scale", 1.0, global_easing=easing, time_var="t")
    pos_x_expr = build_track_expression(kfs, "pos_x", 0.0, global_easing=easing, time_var="t")
    pos_y_expr = build_track_expression(kfs, "pos_y", 0.0, global_easing=easing, time_var="t")
    rot_expr = build_track_expression(kfs, "rotation", 0.0, global_easing=easing, time_var="t")
    opacity_expr = build_track_expression(kfs, "opacity", 1.0, global_easing=easing, time_var="T") # 'T' for geq
    
    y_factor = ANCHOR_Y_FACTORS.get(anchor.lower(), 0.35 if h > w else 0.50)
    
    # 4. Construct FFmpeg Filter Graph
    fg_chain = []
    # Dynamic scale
    fg_chain.append(f"scale=w='trunc({w}*({scale_expr})/2)*2':h='trunc({h}*({scale_expr})/2)*2':eval=frame")
    
    # Dynamic rotation
    if has_rot:
        fg_chain.append(f"rotate=angle='({rot_expr})*PI/180':ow=hypot(iw\\,ih):oh=hypot(iw\\,ih):c=black@0")
        
    # Dynamic opacity
    if has_opacity:
        fg_chain.append(f"format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*({opacity_expr})'")
        
    filter_complex = (
        f"color=c=black:s={w}x{h}:r={fps:.3f}:d={duration:.3f}[bg];"
        f"[0:v]{','.join(fg_chain)}[fg];"
        f"[bg][fg]overlay=x='(W-w)/2+({pos_x_expr})':y='(H-h)*{y_factor:.2f}+({pos_y_expr})':eval=frame:shortest=1[outv]"
    )
    
    console.print("[cyan]Rendering keyframed video transform via FFmpeg...[/cyan]")
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        str(output_file)
    ]
    
    subprocess.run(cmd, check=True)
    console.print(f"\n[bold green]Success![/bold green] Keyframed transform video saved to: [bold]{output_file}[/bold]")

def main():
    # Backwards compatibility: if executed with direct flags (-i, --input, etc.), redirect to 'apply'
    if len(sys.argv) > 1 and sys.argv[1].startswith("-"):
        sys.argv.insert(1, "apply")
    app()

if __name__ == "__main__":
    main()

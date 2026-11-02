#!/usr/bin/env python3
"""
Dynamic Morphing Shapes & Motion Graphics Generator for UGC Videos.
Applies animated bar graphs, circular progress motions, morphing rectangles, and focus rings.
Designed to boost viewer retention, engagement, and visual callouts in UGC/short-form content.
"""

import sys
import os
import math
import subprocess
import json
from pathlib import Path
from typing import Tuple, Optional
import typer
from rich.console import Console
from PIL import Image, ImageDraw, ImageFont

app = typer.Typer(help="Add dynamic morphing shapes and motion graphics overlays.")
console = Console()

PALETTES = {
    "cyan": {"primary": (0, 229, 255, 255), "secondary": (0, 150, 255, 200), "text": (255, 255, 255, 255)},
    "yellow": {"primary": (255, 230, 0, 255), "secondary": (255, 170, 0, 200), "text": (0, 0, 0, 255)},
    "green": {"primary": (57, 255, 20, 255), "secondary": (0, 200, 83, 200), "text": (0, 0, 0, 255)},
    "orange": {"primary": (255, 87, 34, 255), "secondary": (255, 152, 0, 200), "text": (255, 255, 255, 255)},
    "purple": {"primary": (179, 136, 255, 255), "secondary": (124, 77, 255, 200), "text": (255, 255, 255, 255)},
}

def get_ffmpeg_paths():
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_specs(video_path: Path, ffprobe_exe: str) -> Tuple[int, int, float]:
    """Retrieve width, height, and fps from the input video."""
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    info = json.loads(res.stdout)["streams"][0]
    w = int(info["width"])
    h = int(info["height"])
    fps_parts = info["r_frame_rate"].split('/')
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
    return w, h, fps

def ease_out_back(t: float) -> float:
    """Overshoot ease-out curve for bouncy kinetic motion."""
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * math.pow(t - 1.0, 3) + c1 * math.pow(t - 1.0, 2)

def ease_out_cubic(t: float) -> float:
    """Smooth cubic deceleration."""
    return 1.0 - math.pow(1.0 - t, 3)

def render_bargraph_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """Renders one frame of an animated rising bar graph card."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    card_w, card_h = int(w * 0.75), int(h * 0.28)
    if pos == "top_center":
        cx, cy = w // 2, int(h * 0.25)
    elif pos == "bottom_center":
        cx, cy = w // 2, int(h * 0.75)
    else:
        cx, cy = w // 2, h // 2
        
    x0, y0 = cx - card_w // 2, cy - card_h // 2
    x1, y1 = cx + card_w // 2, cy + card_h // 2
    
    scale = ease_out_back(min(1.0, progress / 0.25)) if progress < 0.25 else 1.0
    if scale <= 0:
        return img
        
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=(15, 20, 30, 225), outline=palette["primary"], width=4)
    
    title_text = label if label else "METRIC ACCELERATION"
    draw.text((x0 + 35, y0 + 25), title_text.upper(), fill=palette["primary"], font_size=int(card_h * 0.12))
    
    bar_targets = [0.35, 0.55, 0.80, 1.00]
    num_bars = len(bar_targets)
    bar_area_w = card_w - 70
    gap = 25
    bar_w = (bar_area_w - (num_bars - 1) * gap) // num_bars
    base_y = y1 - 40
    max_bar_h = card_h - 110
    
    bar_progress = max(0.0, (progress - 0.15) / 0.7)
    ease_p = ease_out_cubic(min(1.0, bar_progress))
    
    for i, target in enumerate(bar_targets):
        current_h = max_bar_h * target * ease_p
        bx0 = x0 + 35 + i * (bar_w + gap)
        bx1 = bx0 + bar_w
        by0 = base_y - current_h
        by1 = base_y
        
        bar_fill = palette["primary"] if i == num_bars - 1 else palette["secondary"]
        if current_h > 4:
            draw.rounded_rectangle([bx0, by0, bx1, by1], radius=14, fill=bar_fill)
            
    return img

def render_circular_motion_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """Renders one frame of an animated circular progress ring with metric callout."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    diameter = int(min(w, h) * 0.42)
    radius = diameter // 2
    
    if pos == "top_center":
        cx, cy = w // 2, int(h * 0.28)
    elif pos == "bottom_center":
        cx, cy = w // 2, int(h * 0.72)
    else:
        cx, cy = w // 2, h // 2
        
    box = [cx - radius, cy - radius, cx + radius, cy + radius]
    
    draw.ellipse(box, outline=(255, 255, 255, 40), width=18)
    
    arc_p = ease_out_cubic(min(1.0, progress / 0.75))
    end_angle = -90 + (arc_p * 360)
    
    if end_angle > -90:
        draw.arc(box, start=-90, end=end_angle, fill=palette["primary"], width=20)
        
    pct = int(arc_p * 100)
    center_text = f"{pct}%" if not label else label
    draw.text((cx, cy - 15), center_text, fill=(255, 255, 255, 255), anchor="mm", font_size=int(diameter * 0.22))
    
    pulse_p = (progress * 2.0) % 1.0
    pulse_r = radius + int(pulse_p * 40)
    pulse_alpha = int((1.0 - pulse_p) * 160)
    draw.ellipse(
        [cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r],
        outline=(palette["primary"][0], palette["primary"][1], palette["primary"][2], pulse_alpha),
        width=4
    )
    
    return img

def render_rectangle_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """Renders one frame of a morphing rounded rectangle callout card."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    card_w, card_h = int(w * 0.80), int(h * 0.16)
    
    if pos == "top_center":
        cx, cy = w // 2, int(h * 0.20)
    elif pos == "bottom_center":
        cx, cy = w // 2, int(h * 0.78)
    else:
        cx, cy = w // 2, h // 2
        
    scale = ease_out_back(min(1.0, progress / 0.25)) if progress < 0.25 else 1.0
    cur_w = int(card_w * scale)
    cur_h = int(card_h * scale)
    
    if cur_w <= 10 or cur_h <= 10:
        return img
        
    x0, y0 = cx - cur_w // 2, cy - cur_h // 2
    x1, y1 = cx + cur_w // 2, cy + cur_h // 2
    
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(10, 15, 25, 230), outline=palette["primary"], width=6)
    
    dot_r = 14
    dot_x = x0 + 40
    dot_y = cy
    draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=palette["primary"])
    
    card_text = label if label else "PAY ATTENTION TO THIS"
    draw.text((dot_x + 30, cy), card_text.upper(), fill=(255, 255, 255, 255), anchor="lm", font_size=int(card_h * 0.32))
    
    return img

def render_focus_ring_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """Renders an animated target/focus ring with rotating crosshairs."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cx, cy = w // 2, h // 2
    base_radius = int(min(w, h) * 0.16)
    
    scale = 1.0 + 0.10 * math.sin(progress * 6.28 * 2)
    r = int(base_radius * scale)
    
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=palette["primary"], width=5)
    
    tick = 22
    draw.line([cx - r - tick, cy, cx - r + tick, cy], fill=palette["primary"], width=4)
    draw.line([cx + r - tick, cy, cx + r + tick, cy], fill=palette["primary"], width=4)
    draw.line([cx, cy - r - tick, cx, cy - r + tick], fill=palette["primary"], width=4)
    draw.line([cx, cy + r - tick, cx, cy + r + tick], fill=palette["primary"], width=4)
    
    if label:
        draw.text((cx, cy + r + 30), label.upper(), fill=palette["primary"], anchor="mm", font_size=36)
        
    return img

def render_badge_callout_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """Renders a high-energy animated badge / sticker pop with glowing double borders."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    badge_w, badge_h = int(w * 0.72), int(h * 0.085)
    if pos == "top_center":
        cx, cy = w // 2, int(h * 0.18)
    elif pos == "bottom_center":
        cx, cy = w // 2, int(h * 0.80)
    else:
        cx, cy = w // 2, int(h * 0.28)
        
    scale = ease_out_back(min(1.0, progress / 0.22)) if progress < 0.22 else 1.0
    cur_w = int(badge_w * scale)
    cur_h = int(badge_h * scale)
    if cur_w <= 10 or cur_h <= 10:
        return img
        
    x0, y0 = cx - cur_w // 2, cy - cur_h // 2
    x1, y1 = cx + cur_w // 2, cy + cur_h // 2
    
    draw.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], radius=28, outline=palette["secondary"], width=3)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(12, 18, 30, 240), outline=palette["primary"], width=5)
    
    font = None
    font_path = "C:/Windows/Fonts/arialbd.ttf"
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, int(badge_h * 0.38))
        except Exception:
            font = None
            
    badge_text = label if label else "VIRAL HACK"
    draw.text((cx, cy), badge_text.upper(), fill=(255, 255, 255, 255), anchor="mm", font=font)
    return img

def render_progress_bar_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """Renders an animated viewer retention progress indicator line."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    bar_h = 10
    if pos == "top_center":
        y0 = 12
    else:
        y0 = h - bar_h - 12
    y1 = y0 + bar_h
    
    draw.rounded_rectangle([24, y0, w - 24, y1], radius=5, fill=(255, 255, 255, 50))
    fill_w = int((w - 48) * min(1.0, progress))
    if fill_w > 4:
        draw.rounded_rectangle([24, y0, 24 + fill_w, y1], radius=5, fill=palette["primary"])
        draw.ellipse([24 + fill_w - 6, y0 - 3, 24 + fill_w + 6, y1 + 3], fill=(255, 255, 255, 240))
        
    return img

@app.command()
def apply_shape(
    input_file: Path = typer.Option(..., "--input", "-i", help="Source video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    shape: str = typer.Option("bargraph", "--shape", "-s", help="Shape type: 'bargraph', 'circular_motion', 'rectangle', 'focus_ring', 'badge_callout', 'progress_bar'"),
    start_time: float = typer.Option(1.5, "--start", "-t", help="Start timestamp in seconds when shape appears"),
    duration: float = typer.Option(3.0, "--duration", "-d", help="Duration in seconds of the shape animation"),
    label: str = typer.Option("", "--label", "-l", help="Text, number, or callout label inside shape"),
    color: str = typer.Option("cyan", "--color", "-c", help="Color theme: cyan, yellow, green, orange, purple"),
    position: str = typer.Option("center", "--position", "-pos", help="Position: center, top_center, bottom_center")
):
    """
    Renders and composites animated morphing shapes onto video for high viewer retention.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_with_{shape}.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    palette = PALETTES.get(color.lower(), PALETTES["cyan"])
    
    console.print(f"[bold green]Inspecting video specifications...[/bold green]")
    w, h, fps = get_video_specs(input_file, ffprobe_exe)
    console.print(f"Canvas: [bold yellow]{w}x{h}[/bold yellow] @ [bold yellow]{fps:.1f} fps[/bold yellow]")
    
    total_frames = max(1, int(duration * fps))
    end_time = start_time + duration
    console.print(f"Generating [bold cyan]{shape}[/bold cyan] ({total_frames} frames from {start_time:.2f}s to {end_time:.2f}s)...")
    
    overlay_clip = output_dir / f"temp_{shape}_overlay.mov"
    
    encode_cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "qtrle",
        "-r", str(fps),
        str(overlay_clip)
    ]
    
    proc = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for f_idx in range(total_frames):
        p = f_idx / float(total_frames)
        if shape == "bargraph":
            frame_img = render_bargraph_frame(p, w, h, label, palette, position)
        elif shape == "circular_motion":
            frame_img = render_circular_motion_frame(p, w, h, label, palette, position)
        elif shape == "rectangle":
            frame_img = render_rectangle_frame(p, w, h, label, palette, position)
        elif shape == "focus_ring":
            frame_img = render_focus_ring_frame(p, w, h, label, palette, position)
        elif shape == "badge_callout":
            frame_img = render_badge_callout_frame(p, w, h, label, palette, position)
        elif shape == "progress_bar":
            frame_img = render_progress_bar_frame(p, w, h, label, palette, position)
        else:
            frame_img = render_bargraph_frame(p, w, h, label, palette, position)
            
        proc.stdin.write(frame_img.tobytes())
        
    proc.stdin.close()
    proc.wait()
    console.print("[green]Transparent motion graphic sequence rendered.[/green]")
    
    console.print(f"[cyan]Compositing morphing shape into video stream...[/cyan]")
    composite_cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_file),
        "-itsoffset", f"{start_time:.3f}",
        "-i", str(overlay_clip),
        "-filter_complex", f"[0:v][1:v]overlay=0:0:enable='between(t,{start_time:.3f},{end_time:.3f})'[outv]",
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        str(output_file)
    ]
    
    subprocess.run(composite_cmd, check=True)
    
    if overlay_clip.exists():
        overlay_clip.unlink()
        
    console.print(f"\n[bold green]Success![/bold green] Morphing shape applied! Saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()


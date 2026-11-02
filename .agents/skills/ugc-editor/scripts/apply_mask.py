#!/usr/bin/env python3
"""
Geometric Masking & Feather Engine for UGC Videos (CapCut 1:1 Parity).
Applies customizable geometric masks (Circle, Rectangle, Split, Filmstrip, Heart, Star)
with real-time edge feathering blur, rotation, corner roundness, and invert controls.
"""

import sys
import os
import json
import math
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import typer
from rich.console import Console
from PIL import Image, ImageDraw, ImageFilter, ImageOps

# Ensure utf-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(help="Apply geometric masks with edge feathering to video clips.")
console = Console(highlight=False, legacy_windows=False)

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_dimensions(file_path: Path, ffprobe_exe: str) -> Tuple[int, int]:
    cmd = [
        ffprobe_exe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)["streams"][0]
        return int(data["width"]), int(data["height"])
    except Exception:
        return 720, 1280

def generate_mask_image(
    width: int,
    height: int,
    shape: str = "circle",
    feather: float = 20.0,
    size_w: float = 0.70,     # Percentage of width
    size_h: float = 0.70,     # Percentage of height
    pos_x: float = 0.50,      # Center X (0.0 - 1.0)
    pos_y: float = 0.50,      # Center Y (0.0 - 1.0)
    roundness: float = 30.0,  # Corner radius in pixels
    rotation: float = 0.0,    # Degrees
    invert: bool = False
) -> Image.Image:
    """Generate high-precision grayscale mask with Pillow."""
    # Create black canvas (0 = transparent / masked out)
    img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(img)

    cx = int(width * pos_x)
    cy = int(height * pos_y)
    w_px = int(width * size_w)
    h_px = int(height * size_h)

    shape = shape.lower()

    if shape == "circle":
        rx = w_px // 2
        ry = h_px // 2
        bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
        draw.ellipse(bbox, fill=255)

    elif shape == "rectangle":
        x0 = cx - (w_px // 2)
        y0 = cy - (h_px // 2)
        x1 = cx + (w_px // 2)
        y1 = cy + (h_px // 2)
        r = min(roundness, min(w_px, h_px) // 2)
        if r > 0:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=int(r), fill=255)
        else:
            draw.rectangle([x0, y0, x1, y1], fill=255)

    elif shape == "split":
        # Split screen along angled dividing line
        # Draw half plane
        angle_rad = math.radians(rotation)
        nx = math.cos(angle_rad)
        ny = math.sin(angle_rad)
        corners = [(0, 0), (width, 0), (width, height), (0, height)]
        poly = []
        for x, y in corners:
            val = (x - cx) * nx + (y - cy) * ny
            if val <= 0:
                poly.append((x, y))
        draw.rectangle([0, 0, width, cy], fill=255)

    elif shape == "filmstrip":
        # Dual cinematic top & bottom letterbox bars
        bar_h = int(height * (1.0 - size_h) / 2.0)
        draw.rectangle([0, bar_h, width, height - bar_h], fill=255)

    elif shape == "heart":
        # Parametric heart shape centered at (cx, cy)
        pts = []
        scale = min(w_px, h_px) / 32.0
        for deg in range(0, 360, 5):
            t = math.radians(deg)
            x = 16 * (math.sin(t) ** 3)
            y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
            pts.append((cx + x * scale, cy + y * scale))
        draw.polygon(pts, fill=255)

    elif shape == "star":
        # 5-point star
        pts = []
        r_outer = min(w_px, h_px) // 2
        r_inner = r_outer * 0.4
        for i in range(10):
            r = r_outer if i % 2 == 0 else r_inner
            angle = math.radians(i * 36 - 90)
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(pts, fill=255)

    else:
        draw.rectangle([0, 0, width, height], fill=255)

    # Rotation
    if rotation != 0.0 and shape not in ["split"]:
        img = img.rotate(-rotation, resample=Image.Resampling.BICUBIC, center=(cx, cy))

    # Feathering (Gaussian Blur)
    if feather > 0.0:
        blur_r = max(1.0, min(100.0, feather))
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_r))

    # Invert Mask
    if invert:
        img = ImageOps.invert(img)

    return img

@app.command()
def apply(
    input_file: Path = typer.Option(..., "-i", "--input", help="Source video file"),
    output_file: Path = typer.Option(..., "-o", "--output", help="Destination video file"),
    shape: str = typer.Option("circle", "-s", "--shape", help="Mask shape (circle, rectangle, split, filmstrip, heart, star)"),
    feather: float = typer.Option(20.0, "-f", "--feather", help="Edge feathering blur in pixels (0 - 100)"),
    size_w: float = typer.Option(0.70, "--width", help="Width percentage (0.1 - 1.0)"),
    size_h: float = typer.Option(0.70, "--height", help="Height percentage (0.1 - 1.0)"),
    pos_x: float = typer.Option(0.50, "-x", "--pos-x", help="Center X position (0.0 - 1.0)"),
    pos_y: float = typer.Option(0.50, "-y", "--pos-y", help="Center Y position (0.0 - 1.0)"),
    roundness: float = typer.Option(30.0, "--roundness", help="Corner radius for rectangle"),
    rotation: float = typer.Option(0.0, "-r", "--rotation", help="Rotation angle in degrees"),
    invert: bool = typer.Option(False, "--invert", help="Invert mask inside-out")
):
    """Apply geometric mask with edge feathering to a video file."""
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file {input_file} does not exist.[/bold red]")
        raise typer.Exit(1)

    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    w, h = get_video_dimensions(input_file, ffprobe_exe)

    console.print(f"[bold cyan]🎭 Geometric Masking:[/bold cyan] Shape: [yellow]{shape}[/yellow] | Feather: [white]{feather}px[/white] | Res: {w}x{h}")

    # Generate the mask image
    mask_img = generate_mask_image(
        width=w, height=h,
        shape=shape, feather=feather,
        size_w=size_w, size_h=size_h,
        pos_x=pos_x, pos_y=pos_y,
        roundness=roundness, rotation=rotation,
        invert=invert
    )

    temp_mask_path = output_file.parent / f"temp_mask_{input_file.stem}.png"
    temp_mask_path.parent.mkdir(parents=True, exist_ok=True)
    mask_img.save(temp_mask_path)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    filter_complex = (
        f"[1:v]scale={w}:{h}[mask];"
        f"[0:v][mask]alphamerge[vmasked];"
        f"color=c=black:s={w}x{h}:r=30[bg];"
        f"[bg][vmasked]overlay=shortest=1[v_out]"
    )

    cmd = [
        ffmpeg_exe, "-y",
        "-i", str(input_file),
        "-loop", "1", "-i", str(temp_mask_path),
        "-filter_complex", filter_complex,
        "-map", "[v_out]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-shortest",
        str(output_file)
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        console.print(f"[bold green]✔ Successfully applied {shape} mask with {feather}px feathering![/bold green] Output: {output_file.name}")
    except subprocess.CalledProcessError as err:
        console.print(f"[bold red]FFmpeg Mask Error:[/bold red] {err.stderr}")
        raise typer.Exit(1)
    finally:
        if temp_mask_path.exists():
            temp_mask_path.unlink()

@app.command()
def preview_mask(
    output_png: Path = typer.Option(..., "-o", "--output", help="PNG path to save generated mask preview"),
    width: int = typer.Option(720, "-w", "--width", help="Canvas width"),
    height: int = typer.Option(1280, "-h", "--height", help="Canvas height"),
    shape: str = typer.Option("circle", "-s", "--shape", help="Shape name"),
    feather: float = typer.Option(20.0, "-f", "--feather", help="Feather blur in pixels"),
    size_w: float = typer.Option(0.70, "--size-w"),
    size_h: float = typer.Option(0.70, "--size-h"),
    pos_x: float = typer.Option(0.50, "--pos-x"),
    pos_y: float = typer.Option(0.50, "--pos-y"),
    roundness: float = typer.Option(30.0, "--roundness"),
    rotation: float = typer.Option(0.0, "--rotation"),
    invert: bool = typer.Option(False, "--invert")
):
    """Generate a standalone mask PNG image for visual preview."""
    mask_img = generate_mask_image(
        width=width, height=height,
        shape=shape, feather=feather,
        size_w=size_w, size_h=size_h,
        pos_x=pos_x, pos_y=pos_y,
        roundness=roundness, rotation=rotation,
        invert=invert
    )
    output_png.parent.mkdir(parents=True, exist_ok=True)
    mask_img.save(output_png)
    print(f"Mask preview saved to: {output_png}")

if __name__ == "__main__":
    app()

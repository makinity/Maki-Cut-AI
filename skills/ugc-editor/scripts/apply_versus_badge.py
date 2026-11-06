#!/usr/bin/env python3
"""
Glowing Neon Versus & Price Comparison Badge Generator for UGC Videos.
Inspired by MrBeast ($1 vs $10,000 challenge) and viral direct-response comparison ads.
Renders glowing neon price/versus badges with multi-layer outer auras, pill backplates,
spring bounce entrance physics, and synchronized SFX.
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
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(help="Add glowing neon price tags and versus comparison badges.")
console = Console()

COLOR_PALETTES = {
    "red": {
        "text": (255, 255, 255, 255),
        "primary": (255, 30, 45, 255),
        "glow": (255, 30, 45, 180),
        "bg": (15, 10, 12, 235),
        "border": (255, 60, 75, 255),
    },
    "green": {
        "text": (255, 255, 255, 255),
        "primary": (0, 255, 60, 255),
        "glow": (0, 255, 60, 180),
        "bg": (10, 16, 12, 235),
        "border": (30, 255, 90, 255),
    },
    "gold": {
        "text": (255, 255, 255, 255),
        "primary": (255, 200, 40, 255),
        "glow": (255, 190, 30, 180),
        "bg": (18, 15, 10, 235),
        "border": (255, 215, 70, 255),
    },
    "cyan": {
        "text": (255, 255, 255, 255),
        "primary": (0, 235, 255, 255),
        "glow": (0, 220, 255, 180),
        "bg": (10, 15, 18, 235),
        "border": (50, 245, 255, 255),
    },
    "yellow": {
        "text": (0, 0, 0, 255),
        "primary": (255, 235, 10, 255),
        "glow": (255, 220, 0, 180),
        "bg": (20, 20, 10, 235),
        "border": (255, 240, 50, 255),
    },
    "purple": {
        "text": (255, 255, 255, 255),
        "primary": (195, 80, 255, 255),
        "glow": (185, 60, 255, 180),
        "bg": (16, 10, 18, 235),
        "border": (210, 110, 255, 255),
    },
    "white": {
        "text": (0, 0, 0, 255),
        "primary": (245, 245, 245, 255),
        "glow": (255, 255, 255, 180),
        "bg": (15, 15, 15, 235),
        "border": (255, 255, 255, 255),
    },
}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_specs(video_path: Path, ffprobe_exe: str) -> Tuple[int, int, float, float]:
    cmd = [
        ffprobe_exe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    info = json.loads(res.stdout)["streams"][0]
    w = int(info["width"])
    h = int(info["height"])
    fps_parts = info["r_frame_rate"].split('/')
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
    duration = float(info.get("duration", 0.0))
    if duration == 0.0:
        cmd_fmt = [ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video_path)]
        res_fmt = subprocess.run(cmd_fmt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration = float(json.loads(res_fmt.stdout).get("format", {}).get("duration", 10.0))
    return w, h, fps, duration

def get_best_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    font_paths = [
        "fonts/ArchivoBlack-Regular.ttf" if bold else "fonts/Archivo-Variable.ttf",
        "fonts/Roboto-Bold.ttf" if bold else "fonts/Roboto.ttf",
        "fonts/Montserrat.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

def ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * math.pow(t - 1.0, 3) + c1 * math.pow(t - 1.0, 2)

def draw_single_badge(
    draw: ImageDraw.ImageDraw,
    glow_img: Image.Image,
    center_x: int,
    center_y: int,
    label: str,
    palette_name: str,
    scale: float,
    glow_intensity: float = 1.0,
    font_size_base: int = 68
) -> None:
    """Draws a single high-contrast neon pill badge with outer glow halo."""
    pal = COLOR_PALETTES.get(palette_name.lower(), COLOR_PALETTES["red"])
    
    font_size = max(16, int(font_size_base * scale))
    font = get_best_font(font_size, bold=True)
    
    # Calculate text bounding box
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    pad_x = int(36 * scale)
    pad_y = int(20 * scale)
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    radius = bh // 2
    
    x0 = center_x - bw // 2
    y0 = center_y - bh // 2
    x1 = center_x + bw // 2
    y1 = center_y + bh // 2
    
    # 1. Render Outer Neon Glow onto glow_img for smooth blurring
    glow_draw = ImageDraw.Draw(glow_img)
    glow_color = pal["glow"]
    glow_alpha = int(glow_color[3] * glow_intensity * min(1.0, scale))
    glow_rgba = (glow_color[0], glow_color[1], glow_color[2], glow_alpha)
    
    glow_margin = int(14 * scale)
    glow_draw.rounded_rectangle(
        [x0 - glow_margin, y0 - glow_margin, x1 + glow_margin, y1 + glow_margin],
        radius=radius + glow_margin,
        fill=glow_rgba
    )
    
    # 2. Render Pill Backplate on main draw
    bg_color = pal["bg"]
    border_color = pal["border"]
    border_w = max(2, int(4 * scale))
    
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        fill=bg_color,
        outline=border_color,
        width=border_w
    )
    
    # Inner accent rim
    inner_pad = max(2, int(3 * scale))
    draw.rounded_rectangle(
        [x0 + inner_pad, y0 + inner_pad, x1 - inner_pad, y1 - inner_pad],
        radius=max(2, radius - inner_pad),
        outline=(pal["primary"][0], pal["primary"][1], pal["primary"][2], 120),
        width=max(1, int(2 * scale))
    )
    
    # 3. Render High-Impact Text (with thick dark drop-shadow for contrast)
    tx = center_x
    ty = center_y - int(2 * scale)
    
    # Shadow
    shadow_offset = max(2, int(3 * scale))
    draw.text((tx + shadow_offset, ty + shadow_offset), label, font=font, fill=(0, 0, 0, 240), anchor="mm")
    
    # Primary Text (colored if yellow/white, or pure white with colored rim)
    text_color = pal["text"]
    draw.text((tx, ty), label, font=font, fill=text_color, anchor="mm")

def draw_vs_token(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    center_y: int,
    scale: float,
    font_size_base: int = 42
) -> None:
    """Renders a metallic circular 'VS' token in between comparison badges."""
    radius = int(32 * scale)
    font_size = max(12, int(font_size_base * scale))
    font = get_best_font(font_size, bold=True)
    
    x0 = center_x - radius
    y0 = center_y - radius
    x1 = center_x + radius
    y1 = center_y + radius
    
    # Outer dark shadow
    draw.ellipse([x0 - 2, y0 - 2, x1 + 2, y1 + 2], fill=(0, 0, 0, 180))
    # Outer Gold/Metallic Rim
    draw.ellipse([x0, y0, x1, y1], fill=(22, 22, 26, 255), outline=(255, 215, 0, 255), width=max(2, int(3 * scale)))
    # VS text
    draw.text((center_x, center_y), "VS", font=font, fill=(255, 215, 0, 255), anchor="mm")

def render_badge_frame(
    progress: float,
    w: int,
    h: int,
    mode: str,
    left_label: str,
    left_color: str,
    right_label: str,
    right_color: str,
    single_label: str,
    single_color: str,
    pos: str,
    custom_y: Optional[int],
    show_vs: bool,
    glow_radius: int
) -> Image.Image:
    """Renders a single frame of glowing neon comparison badge(s)."""
    frame_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame_img)
    
    # Scale animation: Spring bounce entry (0 -> 0.22s), hold, smooth exit (0.85 -> 1.0)
    if progress < 0.15:
        t = progress / 0.15
        scale = ease_out_back(t)
    elif progress > 0.88:
        t = (1.0 - progress) / 0.12
        scale = max(0.0, t)
    else:
        # Subtle breathing pulse while on-screen
        pulse_phase = (progress - 0.15) / 0.73
        scale = 1.0 + 0.04 * math.sin(pulse_phase * math.pi * 6)
        
    if scale <= 0.05:
        return frame_img
        
    glow_pulse = 1.0 + 0.25 * math.sin(progress * math.pi * 8)
    
    # Determine Y position
    if custom_y is not None:
        cy = custom_y
    elif pos == "top":
        cy = int(h * 0.18)
    elif pos == "chest":
        cy = int(h * 0.62)
    elif pos == "bottom":
        cy = int(h * 0.82)
    elif pos == "center":
        cy = int(h * 0.50)
    else:
        cy = int(h * 0.18)
        
    if mode == "single":
        cx = w // 2
        draw_single_badge(
            draw=draw,
            glow_img=glow_canvas,
            center_x=cx,
            center_y=cy,
            label=single_label,
            palette_name=single_color,
            scale=scale,
            glow_intensity=glow_pulse,
            font_size_base=72
        )
    else:  # versus / comparison
        # Left badge at X ≈ 28%, Right badge at X ≈ 72%
        cx_left = int(w * 0.28)
        cx_right = int(w * 0.72)
        
        draw_single_badge(
            draw=draw,
            glow_img=glow_canvas,
            center_x=cx_left,
            center_y=cy,
            label=left_label,
            palette_name=left_color,
            scale=scale,
            glow_intensity=glow_pulse,
            font_size_base=64
        )
        
        draw_single_badge(
            draw=draw,
            glow_img=glow_canvas,
            center_x=cx_right,
            center_y=cy,
            label=right_label,
            palette_name=right_color,
            scale=scale,
            glow_intensity=glow_pulse,
            font_size_base=64
        )
        
        if show_vs:
            draw_vs_token(
                draw=draw,
                center_x=w // 2,
                center_y=cy,
                scale=scale,
                font_size_base=38
            )
            
    # Apply Gaussian blur to glow canvas and composite under badge
    if glow_radius > 0:
        blurred_glow = glow_canvas.filter(ImageFilter.GaussianBlur(glow_radius))
        # Composite: glow behind badges
        final_img = Image.alpha_composite(blurred_glow, frame_img)
        return final_img
    else:
        return frame_img

@app.command()
def apply(
    input_file: Path = typer.Option(..., "--input", "-i", help="Input video file path"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output video file path"),
    mode: str = typer.Option("versus", "--mode", "-m", help="Badge mode: 'versus' (dual comparison) or 'single' (single price/callout)"),
    left_label: str = typer.Option("$1", "--left-label", "-l", help="Left comparison label (e.g. '$1', 'BEFORE', 'CHEAP')"),
    left_color: str = typer.Option("red", "--left-color", help="Left badge color: red, green, gold, cyan, yellow, purple, white"),
    right_label: str = typer.Option("$10,000", "--right-label", "-r", help="Right comparison label (e.g. '$10k', 'AFTER', 'EXPENSIVE')"),
    right_color: str = typer.Option("green", "--right-color", help="Right badge color: red, green, gold, cyan, yellow, purple, white"),
    single_label: str = typer.Option("$10,000", "--label", help="Single badge label if mode is 'single'"),
    single_color: str = typer.Option("green", "--color", help="Single badge color if mode is 'single'"),
    vs_token: bool = typer.Option(True, "--vs/--no-vs", help="Include metallic center 'VS' token in versus mode"),
    position: str = typer.Option("top", "--pos", help="Placement preset: 'top' (Y=18%), 'chest' (Y=62%), 'bottom' (Y=82%), 'center'"),
    custom_y: Optional[int] = typer.Option(None, "--y", help="Exact custom Y coordinate"),
    start_time: float = typer.Option(0.0, "--start", "-s", help="Start timestamp in seconds"),
    duration: Optional[float] = typer.Option(None, "--duration", "-d", help="Display duration in seconds (defaults to rest of video)"),
    glow_radius: int = typer.Option(16, "--glow", help="Neon outer glow blur radius (default: 16)"),
    sfx: bool = typer.Option(True, "--sfx/--no-sfx", help="Mix synchronized reveal sound effect")
):
    """
    Renders glowing neon versus/price comparison badges with outer glow aura, pill container, and spring bounce animation.
    """
    ffmpeg_exe, ffprobe_exe = get_ffmpeg_paths()
    
    if not input_file.exists():
        console.print(f"[bold red]Error: Input file '{input_file}' not found![/bold red]")
        raise typer.Exit(1)
        
    output_dir = Path("Output")
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_file is None:
        output_file = output_dir / f"{input_file.stem}_versus_badge.mp4"
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
    console.print(f"[bold cyan]Analyzing input video specs:[/bold cyan] {input_file.name}")
    w, h, fps, total_dur = get_video_specs(input_file, ffprobe_exe)
    console.print(f"  • Resolution: {w}x{h} @ {fps:.2f} fps | Duration: {total_dur:.2f}s")
    
    # Calculate effective duration
    if duration is None:
        eff_dur = max(0.5, total_dur - start_time)
    else:
        eff_dur = min(duration, total_dur - start_time)
        
    end_time = start_time + eff_dur
    total_badge_frames = max(1, int(eff_dur * fps))
    console.print(f"[cyan]Rendering {total_badge_frames} badge overlay frames ({eff_dur:.2f}s duration)...[/cyan]")
    
    overlay_clip = output_dir / f"temp_badge_{input_file.stem}.mov"
    
    # Pipe RGBA frames directly into FFmpeg
    pipe_cmd = [
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
    
    proc = subprocess.Popen(pipe_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    for f_idx in range(total_badge_frames):
        p = f_idx / float(total_badge_frames)
        frame_img = render_badge_frame(
            progress=p,
            w=w,
            h=h,
            mode=mode,
            left_label=left_label,
            left_color=left_color,
            right_label=right_label,
            right_color=right_color,
            single_label=single_label,
            single_color=single_color,
            pos=position,
            custom_y=custom_y,
            show_vs=vs_token,
            glow_radius=glow_radius
        )
        proc.stdin.write(frame_img.tobytes())
        
    proc.stdin.close()
    proc.wait()
    console.print("[green]Transparent neon badge sequence generated.[/green]")
    
    # Select SFX if requested
    sfx_path = None
    if sfx:
        for cand in ["SFX/Power Up.mp3", "SFX/Scene Change .mp3", "SFX/UI Beep 5.wav", "SFX/Switch Click.mp3", "SFX/whoosh-6316.mp3"]:
            if os.path.exists(cand):
                sfx_path = cand
                break
                
    console.print(f"[cyan]Compositing badge overlay into video stream...[/cyan]")
    if sfx_path:
        console.print(f"[cyan]Mixing synchronized SFX: [bold]{sfx_path}[/bold] at {start_time:.2f}s...[/cyan]")
        delay_ms = int(start_time * 1000)
        filter_complex = (
            f"[0:v][1:v]overlay=0:0:enable='between(t,{start_time:.3f},{end_time:.3f})'[outv];"
            f"[2:a]adelay={delay_ms}|{delay_ms},volume=0.40[sfx_delayed];"
            f"[0:a][sfx_delayed]amix=inputs=2:duration=first:dropout_transition=2[outa]"
        )
        composite_cmd = [
            ffmpeg_exe,
            "-y",
            "-i", str(input_file),
            "-itsoffset", f"{start_time:.3f}",
            "-i", str(overlay_clip),
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
    else:
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
        
    console.print(f"\n[bold green]Success![/bold green] Glowing neon comparison badges applied! Video saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()

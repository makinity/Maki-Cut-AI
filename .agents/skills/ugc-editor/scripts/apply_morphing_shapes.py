#!/usr/bin/env python3
"""
Dynamic Morphing Shapes & Visual Engagement Graphics Generator for UGC Videos.
Applies animated bar graphs, circular progress rings, morphing callout rectangles,
bouncing CTA arrows, social media badges (Facebook, Instagram, TikTok, YouTube),
and prohibition Red X badges with smooth dark-red vignettes and error SFX.
"""

import sys
import os
import math
import subprocess
import json
import re
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
import typer
from rich.console import Console
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# UTF-8 resilience for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(help="Add dynamic morphing shapes, social badges, CTA arrows, and warning Red X overlays.")
console = Console()

PALETTES = {
    "cyan": {"primary": (0, 229, 255, 255), "secondary": (0, 150, 255, 200), "text": (255, 255, 255, 255)},
    "yellow": {"primary": (255, 230, 0, 255), "secondary": (255, 170, 0, 200), "text": (0, 0, 0, 255)},
    "green": {"primary": (57, 255, 20, 255), "secondary": (0, 200, 83, 200), "text": (0, 0, 0, 255)},
    "orange": {"primary": (255, 87, 34, 255), "secondary": (255, 152, 0, 200), "text": (255, 255, 255, 255)},
    "purple": {"primary": (179, 136, 255, 255), "secondary": (124, 77, 255, 200), "text": (255, 255, 255, 255)},
    "gold": {"primary": (214, 171, 76, 255), "secondary": (160, 120, 40, 200), "text": (244, 240, 232, 255)},
    "red": {"primary": (255, 35, 45, 255), "secondary": (180, 20, 30, 200), "text": (255, 255, 255, 255)},
}

def get_ffmpeg_paths() -> Tuple[str, str]:
    venv_scripts = Path(sys.prefix) / "Scripts"
    ffmpeg_exe = str(venv_scripts / "ffmpeg.exe") if (venv_scripts / "ffmpeg.exe").exists() else "ffmpeg"
    ffprobe_exe = str(venv_scripts / "ffprobe.exe") if (venv_scripts / "ffprobe.exe").exists() else "ffprobe"
    return ffmpeg_exe, ffprobe_exe

def get_video_specs(video_path: Path, ffprobe_exe: str) -> Tuple[int, int, float, float]:
    """Retrieve width, height, fps, and duration from the input video."""
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
        # Fallback check format duration
        cmd_fmt = [ffprobe_exe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video_path)]
        res_fmt = subprocess.run(cmd_fmt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration = float(json.loads(res_fmt.stdout).get("format", {}).get("duration", 10.0))
    return w, h, fps, duration

def ease_out_back(t: float) -> float:
    """Overshoot ease-out curve for bouncy kinetic motion."""
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * math.pow(t - 1.0, 3) + c1 * math.pow(t - 1.0, 2)

def ease_out_cubic(t: float) -> float:
    """Smooth cubic deceleration."""
    return 1.0 - math.pow(1.0 - t, 3)

def get_best_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    """Load workspace branded font or fallback to system Arial."""
    font_paths = [
        "fonts/ArchivoBlack-Regular.ttf" if bold else "fonts/Archivo-Variable.ttf",
        "fonts/Roboto-Bold.ttf" if bold else "fonts/Roboto.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

# -------------------------------------------------------------
# SHAPE RENDERERS
# -------------------------------------------------------------

def render_arrow_down_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """
    Renders an animated bouncing CTA arrow pointing below (for 'link in comments', 'link below').
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if pos == "center":
        cx, cy = w // 2, h // 2
    elif pos == "top_center":
        cx, cy = w // 2, int(h * 0.35)
    else:  # bottom_center
        cx, cy = w // 2, int(h * 0.80)

    # Bob up and down (subtle vertical pulse)
    bounce = math.sin(progress * math.pi * 4) * 20
    cy += int(bounce)

    # Scale in and out
    scale = min(1.0, progress / 0.15) if progress < 0.15 else (min(1.0, (1.0 - progress) / 0.15) if progress > 0.85 else 1.0)
    if scale <= 0.05:
        return img

    arrow_color = palette.get("primary", (214, 171, 76, 255))
    glow_color = (12, 16, 24, 230)

    # Draw Text Pill above the arrow
    pill_text = label if label else "LINK IN COMMENTS"
    pill_w = int(w * 0.52 * scale)
    pill_h = int(58 * scale)
    px0 = cx - pill_w // 2
    py0 = cy - pill_h - int(40 * scale)
    px1 = cx + pill_w // 2
    py1 = cy - int(40 * scale)

    draw.rounded_rectangle([px0, py0, px1, py1], radius=pill_h // 2, fill=glow_color, outline=arrow_color, width=4)
    font = get_best_font(int(pill_h * 0.44), bold=True)
    draw.text(((px0 + px1) // 2, (py0 + py1) // 2), pill_text.upper(), fill=(255, 255, 255, 255), anchor="mm", font=font)

    # Draw Arrow Pointing Down
    arr_size = int(65 * scale)
    draw.ellipse([cx - arr_size - 12, cy - 12, cx + arr_size + 12, cy + arr_size * 2 + 12], fill=glow_color)

    points = [
        (cx - int(arr_size * 0.32), cy),
        (cx + int(arr_size * 0.32), cy),
        (cx + int(arr_size * 0.32), cy + int(arr_size * 0.95)),
        (cx + int(arr_size * 0.95), cy + int(arr_size * 0.95)),
        (cx, cy + int(arr_size * 1.85)),
        (cx - int(arr_size * 0.95), cy + int(arr_size * 0.95)),
        (cx - int(arr_size * 0.32), cy + int(arr_size * 0.95)),
    ]
    draw.polygon(points, fill=arrow_color, outline=(255, 255, 255, 230))
    return img

def render_social_icon_frame(platform: str, progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    """
    Renders an official brand social media icon pop-up (Facebook, Instagram, TikTok, YouTube).
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if pos == "top_center":
        cx, cy = w // 2, int(h * 0.25)
    elif pos == "bottom_center":
        cx, cy = w // 2, int(h * 0.78)
    else:
        cx, cy = w // 2, int(h * 0.42)

    scale = min(1.0, progress / 0.16) if progress < 0.16 else (min(1.0, (1.0 - progress) / 0.15) if progress > 0.85 else 1.0)
    if scale <= 0.05:
        return img

    size = int(140 * scale)
    r = size // 2
    plat = platform.lower()

    if "face" in plat or "fb" in plat:
        fb_blue = (24, 119, 242, 255)
        draw.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=int(30 * scale), fill=fb_blue, outline=(255, 255, 255, 230), width=4)
        f_font = get_best_font(int(size * 0.78), bold=True)
        draw.text((cx + int(size * 0.08), cy + int(size * 0.04)), "f", fill=(255, 255, 255, 255), anchor="mm", font=f_font)
        default_label = "FACEBOOK"
    elif "insta" in plat or "ig" in plat:
        ig_color = (225, 48, 108, 255)
        draw.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=int(32 * scale), fill=ig_color, outline=(255, 220, 100, 230), width=4)
        cam_r = int(r * 0.65)
        draw.rounded_rectangle([cx - cam_r, cy - cam_r, cx + cam_r, cy + cam_r], radius=int(14 * scale), outline=(255, 255, 255, 255), width=int(7 * scale))
        lens_r = int(cam_r * 0.45)
        draw.ellipse([cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r], outline=(255, 255, 255, 255), width=int(6 * scale))
        dot_r = int(3 * scale)
        draw.ellipse([cx + int(cam_r * 0.55) - dot_r, cy - int(cam_r * 0.55) - dot_r, cx + int(cam_r * 0.55) + dot_r, cy - int(cam_r * 0.55) + dot_r], fill=(255, 255, 255, 255))
        default_label = "INSTAGRAM"
    elif "tik" in plat:
        draw.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=int(30 * scale), fill=(10, 10, 15, 245), outline=(0, 242, 234, 255), width=4)
        f_font = get_best_font(int(size * 0.70), bold=True)
        draw.text((cx, cy), "d", fill=(254, 44, 85, 255), anchor="mm", font=f_font)
        default_label = "TIKTOK"
    else:  # YouTube
        yt_red = (255, 0, 0, 255)
        draw.rounded_rectangle([cx - int(r * 1.25), cy - int(r * 0.85), cx + int(r * 1.25), cy + int(r * 0.85)], radius=int(26 * scale), fill=yt_red, outline=(255, 255, 255, 240), width=4)
        tri_pts = [(cx - int(r * 0.35), cy - int(r * 0.4)), (cx - int(r * 0.35), cy + int(r * 0.4)), (cx + int(r * 0.45), cy)]
        draw.polygon(tri_pts, fill=(255, 255, 255, 255))
        default_label = "YOUTUBE"

    # Optional handle/title pill below
    show_label = label if label else default_label
    if show_label:
        pill_w, pill_h = int(w * 0.48 * scale), int(50 * scale)
        py0 = cy + r + int(20 * scale)
        py1 = py0 + pill_h
        draw.rounded_rectangle([cx - pill_w // 2, py0, cx + pill_w // 2, py1], radius=pill_h // 2, fill=(12, 16, 24, 235), outline=(255, 255, 255, 180), width=3)
        font = get_best_font(int(pill_h * 0.46), bold=True)
        draw.text((cx, (py0 + py1) // 2), show_label.upper(), fill=(255, 255, 255, 255), anchor="mm", font=font)

    return img

def render_red_x_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str, with_vignette: bool = True) -> Image.Image:
    """
    Renders a bold Red X warning badge with smooth dark-red radial vignette.
    """
    # 1. Smooth Dark-Red Radial Vignette
    if with_vignette:
        vig_alpha = int(min(1.0, progress / 0.15) * 140) if progress < 0.2 else int(max(0.0, (1.0 - progress) / 0.3) * 140)
        if vig_alpha > 5:
            y, x = np.ogrid[:h, :w]
            norm_x = (x - w / 2) / (w / 2)
            norm_y = (y - h / 2) / (h / 2)
            dist = np.sqrt(norm_x**2 + norm_y**2)
            alpha_arr = np.clip((dist - 0.45) / 0.70, 0, 1) ** 2 * vig_alpha
            vig_data = np.zeros((h, w, 4), dtype=np.uint8)
            vig_data[..., 0] = 50
            vig_data[..., 3] = alpha_arr.astype(np.uint8)
            img = Image.fromarray(vig_data, mode="RGBA")
        else:
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)

    # 2. Position
    if pos == "top_center":
        cx, cy = w // 2, int(h * 0.26)
    elif pos == "bottom_center":
        cx, cy = w // 2, int(h * 0.72)
    else:
        cx, cy = w // 2, int(h * 0.44)

    # Heavy slam pop (1.35x -> 0.95x -> 1.0x)
    if progress < 0.12:
        t = progress / 0.12
        scale = 1.35 - (0.40 * t)
    else:
        scale = min(1.0, (1.0 - progress) / 0.15) if progress > 0.85 else 1.0

    if scale <= 0.05:
        return img

    size = int(190 * scale)
    r = size // 2

    # Outer Red Warning Glow
    draw.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=(80, 0, 0, 160))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 5, 5, 240), outline=(245, 30, 40, 255), width=int(8 * scale))

    # Bold X cross
    span = int(r * 0.55)
    lw = int(24 * scale)
    x_color = (255, 35, 45, 255)
    draw.line([cx - span, cy - span, cx + span, cy + span], fill=x_color, width=lw)
    draw.line([cx - span, cy + span, cx + span, cy - span], fill=x_color, width=lw)
    draw.line([cx - span + 2, cy - span + 2, cx + span - 2, cy + span - 2], fill=(255, 255, 255, 180), width=max(2, int(lw * 0.2)))

    # Warning text pill below
    pill_text = label if label else "DO NOT DO THIS"
    pill_w = int(w * 0.60 * scale)
    pill_h = int(60 * scale)
    py0 = cy + r + int(24 * scale)
    py1 = py0 + pill_h
    draw.rounded_rectangle([cx - pill_w // 2, py0, cx + pill_w // 2, py1], radius=pill_h // 2, fill=(15, 0, 0, 245), outline=(255, 35, 45, 255), width=4)
    font = get_best_font(int(pill_h * 0.44), bold=True)
    draw.text((cx, (py0 + py1) // 2), pill_text.upper(), fill=(255, 255, 255, 255), anchor="mm", font=font)

    return img

def render_bargraph_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
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
    font = get_best_font(int(card_h * 0.12), bold=True)
    draw.text((x0 + 35, y0 + 25), title_text.upper(), fill=palette["primary"], font=font)
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
    font = get_best_font(int(diameter * 0.22), bold=True)
    draw.text((cx, cy - 15), center_text, fill=(255, 255, 255, 255), anchor="mm", font=font)
    pulse_p = (progress * 2.0) % 1.0
    pulse_r = radius + int(pulse_p * 40)
    pulse_alpha = int((1.0 - pulse_p) * 160)
    draw.ellipse([cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r], outline=(palette["primary"][0], palette["primary"][1], palette["primary"][2], pulse_alpha), width=4)
    return img

def render_rectangle_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
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
    font = get_best_font(int(card_h * 0.32), bold=True)
    draw.text((dot_x + 30, cy), card_text.upper(), fill=(255, 255, 255, 255), anchor="lm", font=font)
    return img

def render_focus_ring_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
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
        font = get_best_font(36, bold=True)
        draw.text((cx, cy + r + 30), label.upper(), fill=palette["primary"], anchor="mm", font=font)
    return img

def render_badge_callout_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
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
    badge_text = label if label else "VIRAL HACK"
    font = get_best_font(int(badge_h * 0.38), bold=True)
    draw.text((cx, cy), badge_text.upper(), fill=(255, 255, 255, 255), anchor="mm", font=font)
    return img

def render_progress_bar_frame(progress: float, w: int, h: int, label: str, palette: dict, pos: str) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bar_h = 10
    y0 = 12 if pos == "top_center" else h - bar_h - 12
    y1 = y0 + bar_h
    draw.rounded_rectangle([24, y0, w - 24, y1], radius=5, fill=(255, 255, 255, 50))
    fill_w = int((w - 48) * min(1.0, progress))
    if fill_w > 4:
        draw.rounded_rectangle([24, y0, 24 + fill_w, y1], radius=5, fill=palette["primary"])
        draw.ellipse([24 + fill_w - 6, y0 - 3, 24 + fill_w + 6, y1 + 3], fill=(255, 255, 255, 240))
    return img

# -------------------------------------------------------------
# MAIN CLI COMMAND
# -------------------------------------------------------------

@app.command()
def apply_shape(
    input_file: Path = typer.Option(..., "--input", "-i", help="Source video (in Input/ or Output/)"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Target output video path"),
    shape: str = typer.Option("red_x", "--shape", "-s", help="Shape type: 'red_x', 'arrow_down', 'facebook', 'instagram', 'tiktok', 'youtube', 'bargraph', 'circular_motion', 'rectangle', 'badge_callout', 'progress_bar'"),
    start_time: float = typer.Option(1.5, "--start", "-t", help="Start timestamp in seconds when shape appears"),
    duration: float = typer.Option(2.5, "--duration", "-d", help="Duration in seconds of the shape animation"),
    label: str = typer.Option("", "--label", "-l", help="Text, handle, or message inside callout"),
    color: str = typer.Option("red", "--color", "-c", help="Color theme: red, gold, cyan, yellow, green, orange, purple"),
    position: str = typer.Option("center", "--position", "-pos", help="Position: center, top_center, bottom_center"),
    vignette: bool = typer.Option(True, "--vignette/--no-vignette", help="Include radial dark-red warning vignette for Red X"),
    sfx: bool = typer.Option(True, "--sfx/--no-sfx", help="Include error/punch sound effect from SFX/")
):
    """
    Renders and composites dynamic engagement graphics (Red X, CTA Arrow, Social Media Badges, Metric Charts).
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

    shape_key = shape.lower().replace("-", "_")
    palette = PALETTES.get(color.lower(), PALETTES["red"] if "red" in shape_key else PALETTES["gold"])

    console.print(f"[bold green]Inspecting video specifications...[/bold green]")
    w, h, fps, total_duration = get_video_specs(input_file, ffprobe_exe)
    console.print(f"Canvas: [bold yellow]{w}x{h}[/bold yellow] @ [bold yellow]{fps:.1f} fps[/bold yellow] (Duration: {total_duration:.2f}s)")

    total_frames = max(1, int(duration * fps))
    end_time = min(total_duration, start_time + duration)
    console.print(f"Generating [bold cyan]{shape}[/bold cyan] ({total_frames} frames from {start_time:.2f}s to {end_time:.2f}s)...")

    overlay_clip = output_dir / f"temp_{shape_key}_overlay.mov"

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
        if shape_key in {"red_x", "warning_x", "error"}:
            frame_img = render_red_x_frame(p, w, h, label if label else "DO NOT DO THIS", palette, position, with_vignette=vignette)
        elif shape_key in {"arrow_down", "arrow", "cta_arrow"}:
            frame_img = render_arrow_down_frame(p, w, h, label if label else "LINK IN COMMENTS", palette, position if position != "center" else "bottom_center")
        elif shape_key in {"facebook", "social_fb", "fb"}:
            frame_img = render_social_icon_frame("facebook", p, w, h, label, palette, position)
        elif shape_key in {"instagram", "social_ig", "ig"}:
            frame_img = render_social_icon_frame("instagram", p, w, h, label, palette, position)
        elif shape_key in {"tiktok", "social_tiktok"}:
            frame_img = render_social_icon_frame("tiktok", p, w, h, label, palette, position)
        elif shape_key in {"youtube", "social_yt", "yt"}:
            frame_img = render_social_icon_frame("youtube", p, w, h, label, palette, position)
        elif shape_key == "bargraph":
            frame_img = render_bargraph_frame(p, w, h, label, palette, position)
        elif shape_key == "circular_motion":
            frame_img = render_circular_motion_frame(p, w, h, label, palette, position)
        elif shape_key == "rectangle":
            frame_img = render_rectangle_frame(p, w, h, label, palette, position)
        elif shape_key == "focus_ring":
            frame_img = render_focus_ring_frame(p, w, h, label, palette, position)
        elif shape_key == "badge_callout":
            frame_img = render_badge_callout_frame(p, w, h, label, palette, position)
        elif shape_key == "progress_bar":
            frame_img = render_progress_bar_frame(p, w, h, label, palette, position)
        else:
            frame_img = render_red_x_frame(p, w, h, label, palette, position, with_vignette=vignette)

        proc.stdin.write(frame_img.tobytes())

    proc.stdin.close()
    proc.wait()
    console.print("[green]Transparent motion graphic sequence rendered.[/green]")

    # Audio handling: check if SFX is requested
    sfx_path = None
    if sfx and shape_key in {"red_x", "warning_x", "error"}:
        # Select best error sound
        for sfx_cand in ["SFX/Nope .mp3", "SFX/Buzz - Whoosh.wav", "SFX/SLAP SFX.mp3"]:
            if os.path.exists(sfx_cand):
                sfx_path = sfx_cand
                break
    elif sfx and shape_key in {"arrow_down", "cta_arrow"}:
        if os.path.exists("SFX/WHOOSH 2 SFX.mp3"):
            sfx_path = "SFX/WHOOSH 2 SFX.mp3"

    console.print(f"[cyan]Compositing graphic into video stream...[/cyan]")
    if sfx_path:
        console.print(f"[cyan]Mixing synchronized SFX: [bold]{sfx_path}[/bold] at {start_time:.2f}s...[/cyan]")
        delay_ms = int(start_time * 1000)
        filter_complex = (
            f"[0:v][1:v]overlay=0:0:enable='between(t,{start_time:.3f},{end_time:.3f})'[outv];"
            f"[2:a]adelay={delay_ms}|{delay_ms},volume=0.45[sfx_delayed];"
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

    console.print(f"\n[bold green]Success![/bold green] Engagement graphic applied! Saved to: [bold]{output_file}[/bold]")

if __name__ == "__main__":
    app()
